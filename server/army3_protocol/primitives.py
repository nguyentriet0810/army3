"""Strict big-endian readers and writers used by message codecs."""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import DecodeError, EncodeError


def _validate_uint(value: int, bits: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EncodeError(f"{field_name} must be an integer")
    maximum = (1 << bits) - 1
    if not 0 <= value <= maximum:
        raise EncodeError(f"{field_name} must be between 0 and {maximum}")
    return value


@dataclass(slots=True)
class ByteReader:
    """Consume a complete message payload without reading past its boundary."""

    data: bytes
    max_string_bytes: int = 0xFFFF
    _offset: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if not isinstance(self.data, (bytes, bytearray, memoryview)):
            raise DecodeError("payload must be bytes-like")
        self.data = bytes(self.data)
        if not 0 <= self.max_string_bytes <= 0xFFFF:
            raise ValueError("max_string_bytes must be between 0 and 65535")

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def remaining(self) -> int:
        return len(self.data) - self._offset

    def read_exact(self, size: int, field_name: str = "bytes") -> bytes:
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("size must be a non-negative integer")
        end = self._offset + size
        if end > len(self.data):
            raise DecodeError(
                f"truncated {field_name}: need {size} byte(s), "
                f"only {self.remaining} remain"
            )
        value = self.data[self._offset : end]
        self._offset = end
        return value

    def read_u8(self, field_name: str = "u8") -> int:
        return self.read_exact(1, field_name)[0]

    def read_u16(self, field_name: str = "u16") -> int:
        return int.from_bytes(self.read_exact(2, field_name), "big")

    def read_u32(self, field_name: str = "u32") -> int:
        return int.from_bytes(self.read_exact(4, field_name), "big")

    def read_string16(self, field_name: str = "string16") -> str:
        size = self.read_u16(f"{field_name}.length")
        if size > self.max_string_bytes:
            raise DecodeError(
                f"{field_name} length {size} exceeds limit {self.max_string_bytes}"
            )
        raw = self.read_exact(size, field_name)
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise DecodeError(f"{field_name} is not valid UTF-8") from exc

    def ensure_finished(self) -> None:
        if self.remaining:
            raise DecodeError(f"payload has {self.remaining} trailing byte(s)")


@dataclass(slots=True)
class ByteWriter:
    """Build a message payload using explicitly sized values."""

    _buffer: bytearray = field(init=False, default_factory=bytearray)

    def write_bytes(self, value: bytes | bytearray | memoryview) -> None:
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise EncodeError("value must be bytes-like")
        self._buffer.extend(value)

    def write_u8(self, value: int, field_name: str = "u8") -> None:
        self._buffer.append(_validate_uint(value, 8, field_name))

    def write_u16(self, value: int, field_name: str = "u16") -> None:
        self._buffer.extend(_validate_uint(value, 16, field_name).to_bytes(2, "big"))

    def write_u32(self, value: int, field_name: str = "u32") -> None:
        self._buffer.extend(_validate_uint(value, 32, field_name).to_bytes(4, "big"))

    def write_string16(self, value: str, field_name: str = "string16") -> None:
        if not isinstance(value, str):
            raise EncodeError(f"{field_name} must be a string")
        raw = value.encode("utf-8", errors="strict")
        if len(raw) > 0xFFFF:
            raise EncodeError(f"{field_name} exceeds 65535 UTF-8 bytes")
        self.write_u16(len(raw), f"{field_name}.length")
        self.write_bytes(raw)

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)
