"""List native method pointers from an IL2CPP object's class vtable.

The process is opened read-only through :mod:`tools.inspect_runtime_state` and
is rejected unless its executable belongs to the verified local client copy.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from tools.inspect_runtime_state import ProcessReader, RuntimeReadError
except ModuleNotFoundError:  # Direct execution: python tools/inspect_runtime_vtable.py
    from inspect_runtime_state import ProcessReader, RuntimeReadError


def inspect_vtable(
    reader: ProcessReader,
    module_base: int,
    object_address: int,
    start: int = 0x128,
    end: int = 0x308,
) -> list[dict[str, str]]:
    klass = reader.pointer(object_address)
    entries: list[dict[str, str]] = []
    for offset in range(start, end, 0x10):
        method = reader.pointer(klass + offset)
        if not method:
            continue
        entries.append(
            {
                "slot_offset": f"0x{offset:X}",
                "method": f"0x{method:X}",
                "rva": (
                    f"0x{method - module_base:X}" if method >= module_base else ""
                ),
            }
        )
    return entries


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--object", type=lambda value: int(value, 0), required=True)
    parser.add_argument(
        "--dump-size",
        type=lambda value: int(value, 0),
        default=0,
        help="also print this many raw object bytes (maximum 0x400)",
    )
    parser.add_argument(
        "--as-managed-string",
        action="store_true",
        help="interpret --object as a managed System.String and print it",
    )
    parser.add_argument(
        "--client-root",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "build"
        / "army3-local-client",
    )
    args = parser.parse_args()
    try:
        with ProcessReader(args.pid, args.client_root) as reader:
            module_base = reader.module_base("GameAssembly.dll")
            if args.as_managed_string:
                print(reader.managed_string(args.object))
            if args.dump_size:
                if not 0 < args.dump_size <= 0x400:
                    raise RuntimeReadError("--dump-size must be between 1 and 0x400")
                raw = reader.read(args.object, args.dump_size)
                for offset in range(0, len(raw), 16):
                    chunk = raw[offset : offset + 16]
                    print(f"object+0x{offset:03X}: {chunk.hex(' ')}")
            for entry in inspect_vtable(reader, module_base, args.object):
                print(
                    f"{entry['slot_offset']} method={entry['method']} "
                    f"rva={entry['rva']}"
                )
    except RuntimeReadError as exc:
        raise SystemExit(f"runtime vtable inspection failed: {exc}") from exc


if __name__ == "__main__":
    main()
