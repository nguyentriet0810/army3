import asyncio
import logging
import unittest

from server.app import start_server
from server.army3_protocol.framing import (
    FrameDirection,
    FrameStreamDecoder,
    Packet,
    encode_frame,
)
from server.army3_protocol.messages import (
    BootstrapDaResponse,
    BootstrapE0EmptyResponse,
    BootstrapE1Response,
    BootstrapVersions,
    ClientPostResetStatus,
    ClientAreaRequest,
    ClientPrelogin72,
    ClientSessionRequest,
    ClientU32B2,
    Command,
    HandshakeResponse,
    ServerSessionResponse,
    ServerPreloginStatus,
    ServerAreaList,
    ScreenBootstrapResponse,
)
from server.army3_protocol.transform import ByteTransform, TransformCursor
from server.config import ServerConfig


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


class LocalServerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.logger = logging.getLogger("army3.local_server")
        self.previous_level = self.logger.level
        self.previous_propagate = self.logger.propagate
        self.log_handler = _ListHandler()
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.logger.addHandler(self.log_handler)
        self.server = await start_server(ServerConfig(port=0))
        socket = self.server.sockets[0]
        self.port = socket.getsockname()[1]

    async def asyncTearDown(self) -> None:
        self.server.close()
        await self.server.wait_closed()
        self.logger.removeHandler(self.log_handler)
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate

    async def _read_packets(
        self,
        reader: asyncio.StreamReader,
        decoder: FrameStreamDecoder,
        count: int,
    ) -> list[Packet]:
        packets: list[Packet] = []
        while len(packets) < count:
            data = await asyncio.wait_for(reader.read(4096), timeout=2)
            self.assertTrue(data, "server closed before expected packets arrived")
            packets.extend(decoder.feed(data))
        self.assertEqual(len(packets), count)
        return packets

    async def test_simulated_client_completes_login_bootstrap(self) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        server_decoder = FrameStreamDecoder(FrameDirection.SERVER_TO_CLIENT)
        client_cursor: TransformCursor | None = None
        try:
            writer.write(
                encode_frame(Packet(Command.HANDSHAKE), FrameDirection.CLIENT_TO_SERVER)
            )
            await writer.drain()

            handshake_packet = (await self._read_packets(reader, server_decoder, 1))[0]
            handshake = HandshakeResponse.decode_payload(handshake_packet.payload)
            self.assertEqual(handshake, HandshakeResponse(b"\x00", 0, "local"))

            transform = ByteTransform.from_seed(handshake.seed, handshake.shift)
            server_decoder.cursor = transform.cursor()
            client_cursor = transform.cursor()

            writer.write(
                encode_frame(
                    ClientPostResetStatus(1).to_packet(),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
                + encode_frame(
                    ClientPrelogin72(1, 1, "runtime").to_packet(),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
                + encode_frame(
                    Packet(Command.PRELOGIN_STATUS),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()
            status_packet = (await self._read_packets(reader, server_decoder, 1))[0]
            self.assertEqual(status_packet.command, Command.PRELOGIN_STATUS)
            self.assertEqual(
                ServerPreloginStatus.decode_payload(status_packet.payload).value,
                1,
            )

            initial_bb = ClientSessionRequest(
                "secret-installation-value", "secret-config-value", 1
            ).to_packet()
            writer.write(
                encode_frame(initial_bb, FrameDirection.CLIENT_TO_SERVER, client_cursor)
                + encode_frame(
                    ClientU32B2(1).to_packet(),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
                + encode_frame(
                    Packet(Command.UNKNOWN_07),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()

            initial_responses = await self._read_packets(reader, server_decoder, 2)
            self.assertEqual(
                [packet.command for packet in initial_responses],
                [Command.CLIENT_SESSION, Command.BOOTSTRAP_VERSIONS],
            )
            ServerSessionResponse.decode_payload(initial_responses[0].payload)
            self.assertEqual(
                BootstrapVersions.decode_payload(initial_responses[1].payload),
                BootstrapVersions(2, 2, 2),
            )

            request_order = (
                Command.BOOTSTRAP_E1,
                Command.BOOTSTRAP_E0,
                Command.BOOTSTRAP_DA,
                Command.BOOTSTRAP_READY,
            )
            writer.write(
                b"".join(
                    encode_frame(
                        Packet(command),
                        FrameDirection.CLIENT_TO_SERVER,
                        client_cursor,
                    )
                    for command in request_order
                )
            )
            await writer.drain()

            bootstrap_responses = await self._read_packets(reader, server_decoder, 3)
            self.assertEqual(
                [packet.command for packet in bootstrap_responses],
                [Command.BOOTSTRAP_E1, Command.BOOTSTRAP_E0, Command.BOOTSTRAP_DA],
            )
            BootstrapE1Response.decode_payload(bootstrap_responses[0].payload)
            BootstrapE0EmptyResponse.decode_payload(bootstrap_responses[1].payload)
            BootstrapDaResponse.decode_payload(bootstrap_responses[2].payload)

            panel_bb = ClientSessionRequest(
                "secret-panel-field-b", "secret-panel-field-a", 0
            ).to_packet()
            writer.write(
                encode_frame(
                    panel_bb,
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()
            panel_response = (await self._read_packets(reader, server_decoder, 1))[0]
            self.assertEqual(panel_response.command, Command.CLIENT_SESSION)
            self.assertEqual(
                ServerSessionResponse.decode_payload(panel_response.payload),
                ServerSessionResponse("local", "local", "local", "local"),
            )

            writer.write(
                encode_frame(
                    ClientAreaRequest().to_packet(),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()
            area_response = (
                await self._read_packets(reader, server_decoder, 1)
            )[0]
            self.assertEqual(area_response.command, Command.AREA)
            self.assertEqual(
                ServerAreaList.decode_payload(area_response.payload),
                ServerAreaList(),
            )
        finally:
            writer.close()
            await writer.wait_closed()

        combined_logs = "\n".join(self.log_handler.messages)
        for submitted_value in (
            "secret-installation-value",
            "secret-config-value",
            "secret-panel-field-b",
            "secret-panel-field-a",
        ):
            self.assertNotIn(submitted_value, combined_logs)

    async def test_idle_transformed_connection_receives_heartbeat(self) -> None:
        heartbeat_server = await start_server(
            ServerConfig(port=0, heartbeat_interval_seconds=0.1)
        )
        heartbeat_port = heartbeat_server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", heartbeat_port)
        decoder = FrameStreamDecoder(FrameDirection.SERVER_TO_CLIENT)
        try:
            writer.write(
                encode_frame(Packet(Command.HANDSHAKE), FrameDirection.CLIENT_TO_SERVER)
            )
            await writer.drain()
            handshake_packet = (await self._read_packets(reader, decoder, 1))[0]
            handshake = HandshakeResponse.decode_payload(handshake_packet.payload)
            decoder.cursor = ByteTransform.from_seed(
                handshake.seed, handshake.shift
            ).cursor()

            heartbeat = (await self._read_packets(reader, decoder, 1))[0]
            self.assertEqual(heartbeat, Packet(Command.HEARTBEAT))
        finally:
            writer.close()
            await writer.wait_closed()
            heartbeat_server.close()
            await heartbeat_server.wait_closed()

    async def test_experimental_splash_transition_and_empty_c4_ack(self) -> None:
        experimental_server = await start_server(
            ServerConfig(port=0, experimental_splash_revision=127)
        )
        experimental_port = experimental_server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection(
            "127.0.0.1", experimental_port
        )
        decoder = FrameStreamDecoder(FrameDirection.SERVER_TO_CLIENT)
        try:
            writer.write(
                encode_frame(
                    Packet(Command.HANDSHAKE), FrameDirection.CLIENT_TO_SERVER
                )
            )
            await writer.drain()
            handshake_packet = (await self._read_packets(reader, decoder, 1))[0]
            handshake = HandshakeResponse.decode_payload(handshake_packet.payload)
            transform = ByteTransform.from_seed(handshake.seed, handshake.shift)
            decoder.cursor = transform.cursor()
            client_cursor = transform.cursor()

            writer.write(
                encode_frame(
                    ClientSessionRequest("installation", "config", 1).to_packet(),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()
            responses = await self._read_packets(reader, decoder, 3)
            self.assertEqual(
                [packet.command for packet in responses],
                [
                    Command.CLIENT_SESSION,
                    Command.BOOTSTRAP_VERSIONS,
                    Command.SCREEN_BOOTSTRAP,
                ],
            )
            self.assertEqual(
                ScreenBootstrapResponse.decode_payload(responses[2].payload),
                ScreenBootstrapResponse(127),
            )

            writer.write(
                encode_frame(
                    Packet(Command.SCREEN_BOOTSTRAP),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
                + encode_frame(
                    Packet(Command.PRELOGIN_STATUS),
                    FrameDirection.CLIENT_TO_SERVER,
                    client_cursor,
                )
            )
            await writer.drain()
            status = (await self._read_packets(reader, decoder, 1))[0]
            self.assertEqual(status.command, Command.PRELOGIN_STATUS)
        finally:
            writer.close()
            await writer.wait_closed()
            experimental_server.close()
            await experimental_server.wait_closed()

    async def test_protocol_violation_closes_only_that_connection(self) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            writer.write(
                encode_frame(Packet(Command.UNKNOWN_07), FrameDirection.CLIENT_TO_SERVER)
            )
            await writer.drain()
            self.assertEqual(await asyncio.wait_for(reader.read(1), timeout=2), b"")
        finally:
            writer.close()
            await writer.wait_closed()

        # The listener remains healthy after rejecting a bad session.
        reader2, writer2 = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            writer2.write(
                encode_frame(Packet(Command.HANDSHAKE), FrameDirection.CLIENT_TO_SERVER)
            )
            await writer2.drain()
            decoder = FrameStreamDecoder(FrameDirection.SERVER_TO_CLIENT)
            response = (await self._read_packets(reader2, decoder, 1))[0]
            self.assertEqual(response.command, Command.HANDSHAKE)
        finally:
            writer2.close()
            await writer2.wait_closed()


if __name__ == "__main__":
    unittest.main()
