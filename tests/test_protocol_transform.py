import unittest

from server.army3_protocol.errors import EncodeError
from server.army3_protocol.transform import ByteTransform


class ByteTransformTests(unittest.TestCase):
    def test_seed_becomes_prefix_xor_key(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("10 20 30 40"), 7)
        self.assertEqual(transform.key, bytes.fromhex("10 30 00 40"))

    def test_command_and_data_round_trip(self) -> None:
        transform = ByteTransform.from_seed(bytes.fromhex("10 20 30"), 7)
        encoder = transform.cursor()
        decoder = transform.cursor()

        raw_command = encoder.encode_command(0x54)
        raw_data = [encoder.encode_data(value) for value in (0x00, 0x03, 1, 2, 3)]

        self.assertEqual(decoder.decode_command(raw_command), 0x54)
        self.assertEqual(
            [decoder.decode_data(value) for value in raw_data],
            [0x00, 0x03, 1, 2, 3],
        )
        self.assertEqual(encoder.index, decoder.index)

    def test_identity_transform_still_advances_cursor(self) -> None:
        cursor = ByteTransform.from_seed(b"\x00", 0).cursor()
        self.assertEqual(cursor.encode_command(0xE2), 0xE2)
        self.assertEqual(cursor.encode_data(0x12), 0x12)
        self.assertEqual(cursor.index, 0)

    def test_send_and_receive_cursors_are_independent(self) -> None:
        transform = ByteTransform.from_seed(b"\x10\x20", 1)
        send = transform.cursor()
        receive = transform.cursor()
        send.encode_command(1)
        send.encode_data(2)
        self.assertEqual(receive.index, 0)

    def test_empty_or_oversized_seed_is_rejected(self) -> None:
        with self.assertRaises(EncodeError):
            ByteTransform.from_seed(b"", 0)
        with self.assertRaises(EncodeError):
            ByteTransform.from_seed(bytes(128), 0)
        with self.assertRaises(EncodeError):
            ByteTransform.from_seed(3, 0)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
