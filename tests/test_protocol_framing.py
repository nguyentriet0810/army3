import unittest

from server.army3_protocol.errors import FrameError
from server.army3_protocol.framing import (
    FrameDirection,
    FrameStreamDecoder,
    Packet,
    encode_frame,
)
from server.army3_protocol.transform import ByteTransform


class FrameCodecTests(unittest.TestCase):
    def test_empty_client_request_has_two_byte_length(self) -> None:
        encoded = encode_frame(
            Packet(0xE5),
            FrameDirection.CLIENT_TO_SERVER,
        )
        self.assertEqual(encoded, bytes.fromhex("E5 00 00"))

    def test_server_e1_uses_four_byte_length(self) -> None:
        encoded = encode_frame(
            Packet(0xE1, b"\x01\x02"),
            FrameDirection.SERVER_TO_CLIENT,
        )
        self.assertEqual(encoded, bytes.fromhex("E1 00 00 00 02 01 02"))

    def test_client_e1_request_still_uses_two_byte_length(self) -> None:
        encoded = encode_frame(
            Packet(0xE1),
            FrameDirection.CLIENT_TO_SERVER,
        )
        self.assertEqual(encoded, bytes.fromhex("E1 00 00"))

    def test_fragmented_transformed_frame_does_not_drift_cursor(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("10 20 30"), 7)
        encoded = encode_frame(
            Packet(0xBB, b"payload"),
            FrameDirection.CLIENT_TO_SERVER,
            transform.cursor(),
        )
        decoder_cursor = transform.cursor()
        decoder = FrameStreamDecoder(
            FrameDirection.CLIENT_TO_SERVER,
            decoder_cursor,
        )

        packets = []
        for byte in encoded:
            packets.extend(decoder.feed(bytes((byte,))))

        self.assertEqual(packets, [Packet(0xBB, b"payload")])
        self.assertEqual(decoder.pending_bytes, 0)
        self.assertEqual(decoder_cursor.index, len(encoded) % len(transform.key))

    def test_coalesced_frames_preserve_transform_state(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("12 34"), 3)
        encoder = transform.cursor()
        first = encode_frame(
            Packet(0x07), FrameDirection.CLIENT_TO_SERVER, encoder
        )
        second = encode_frame(
            Packet(0xDB, b"x"), FrameDirection.CLIENT_TO_SERVER, encoder
        )
        decoder = FrameStreamDecoder(
            FrameDirection.CLIENT_TO_SERVER,
            transform.cursor(),
        )
        self.assertEqual(
            decoder.feed(first + second),
            [Packet(0x07), Packet(0xDB, b"x")],
        )

    def test_packet_limit_leaves_coalesced_frame_buffered(self) -> None:
        decoder = FrameStreamDecoder(FrameDirection.CLIENT_TO_SERVER)
        wire = bytes.fromhex("E5 00 00 07 00 00")
        self.assertEqual(decoder.feed(wire, max_packets=1), [Packet(0xE5)])
        self.assertEqual(decoder.pending_bytes, 3)
        self.assertEqual(decoder.feed(b"", max_packets=1), [Packet(0x07)])
        self.assertEqual(decoder.pending_bytes, 0)

    def test_invalid_packet_limit_is_rejected(self) -> None:
        decoder = FrameStreamDecoder(FrameDirection.CLIENT_TO_SERVER)
        with self.assertRaises(ValueError):
            decoder.feed(b"", max_packets=0)

    def test_length32_frame_only_transforms_command(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("10 20 30"), 7)
        encoder = transform.cursor()
        encoded = encode_frame(
            Packet(0xE1, b"\xAA\xBB"),
            FrameDirection.SERVER_TO_CLIENT,
            encoder,
        )

        self.assertEqual(encoded[1:], bytes.fromhex("00 00 00 02 AA BB"))
        self.assertEqual(encoder.index, 1)

        decoder_cursor = transform.cursor()
        decoder = FrameStreamDecoder(
            FrameDirection.SERVER_TO_CLIENT,
            decoder_cursor,
        )
        self.assertEqual(decoder.feed(encoded), [Packet(0xE1, b"\xAA\xBB")])
        self.assertEqual(decoder_cursor.index, 1)

    def test_all_commands_round_trip_across_both_directions(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("13 37 A5"), 0xE9)
        for direction in FrameDirection:
            with self.subTest(direction=direction):
                encoder = transform.cursor()
                expected = [
                    Packet(command, bytes((command,)) * (command % 5))
                    for command in range(256)
                ]
                wire = b"".join(
                    encode_frame(packet, direction, encoder) for packet in expected
                )
                decoder = FrameStreamDecoder(direction, transform.cursor())
                actual = []
                for offset in range(0, len(wire), 7):
                    actual.extend(decoder.feed(wire[offset : offset + 7]))
                self.assertEqual(actual, expected)
                self.assertEqual(decoder.pending_bytes, 0)

    def test_oversized_declared_payload_is_rejected(self) -> None:
        decoder = FrameStreamDecoder(
            FrameDirection.CLIENT_TO_SERVER,
            max_payload_bytes=4,
        )
        with self.assertRaisesRegex(FrameError, "exceeds limit"):
            decoder.feed(bytes.fromhex("01 00 05"))

    def test_invalid_packet_values_are_rejected(self) -> None:
        with self.assertRaises(FrameError):
            Packet(256)
        with self.assertRaises(FrameError):
            Packet(1, "not bytes")  # type: ignore[arg-type]
        with self.assertRaises(FrameError):
            Packet(1, 3)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
