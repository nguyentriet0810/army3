"""Direction-aware packet framing and an incremental stream decoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .errors import FrameError
from .transform import TransformCursor


LENGTH32_SERVER_COMMANDS = frozenset({0x88, 0xA4, 0xC4, 0xD7, 0xE1})


class FrameDirection(Enum):
    """Wire direction, used because only server responses have length-32 frames."""

    CLIENT_TO_SERVER = "client_to_server"
    SERVER_TO_CLIENT = "server_to_client"


@dataclass(frozen=True, slots=True)
class Packet:
    command: int
    payload: bytes = b""

    def __post_init__(self) -> None:
        if isinstance(self.command, bool) or not isinstance(self.command, int):
            raise FrameError("command must be an integer")
        if not 0 <= self.command <= 0xFF:
            raise FrameError("command must be between 0 and 255")
        if not isinstance(self.payload, (bytes, bytearray, memoryview)):
            raise FrameError("payload must be bytes-like")
        normalized_payload = bytes(self.payload)
        object.__setattr__(self, "payload", normalized_payload)


def _uses_length32(command: int, direction: FrameDirection) -> bool:
    return (
        direction is FrameDirection.SERVER_TO_CLIENT
        and command in LENGTH32_SERVER_COMMANDS
    )


def encode_frame(
    packet: Packet,
    direction: FrameDirection,
    cursor: TransformCursor | None = None,
) -> bytes:
    """Encode one frame and advance only the supplied direction cursor."""

    if not isinstance(packet, Packet):
        raise TypeError("packet must be a Packet")
    if not isinstance(direction, FrameDirection):
        raise TypeError("direction must be a FrameDirection")

    length32 = _uses_length32(packet.command, direction)
    length_width = 4 if length32 else 2
    maximum = 0xFFFFFFFF if length32 else 0xFFFF
    if len(packet.payload) > maximum:
        raise FrameError(
            f"payload length {len(packet.payload)} exceeds {length_width}-byte limit"
        )

    length_bytes = len(packet.payload).to_bytes(length_width, "big")
    if cursor is None:
        return bytes((packet.command,)) + length_bytes + packet.payload

    output = bytearray((cursor.encode_command(packet.command),))
    if length32:
        # Confirmed client receive path transforms only the command for this set.
        output.extend(length_bytes)
        output.extend(packet.payload)
        return bytes(output)

    for value in length_bytes:
        output.append(cursor.encode_data(value))
    for value in packet.payload:
        output.append(cursor.encode_data(value))
    return bytes(output)


@dataclass(slots=True)
class FrameStreamDecoder:
    """Decode fragmented or coalesced frames without speculative cursor drift."""

    direction: FrameDirection
    cursor: TransformCursor | None = None
    max_payload_bytes: int = 0xFFFF
    _buffer: bytearray = field(init=False, default_factory=bytearray)

    def __post_init__(self) -> None:
        if not isinstance(self.direction, FrameDirection):
            raise TypeError("direction must be a FrameDirection")
        if (
            isinstance(self.max_payload_bytes, bool)
            or not isinstance(self.max_payload_bytes, int)
            or self.max_payload_bytes < 0
        ):
            raise ValueError("max_payload_bytes must be a non-negative integer")

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)

    def feed(
        self,
        data: bytes | bytearray | memoryview,
        *,
        max_packets: int | None = None,
    ) -> list[Packet]:
        """Append bytes and decode up to ``max_packets`` complete frames.

        Limiting this to one lets a transport change transform state after a
        handshake while leaving already-buffered bytes untouched.
        """

        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise FrameError("stream data must be bytes-like")
        if max_packets is not None and (
            isinstance(max_packets, bool)
            or not isinstance(max_packets, int)
            or max_packets <= 0
        ):
            raise ValueError("max_packets must be a positive integer or None")
        self._buffer.extend(data)

        packets: list[Packet] = []
        while True:
            if max_packets is not None and len(packets) >= max_packets:
                return packets
            packet = self._decode_one()
            if packet is None:
                return packets
            packets.append(packet)

    def _restore(self, checkpoint: int | None) -> None:
        if self.cursor is not None and checkpoint is not None:
            self.cursor.restore(checkpoint)

    def _decode_one(self) -> Packet | None:
        if not self._buffer:
            return None

        checkpoint = self.cursor.checkpoint() if self.cursor is not None else None
        raw_command = self._buffer[0]
        command = (
            self.cursor.decode_command(raw_command)
            if self.cursor is not None
            else raw_command
        )
        length32 = _uses_length32(command, self.direction)
        length_width = 4 if length32 else 2
        header_size = 1 + length_width

        if len(self._buffer) < header_size:
            self._restore(checkpoint)
            return None

        raw_length = self._buffer[1:header_size]
        if self.cursor is not None and not length32:
            length_bytes = bytes(self.cursor.decode_data(value) for value in raw_length)
        else:
            length_bytes = bytes(raw_length)
        payload_size = int.from_bytes(length_bytes, "big")

        if payload_size > self.max_payload_bytes:
            self._restore(checkpoint)
            raise FrameError(
                f"declared payload length {payload_size} exceeds limit "
                f"{self.max_payload_bytes}"
            )

        frame_size = header_size + payload_size
        if len(self._buffer) < frame_size:
            self._restore(checkpoint)
            return None

        raw_payload = self._buffer[header_size:frame_size]
        if self.cursor is not None and not length32:
            payload = bytes(self.cursor.decode_data(value) for value in raw_payload)
        else:
            payload = bytes(raw_payload)

        del self._buffer[:frame_size]
        return Packet(command, payload)
