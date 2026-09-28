"""Binary protocol primitives and message codecs for the Army3 client."""

from .errors import DecodeError, EncodeError, FrameError, ProtocolError
from .framing import (
    LENGTH32_SERVER_COMMANDS,
    FrameDirection,
    FrameStreamDecoder,
    Packet,
    encode_frame,
)
from .transform import ByteTransform, TransformCursor

__all__ = [
    "ByteTransform",
    "DecodeError",
    "EncodeError",
    "FrameDirection",
    "FrameError",
    "FrameStreamDecoder",
    "LENGTH32_SERVER_COMMANDS",
    "Packet",
    "ProtocolError",
    "TransformCursor",
    "encode_frame",
]
