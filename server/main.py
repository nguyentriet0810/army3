"""Command-line entry point for the local compatibility server."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence

from .app import serve_forever
from .config import ServerConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Army3 loopback compatibility server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19150)
    parser.add_argument("--heartbeat-interval", type=float, default=10.0)
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
    )
    try:
        config = ServerConfig(
            host=args.host,
            port=args.port,
            heartbeat_interval_seconds=args.heartbeat_interval,
        )
        asyncio.run(serve_forever(config))
    except ValueError as exc:
        build_parser().error(str(exc))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
