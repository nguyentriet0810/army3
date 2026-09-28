"""Stateful byte transformation established by the 0xE5 handshake."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import EncodeError


@dataclass(frozen=True, slots=True)
class ByteTransform:
    """Immutable effective key and command shift shared by both directions."""

    key: bytes
    shift: int

    def __post_init__(self) -> None:
        if not isinstance(self.key, (bytes, bytearray, memoryview)):
            raise EncodeError("transform key must be bytes-like")
        normalized_key = bytes(self.key)
        if not normalized_key:
            raise EncodeError("transform key must not be empty")
        if len(normalized_key) > 0x7F:
            raise EncodeError("transform key is limited to 127 bytes")
        if isinstance(self.shift, bool) or not isinstance(self.shift, int):
            raise EncodeError("transform shift must be an integer")
        if not 0 <= self.shift <= 0xFF:
            raise EncodeError("transform shift must be between 0 and 255")
        object.__setattr__(self, "key", normalized_key)

    @classmethod
    def from_seed(cls, seed: bytes, shift: int) -> ByteTransform:
        """Convert the handshake seed to the client's prefix-XOR key."""

        if not isinstance(seed, (bytes, bytearray, memoryview)):
            raise EncodeError("transform seed must be bytes-like")
        source = bytes(seed)
        if not source:
            raise EncodeError("transform seed must not be empty")
        effective = bytearray(source)
        for index in range(1, len(effective)):
            effective[index] ^= effective[index - 1]
        return cls(bytes(effective), shift)

    def cursor(self) -> TransformCursor:
        return TransformCursor(self)


@dataclass(slots=True)
class TransformCursor:
    """One independent wire-direction cursor over a transform key."""

    transform: ByteTransform
    _index: int = 0

    @property
    def index(self) -> int:
        return self._index

    def checkpoint(self) -> int:
        return self._index

    def restore(self, checkpoint: int) -> None:
        if not 0 <= checkpoint < len(self.transform.key):
            raise ValueError("checkpoint is outside the transform key")
        self._index = checkpoint

    def _xor_next(self, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFF:
            raise ValueError("transformed value must be one byte")
        result = value ^ self.transform.key[self._index]
        self._index = (self._index + 1) % len(self.transform.key)
        return result

    def encode_command(self, logical_command: int) -> int:
        if (
            isinstance(logical_command, bool)
            or not isinstance(logical_command, int)
            or not 0 <= logical_command <= 0xFF
        ):
            raise ValueError("logical command must be one byte")
        shifted = (logical_command + self.transform.shift) & 0xFF
        return self._xor_next(shifted)

    def decode_command(self, raw_command: int) -> int:
        return (self._xor_next(raw_command) - self.transform.shift) & 0xFF

    def encode_data(self, value: int) -> int:
        return self._xor_next(value)

    def decode_data(self, value: int) -> int:
        return self._xor_next(value)
