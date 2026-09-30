import unittest

from server.army3_protocol.errors import DecodeError
from server.army3_protocol.framing import FrameDirection, Packet, encode_frame
from server.army3_protocol.messages import (
    BootstrapDaResponse,
    BootstrapE0EmptyResponse,
    BootstrapE1Response,
    BootstrapVersions,
    ClientPostResetStatus,
    ClientC6Selection,
    ClientPrelogin72,
    ClientAreaRequest,
    ClientSessionRequest,
    ClientTransportSync0,
    ClientU32B2,
    Command,
    EmptyClientRequest,
    HandshakeResponse,
    ServerSessionResponse,
    ServerPreloginStatus,
    ServerAreaList,
    ServerAreaRecord,
    ServerTransportReset2,
    ScreenBootstrapResponse,
    ScreenResourceItemResponse,
    ScreenResourceManifestResponse,
)


class LoginMessageCodecTests(unittest.TestCase):
    def test_handshake_golden_vector(self) -> None:
        message = HandshakeResponse(b"\x00", 0, "local")
        frame = encode_frame(
            message.to_packet(),
            FrameDirection.SERVER_TO_CLIENT,
        )
        self.assertEqual(
            frame,
            bytes.fromhex("E5 00 0A 01 00 00 00 05 6C 6F 63 61 6C"),
        )
        self.assertEqual(
            HandshakeResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_server_session_response_golden_vector(self) -> None:
        message = ServerSessionResponse("local", "local", "local", "local")
        frame = encode_frame(
            message.to_packet(),
            FrameDirection.SERVER_TO_CLIENT,
        )
        expected = bytes.fromhex(
            "BB 00 1C "
            "00 05 6C 6F 63 61 6C "
            "00 05 6C 6F 63 61 6C "
            "00 05 6C 6F 63 61 6C "
            "00 05 6C 6F 63 61 6C"
        )
        self.assertEqual(frame, expected)
        self.assertEqual(
            ServerSessionResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_client_session_request_round_trip(self) -> None:
        message = ClientSessionRequest("field-b", "field-a", 1)
        self.assertEqual(
            ClientSessionRequest.decode_payload(message.encode_payload()),
            message,
        )

    def test_client_transport_sync0_round_trip(self) -> None:
        message = ClientTransportSync0("local", 0, 0)
        self.assertEqual(len(message.encode_payload()), 16)
        self.assertEqual(
            ClientTransportSync0.decode_payload(message.encode_payload()),
            message,
        )

    def test_client_transport_sync_rejects_unknown_subcommand(self) -> None:
        with self.assertRaisesRegex(DecodeError, "subcommand"):
            ClientTransportSync0.decode_payload(bytes.fromhex("01"))

    def test_server_transport_reset2_is_one_byte(self) -> None:
        message = ServerTransportReset2()
        self.assertEqual(message.encode_payload(), b"\x02")
        self.assertEqual(ServerTransportReset2.decode_payload(b"\x02"), message)

    def test_runtime_prelogin_messages_round_trip(self) -> None:
        messages = (
            ClientPostResetStatus(1),
            ClientPrelogin72(2, 3, "runtime"),
            ClientU32B2(0x01020304),
            ServerPreloginStatus(1),
        )
        for message in messages:
            with self.subTest(message=type(message).__name__):
                payload = message.encode_payload()
                self.assertEqual(type(message).decode_payload(payload), message)

    def test_client_c6_selection_golden_vector(self) -> None:
        message = ClientC6Selection("")
        self.assertEqual(message.encode_payload(), bytes.fromhex("00 00 01"))
        self.assertEqual(
            ClientC6Selection.decode_payload(message.encode_payload()),
            message,
        )

    def test_client_c6_selection_rejects_noncanonical_marker(self) -> None:
        with self.assertRaisesRegex(DecodeError, "marker 1"):
            ClientC6Selection.decode_payload(bytes.fromhex("00 00 00"))

    def test_area_e4_golden_vectors(self) -> None:
        request = ClientAreaRequest()
        response = ServerAreaList()

        self.assertEqual(request.encode_payload(), b"\x00")
        name = "Khu vực Local".encode("utf-8")
        expected_payload = (
            bytes.fromhex("00 00 00 00 00 08 00 00 00 00")
            + len(name).to_bytes(2, "big")
            + name
        )
        self.assertEqual(response.encode_payload(), expected_payload)
        self.assertEqual(
            encode_frame(response.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            b"\xE4" + len(expected_payload).to_bytes(2, "big") + expected_payload,
        )
        self.assertEqual(
            ClientAreaRequest.decode_payload(request.encode_payload()),
            request,
        )
        self.assertEqual(
            ServerAreaList.decode_payload(response.encode_payload()),
            response,
        )

    def test_area_e4_rejects_unconfirmed_request_mode(self) -> None:
        with self.assertRaisesRegex(DecodeError, "mode"):
            ClientAreaRequest.decode_payload(b"\x01")

    def test_area_e4_supports_sentinel_record_and_rejects_password_branch(self) -> None:
        message = ServerAreaList((ServerAreaRecord(-1, name="Tạo khu vực"),))
        self.assertEqual(
            ServerAreaList.decode_payload(message.encode_payload()), message
        )
        with self.assertRaisesRegex(DecodeError, "password-prompt"):
            ServerAreaList.decode_payload(b"\x01")

    def test_bootstrap_versions_golden_vector(self) -> None:
        message = BootstrapVersions(1, 1, 1)
        self.assertEqual(
            encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            bytes.fromhex("E2 00 03 01 01 01"),
        )

    def test_screen_bootstrap_golden_vector_uses_length32(self) -> None:
        message = ScreenBootstrapResponse(127)
        self.assertEqual(message.encode_payload(), bytes.fromhex("00 7F 00 00"))
        self.assertEqual(
            encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            bytes.fromhex("C4 00 00 00 04 00 7F 00 00"),
        )
        self.assertEqual(
            ScreenBootstrapResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_screen_bootstrap_preserves_negative_s8(self) -> None:
        message = ScreenBootstrapResponse(-128, "local")
        self.assertEqual(
            ScreenBootstrapResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_screen_resource_manifest_golden_vector(self) -> None:
        message = ScreenResourceManifestResponse(0, 1)
        self.assertEqual(message.encode_payload(), bytes.fromhex("01 00 00 01"))
        self.assertEqual(
            ScreenResourceManifestResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_screen_resource_item_golden_vector(self) -> None:
        message = ScreenResourceItemResponse("probe", b"\x00")
        self.assertEqual(
            message.encode_payload(),
            bytes.fromhex("02 00 05 70 72 6F 62 65 00 00 00 01 00"),
        )
        self.assertEqual(
            ScreenResourceItemResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_da_empty_golden_vector(self) -> None:
        message = BootstrapDaResponse.empty()
        self.assertEqual(
            encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            bytes.fromhex("DA 00 06 01 00 00 00 01 00"),
        )
        self.assertEqual(BootstrapDaResponse.decode_payload(message.encode_payload()), message)

    def test_e1_empty_golden_vector_uses_length32(self) -> None:
        message = BootstrapE1Response.empty()
        expected = bytes.fromhex(
            "E1 00 00 00 12 "
            "01 00 00 00 02 00 00 00 00 00 02 00 00 00 00 00 01 00"
        )
        self.assertEqual(
            encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            expected,
        )
        self.assertEqual(BootstrapE1Response.decode_payload(message.encode_payload()), message)

    def test_e0_empty_golden_vector(self) -> None:
        message = BootstrapE0EmptyResponse()
        self.assertEqual(
            encode_frame(message.to_packet(), FrameDirection.SERVER_TO_CLIENT),
            bytes.fromhex("E0 00 04 01 00 00 00"),
        )
        self.assertEqual(
            BootstrapE0EmptyResponse.decode_payload(message.encode_payload()),
            message,
        )

    def test_empty_requests_reject_payload(self) -> None:
        request = EmptyClientRequest(Command.BOOTSTRAP_READY)
        self.assertEqual(request.to_packet(), Packet(0xDB))
        with self.assertRaisesRegex(DecodeError, "payload"):
            EmptyClientRequest.from_packet(Packet(0xDB, b"x"))

    def test_message_decoder_rejects_trailing_bytes(self) -> None:
        payload = BootstrapVersions(1, 1, 1).encode_payload() + b"\x00"
        with self.assertRaisesRegex(DecodeError, "trailing"):
            BootstrapVersions.decode_payload(payload)

    def test_nonempty_e0_is_explicitly_unsupported(self) -> None:
        with self.assertRaisesRegex(DecodeError, "outside the confirmed"):
            BootstrapE0EmptyResponse.decode_payload(bytes.fromhex("01 01 00 00"))


if __name__ == "__main__":
    unittest.main()
