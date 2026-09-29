"""Confirmed message schemas needed by the local-login bootstrap path."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .errors import DecodeError, EncodeError
from .framing import Packet
from .primitives import ByteReader, ByteWriter


class Command(IntEnum):
    UNKNOWN_07 = 0x07
    POST_RESET_STATUS = 0x3A
    CLIENT_TEXT_72 = 0x72
    HEARTBEAT = 0x9A
    TRANSPORT_SYNC = 0xA9
    CLIENT_U32_B2 = 0xB2
    CLIENT_SESSION = 0xBB
    SCREEN_BOOTSTRAP = 0xC4
    BOOTSTRAP_DA = 0xDA
    BOOTSTRAP_READY = 0xDB
    BOOTSTRAP_E0 = 0xE0
    BOOTSTRAP_E1 = 0xE1
    BOOTSTRAP_VERSIONS = 0xE2
    HANDSHAKE = 0xE5
    PRELOGIN_STATUS = 0xFD


def _reader(payload: bytes) -> ByteReader:
    return ByteReader(payload)


def _empty_packet(command: Command) -> Packet:
    return Packet(command, b"")


@dataclass(frozen=True, slots=True)
class EmptyClientRequest:
    command: Command

    def __post_init__(self) -> None:
        if self.command not in {
            Command.UNKNOWN_07,
            Command.BOOTSTRAP_DA,
            Command.BOOTSTRAP_READY,
            Command.BOOTSTRAP_E0,
            Command.BOOTSTRAP_E1,
            Command.HANDSHAKE,
            Command.PRELOGIN_STATUS,
            Command.SCREEN_BOOTSTRAP,
        }:
            raise EncodeError(f"0x{int(self.command):02X} is not a known empty request")

    def to_packet(self) -> Packet:
        return _empty_packet(self.command)

    @classmethod
    def from_packet(cls, packet: Packet) -> EmptyClientRequest:
        try:
            command = Command(packet.command)
        except ValueError as exc:
            raise DecodeError(f"unknown empty request command 0x{packet.command:02X}") from exc
        if packet.payload:
            raise DecodeError(
                f"empty request 0x{packet.command:02X} has {len(packet.payload)} payload byte(s)"
            )
        return cls(command)


@dataclass(frozen=True, slots=True)
class HandshakeResponse:
    seed: bytes
    shift: int
    text: str

    def encode_payload(self) -> bytes:
        if not isinstance(self.seed, (bytes, bytearray, memoryview)):
            raise EncodeError("handshake seed must be bytes-like")
        seed = bytes(self.seed)
        if not 1 <= len(seed) <= 0x7F:
            raise EncodeError("handshake seed length must be between 1 and 127")
        writer = ByteWriter()
        writer.write_u8(len(seed), "seed.length")
        writer.write_bytes(seed)
        writer.write_u8(self.shift, "shift")
        writer.write_string16(self.text, "text")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.HANDSHAKE, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> HandshakeResponse:
        reader = _reader(payload)
        seed_length = reader.read_u8("seed.length")
        if not 1 <= seed_length <= 0x7F:
            raise DecodeError("handshake seed length must be between 1 and 127")
        seed = reader.read_exact(seed_length, "seed")
        shift = reader.read_u8("shift")
        text = reader.read_string16("text")
        reader.ensure_finished()
        return cls(seed, shift, text)


@dataclass(frozen=True, slots=True)
class ClientSessionRequest:
    """Two text controls and the mode byte sent by command 0xBB."""

    field_from_control38: str
    field_from_control30: str
    mode: int

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_string16(self.field_from_control38, "field_from_control38")
        writer.write_string16(self.field_from_control30, "field_from_control30")
        writer.write_u8(self.mode, "mode")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.CLIENT_SESSION, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ClientSessionRequest:
        reader = _reader(payload)
        first = reader.read_string16("field_from_control38")
        second = reader.read_string16("field_from_control30")
        mode = reader.read_u8("mode")
        reader.ensure_finished()
        return cls(first, second, mode)


@dataclass(frozen=True, slots=True)
class ClientTransportSync0:
    """Client 0xA9/subcommand 0 observed after the 0xE5 response."""

    stored_text: str
    counter94: int
    counter90: int

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(0, "subcommand")
        writer.write_string16(self.stored_text, "stored_text")
        writer.write_u32(self.counter94, "counter94")
        writer.write_u32(self.counter90, "counter90")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.TRANSPORT_SYNC, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ClientTransportSync0:
        reader = _reader(payload)
        subcommand = reader.read_u8("subcommand")
        if subcommand != 0:
            raise DecodeError(f"unsupported client 0xA9 subcommand {subcommand}")
        result = cls(
            reader.read_string16("stored_text"),
            reader.read_u32("counter94"),
            reader.read_u32("counter90"),
        )
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ServerTransportReset2:
    """Server 0xA9/subcommand 2 asks the client to reset transport counters."""

    def encode_payload(self) -> bytes:
        return b"\x02"

    def to_packet(self) -> Packet:
        return Packet(Command.TRANSPORT_SYNC, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ServerTransportReset2:
        reader = _reader(payload)
        subcommand = reader.read_u8("subcommand")
        reader.ensure_finished()
        if subcommand != 2:
            raise DecodeError(f"expected server 0xA9 subcommand 2, got {subcommand}")
        return cls()


@dataclass(frozen=True, slots=True)
class ClientPostResetStatus:
    """One-byte client status observed immediately after server 0xA9/2.

    The payload shape and ordering are runtime-confirmed.  The semantic
    meaning of ``value`` remains unknown, so the compatibility server only
    validates and acknowledges receipt by continuing the state machine.
    """

    value: int

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.value, "value")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.POST_RESET_STATUS, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ClientPostResetStatus:
        reader = _reader(payload)
        result = cls(reader.read_u8("value"))
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ClientPrelogin72:
    """Two bytes plus one string16 sent before the session request.

    The field shape is confirmed by the native sender and the ordering is
    confirmed at runtime.  The fields' business meanings remain unknown.
    """

    value1: int
    value2: int
    text: str

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.value1, "value1")
        writer.write_u8(self.value2, "value2")
        writer.write_string16(self.text, "text")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.CLIENT_TEXT_72, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ClientPrelogin72:
        reader = _reader(payload)
        result = cls(
            reader.read_u8("value1"),
            reader.read_u8("value2"),
            reader.read_string16("text"),
        )
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ServerPreloginStatus:
    """One-byte 0xFD response; value 1 is the inferred local success status."""

    value: int = 1

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.value, "value")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.PRELOGIN_STATUS, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ServerPreloginStatus:
        reader = _reader(payload)
        result = cls(reader.read_u8("value"))
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ClientU32B2:
    """One u32 client message observed after the initial 0xBB exchange."""

    value: int

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u32(self.value, "value")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.CLIENT_U32_B2, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ClientU32B2:
        reader = _reader(payload)
        result = cls(reader.read_u32("value"))
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ServerSessionResponse:
    list_for_mode1: str
    raw_for_mode1: str
    list_for_mode0: str
    raw_for_mode0: str

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_string16(self.list_for_mode1, "list_for_mode1")
        writer.write_string16(self.raw_for_mode1, "raw_for_mode1")
        writer.write_string16(self.list_for_mode0, "list_for_mode0")
        writer.write_string16(self.raw_for_mode0, "raw_for_mode0")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.CLIENT_SESSION, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ServerSessionResponse:
        reader = _reader(payload)
        values = [reader.read_string16(f"value{index}") for index in range(4)]
        reader.ensure_finished()
        return cls(*values)


@dataclass(frozen=True, slots=True)
class BootstrapVersions:
    e1_version: int
    e0_version: int
    da_version: int

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.e1_version, "e1_version")
        writer.write_u8(self.e0_version, "e0_version")
        writer.write_u8(self.da_version, "da_version")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.BOOTSTRAP_VERSIONS, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> BootstrapVersions:
        reader = _reader(payload)
        result = cls(
            reader.read_u8("e1_version"),
            reader.read_u8("e0_version"),
            reader.read_u8("da_version"),
        )
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class ScreenBootstrapResponse:
    """Confirmed minimal 0xC4/selector-0 screen-activation branch.

    ``revision`` is compared as a signed byte by the client. Its business
    meaning and the meaning of ``text`` remain unknown.
    """

    revision: int
    text: str = ""

    def encode_payload(self) -> bytes:
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or not -128 <= self.revision <= 127
        ):
            raise EncodeError("screen bootstrap revision must be an s8")
        writer = ByteWriter()
        writer.write_u8(0, "selector")
        writer.write_u8(self.revision & 0xFF, "revision")
        writer.write_string16(self.text, "text")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.SCREEN_BOOTSTRAP, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> ScreenBootstrapResponse:
        reader = _reader(payload)
        selector = reader.read_u8("selector")
        if selector != 0:
            raise DecodeError(f"expected 0xC4 selector 0, got {selector}")
        raw_revision = reader.read_u8("revision")
        revision = raw_revision if raw_revision < 0x80 else raw_revision - 0x100
        result = cls(revision, reader.read_string16("text"))
        reader.ensure_finished()
        return result


@dataclass(frozen=True, slots=True)
class BootstrapDaResponse:
    version: int
    blob: bytes

    @classmethod
    def empty(cls, version: int = 1) -> BootstrapDaResponse:
        return cls(version, b"\x00")

    def encode_payload(self) -> bytes:
        if not isinstance(self.blob, (bytes, bytearray, memoryview)):
            raise EncodeError("blob must be bytes-like")
        blob = bytes(self.blob)
        writer = ByteWriter()
        writer.write_u8(self.version, "version")
        writer.write_u32(len(blob), "blob.length")
        writer.write_bytes(blob)
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.BOOTSTRAP_DA, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> BootstrapDaResponse:
        reader = _reader(payload)
        version = reader.read_u8("version")
        blob_length = reader.read_u32("blob.length")
        blob = reader.read_exact(blob_length, "blob")
        reader.ensure_finished()
        return cls(version, blob)


@dataclass(frozen=True, slots=True)
class BootstrapE1Response:
    version: int
    blob1: bytes
    blob2: bytes
    blob3: bytes

    @classmethod
    def empty(cls, version: int = 1) -> BootstrapE1Response:
        return cls(version, b"\x00\x00", b"\x00\x00", b"\x00")

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.version, "version")
        for index, blob in enumerate((self.blob1, self.blob2, self.blob3), 1):
            if not isinstance(blob, (bytes, bytearray, memoryview)):
                raise EncodeError(f"blob{index} must be bytes-like")
            normalized_blob = bytes(blob)
            writer.write_u32(len(normalized_blob), f"blob{index}.length")
            writer.write_bytes(normalized_blob)
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.BOOTSTRAP_E1, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> BootstrapE1Response:
        reader = _reader(payload)
        version = reader.read_u8("version")
        blobs: list[bytes] = []
        for index in range(1, 4):
            size = reader.read_u32(f"blob{index}.length")
            blobs.append(reader.read_exact(size, f"blob{index}"))
        reader.ensure_finished()
        return cls(version, *blobs)


@dataclass(frozen=True, slots=True)
class BootstrapE0EmptyResponse:
    """Only the confirmed empty-collection subset of the 0xE0 schema."""

    version: int = 1

    def encode_payload(self) -> bytes:
        writer = ByteWriter()
        writer.write_u8(self.version, "version")
        writer.write_u8(0, "first_count")
        writer.write_u16(0, "second_count")
        return writer.to_bytes()

    def to_packet(self) -> Packet:
        return Packet(Command.BOOTSTRAP_E0, self.encode_payload())

    @classmethod
    def decode_payload(cls, payload: bytes) -> BootstrapE0EmptyResponse:
        reader = _reader(payload)
        version = reader.read_u8("version")
        first_count = reader.read_u8("first_count")
        second_count = reader.read_u16("second_count")
        reader.ensure_finished()
        if first_count != 0 or second_count != 0:
            raise DecodeError(
                "non-empty 0xE0 records are outside the confirmed M4 schema"
            )
        return cls(version)
