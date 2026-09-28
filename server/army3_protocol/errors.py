"""Protocol-specific exceptions."""


class ProtocolError(Exception):
    """Base class for protocol failures that should close a bad session."""


class EncodeError(ProtocolError, ValueError):
    """A Python value cannot be represented on the wire."""


class DecodeError(ProtocolError, ValueError):
    """A complete payload is structurally invalid."""


class FrameError(ProtocolError, ValueError):
    """A wire frame has an invalid header or declared size."""
