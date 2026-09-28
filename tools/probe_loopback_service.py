"""Capture a bounded prefix from an auxiliary loopback TCP connection.

This is a diagnostic tool for the copied client.  It refuses non-loopback
bind addresses and never forwards traffic.
"""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProbeConfig:
    host: str = "127.0.0.1"
    port: int = 443
    max_bytes: int = 4096
    read_timeout: float = 5.0

    def __post_init__(self) -> None:
        address = ipaddress.ip_address(self.host)
        if not address.is_loopback:
            raise ValueError("probe host must be a numeric loopback address")
        if not 1 <= self.port <= 65535:
            raise ValueError("probe port must be between 1 and 65535")
        if not 1 <= self.max_bytes <= 1_048_576:
            raise ValueError("max bytes must be between 1 and 1048576")
        if not 0.1 <= self.read_timeout <= 60:
            raise ValueError("read timeout must be between 0.1 and 60 seconds")


async def run_probe(config: ProbeConfig) -> None:
    connection_id = 0

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal connection_id
        connection_id += 1
        current = connection_id
        peer = writer.get_extra_info("peername")
        try:
            data = await asyncio.wait_for(
                reader.read(config.max_bytes), timeout=config.read_timeout
            )
            print(
                f"probe connection={current} peer={peer!r} bytes={len(data)} "
                f"hex={data.hex()}",
                flush=True,
            )
        except TimeoutError:
            print(f"probe connection={current} peer={peer!r} timeout", flush=True)
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, config.host, config.port)
    addresses = tuple(sock.getsockname() for sock in server.sockets or ())
    print(f"probe listening={addresses!r}", flush=True)
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--max-bytes", type=int, default=4096)
    parser.add_argument("--read-timeout", type=float, default=5.0)
    args = parser.parse_args()
    config = ProbeConfig(
        host=args.host,
        port=args.port,
        max_bytes=args.max_bytes,
        read_timeout=args.read_timeout,
    )
    try:
        asyncio.run(run_probe(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
