import unittest

from server.army3_protocol.errors import DecodeError, EncodeError
from server.army3_protocol.primitives import ByteReader, ByteWriter


class PrimitiveCodecTests(unittest.TestCase):
    def test_unsigned_values_and_utf8_round_trip(self) -> None:
        writer = ByteWriter()
        writer.write_u8(0xAB)
        writer.write_u16(0xCDEF)
        writer.write_u32(0x12345678)
        writer.write_string16("Việt Nam")

        reader = ByteReader(writer.to_bytes())
        self.assertEqual(reader.read_u8(), 0xAB)
        self.assertEqual(reader.read_u16(), 0xCDEF)
        self.assertEqual(reader.read_u32(), 0x12345678)
        self.assertEqual(reader.read_string16(), "Việt Nam")
        reader.ensure_finished()

    def test_big_endian_layout(self) -> None:
        writer = ByteWriter()
        writer.write_u16(0x1234)
        writer.write_u32(0x89ABCDEF)
        self.assertEqual(writer.to_bytes(), bytes.fromhex("12 34 89 AB CD EF"))

    def test_truncated_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(DecodeError, "truncated"):
            ByteReader(b"\x00").read_u16()

    def test_invalid_utf8_is_rejected(self) -> None:
        with self.assertRaisesRegex(DecodeError, "UTF-8"):
            ByteReader(b"\x00\x01\xff").read_string16()

    def test_string_limit_is_enforced(self) -> None:
        with self.assertRaisesRegex(DecodeError, "exceeds limit"):
            ByteReader(b"\x00\x03abc", max_string_bytes=2).read_string16()

    def test_trailing_bytes_are_rejected(self) -> None:
        reader = ByteReader(b"\x01\x02")
        reader.read_u8()
        with self.assertRaisesRegex(DecodeError, "trailing"):
            reader.ensure_finished()

    def test_out_of_range_integer_is_rejected(self) -> None:
        writer = ByteWriter()
        with self.assertRaises(EncodeError):
            writer.write_u8(256)
        with self.assertRaises(EncodeError):
            writer.write_u16(-1)

    def test_integer_is_not_silently_coerced_to_zero_bytes(self) -> None:
        with self.assertRaises(DecodeError):
            ByteReader(3)  # type: ignore[arg-type]
        with self.assertRaises(EncodeError):
            ByteWriter().write_bytes(3)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
