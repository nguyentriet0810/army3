"""Configuration for the loopback-only compatibility server."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 19150
    max_payload_bytes: int = 0xFFFF
    read_chunk_size: int = 4096
    backlog: int = 16
    heartbeat_interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.host, str):
            raise ValueError("host must be a numeric loopback address")
        try:
            address = ip_address(self.host)
        except ValueError as exc:
            raise ValueError("host must be a numeric loopback address") from exc
        if not address.is_loopback:
            raise ValueError("server may only bind to a loopback address")
        object.__setattr__(self, "host", str(address))

        self._validate_int("port", self.port, 0, 0xFFFF)
        self._validate_int("max_payload_bytes", self.max_payload_bytes, 0, 0xFFFF)
        self._validate_int("read_chunk_size", self.read_chunk_size, 1, 1024 * 1024)
        self._validate_int("backlog", self.backlog, 1, 1024)
        if (
            isinstance(self.heartbeat_interval_seconds, bool)
            or not isinstance(self.heartbeat_interval_seconds, (int, float))
            or not 0.1 <= self.heartbeat_interval_seconds <= 300.0
        ):
            raise ValueError(
                "heartbeat_interval_seconds must be between 0.1 and 300.0"
            )

    @staticmethod
    def _validate_int(name: str, value: int, minimum: int, maximum: int) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not minimum <= value <= maximum
        ):
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
