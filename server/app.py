"""Async TCP transport for the loopback-only compatibility server."""

from __future__ import annotations

import asyncio
import itertools
import logging
from collections.abc import Awaitable, Callable

from .army3_protocol.errors import ProtocolError
from .army3_protocol.framing import (
    FrameDirection,
    FrameStreamDecoder,
    Packet,
    encode_frame,
)
from .army3_protocol.messages import Command
from .army3_protocol.transform import TransformCursor
from .config import ServerConfig
from .session import LoginSession


LOGGER = logging.getLogger("army3.local_server")
_CONNECTION_IDS = itertools.count(1)


async def _handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    config: ServerConfig,
) -> None:
    connection_id = next(_CONNECTION_IDS)
    peer = writer.get_extra_info("peername")
    LOGGER.info("event=connected connection=%s peer=%s", connection_id, peer)

    decoder = FrameStreamDecoder(
        FrameDirection.CLIENT_TO_SERVER,
        max_payload_bytes=config.max_payload_bytes,
    )
    outbound_cursor: TransformCursor | None = None
    session = LoginSession(
        experimental_splash_revision=config.experimental_splash_revision
    )

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    reader.read(config.read_chunk_size),
                    timeout=config.heartbeat_interval_seconds,
                )
            except TimeoutError:
                if outbound_cursor is None:
                    continue
                heartbeat = Packet(Command.HEARTBEAT)
                writer.write(
                    encode_frame(
                        heartbeat,
                        FrameDirection.SERVER_TO_CLIENT,
                        outbound_cursor,
                    )
                )
                await writer.drain()
                LOGGER.debug(
                    "event=heartbeat_sent connection=%s command=0x%02X",
                    connection_id,
                    heartbeat.command,
                )
                continue
            if not data:
                LOGGER.info(
                    "event=client_closed connection=%s state=%s",
                    connection_id,
                    session.state.name,
                )
                return

            pending_input = data
            while True:
                packets = decoder.feed(pending_input, max_packets=1)
                pending_input = b""
                if not packets:
                    break

                packet = packets[0]
                LOGGER.debug(
                    "event=packet_received connection=%s state=%s command=0x%02X bytes=%s",
                    connection_id,
                    session.state.name,
                    packet.command,
                    len(packet.payload),
                )
                outcome = session.handle(packet)

                for response in outcome.outbound:
                    writer.write(
                        encode_frame(
                            response,
                            FrameDirection.SERVER_TO_CLIENT,
                            outbound_cursor,
                        )
                    )
                    LOGGER.debug(
                        "event=packet_sent connection=%s command=0x%02X bytes=%s",
                        connection_id,
                        response.command,
                        len(response.payload),
                    )
                if outcome.outbound:
                    await writer.drain()

                if outcome.enable_transform is not None:
                    if decoder.cursor is not None or outbound_cursor is not None:
                        raise RuntimeError("transform was enabled more than once")
                    decoder.cursor = outcome.enable_transform.cursor()
                    outbound_cursor = outcome.enable_transform.cursor()
                    LOGGER.debug(
                        "event=transform_enabled connection=%s", connection_id
                    )
    except asyncio.CancelledError:
        raise
    except ProtocolError as exc:
        LOGGER.warning(
            "event=protocol_error connection=%s state=%s error=%s",
            connection_id,
            session.state.name,
            exc,
        )
    except (ConnectionError, BrokenPipeError) as exc:
        LOGGER.info(
            "event=connection_error connection=%s error=%s",
            connection_id,
            type(exc).__name__,
        )
    except Exception:
        LOGGER.exception("event=internal_error connection=%s", connection_id)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, BrokenPipeError):
            pass
        LOGGER.info("event=disconnected connection=%s", connection_id)


async def start_server(config: ServerConfig) -> asyncio.Server:
    """Start listening and return the server object for tests or embedding."""

    client_connected: Callable[
        [asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]
    ] = lambda reader, writer: _handle_client(reader, writer, config)
    return await asyncio.start_server(
        client_connected,
        host=config.host,
        port=config.port,
        backlog=config.backlog,
    )


async def serve_forever(config: ServerConfig) -> None:
    server = await start_server(config)
    addresses = ",".join(str(sock.getsockname()) for sock in server.sockets or ())
    LOGGER.info("event=listening addresses=%s", addresses)
    async with server:
        await server.serve_forever()
