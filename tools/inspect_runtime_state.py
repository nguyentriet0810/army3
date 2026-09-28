"""Read selected Army3 IL2CPP bootstrap flags from a copied client process.

The tool opens the process with query/read rights only.  It refuses processes
whose executable is outside the verified local-copy directory.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import struct
import sys
from ctypes import wintypes


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_PATH = 260

BOOTSTRAP_FLAGS_TYPEINFO_RVA = 0x14545E8
UI_STATE_TYPEINFO_RVA = 0x1454500
UI_MANAGER_TYPEINFO_RVA = 0x1454620
POST_LOADING_TYPEINFO_RVA = 0x1454550
NETWORK_STATE_TYPEINFO_RVA = 0x1454618
WWW_HELPER_TYPEINFO_RVA = 0x1456030
IL2CPP_STATIC_FIELDS_OFFSET = 0xA0


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_ubyte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    ]


class RuntimeReadError(RuntimeError):
    pass


def _windows_api() -> ctypes.WinDLL:
    if os.name != "nt":
        raise RuntimeReadError("runtime inspection is supported only on Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Module32FirstW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MODULEENTRY32W),
    ]
    kernel32.Module32FirstW.restype = wintypes.BOOL
    kernel32.Module32NextW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MODULEENTRY32W),
    ]
    kernel32.Module32NextW.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    return kernel32


def _raise_last_error(action: str) -> None:
    code = ctypes.get_last_error()
    raise RuntimeReadError(f"{action} failed with Windows error {code}")


class ProcessReader:
    def __init__(self, pid: int, allowed_root: Path) -> None:
        self.pid = pid
        self.allowed_root = allowed_root.resolve()
        self.kernel32 = _windows_api()
        self.handle = self.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not self.handle:
            _raise_last_error("OpenProcess")
        try:
            executable = self.executable_path()
            try:
                executable.relative_to(self.allowed_root)
            except ValueError as exc:
                raise RuntimeReadError(
                    f"process executable is outside local copy: {executable}"
                ) from exc
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self) -> ProcessReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def executable_path(self) -> Path:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not self.kernel32.QueryFullProcessImageNameW(
            self.handle, 0, buffer, ctypes.byref(size)
        ):
            _raise_last_error("QueryFullProcessImageNameW")
        return Path(buffer.value).resolve()

    def module_base(self, module_name: str) -> int:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid
        )
        if snapshot == INVALID_HANDLE_VALUE:
            _raise_last_error("CreateToolhelp32Snapshot")
        try:
            entry = MODULEENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            if not self.kernel32.Module32FirstW(snapshot, ctypes.byref(entry)):
                _raise_last_error("Module32FirstW")
            while True:
                if entry.szModule.casefold() == module_name.casefold():
                    base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
                    if base is None:
                        raise RuntimeReadError(f"null module base: {module_name}")
                    return base
                if not self.kernel32.Module32NextW(snapshot, ctypes.byref(entry)):
                    break
        finally:
            self.kernel32.CloseHandle(snapshot)
        raise RuntimeReadError(f"module not found: {module_name}")

    def read(self, address: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        count = ctypes.c_size_t()
        if not self.kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(count),
        ):
            _raise_last_error(f"ReadProcessMemory at 0x{address:X}")
        if count.value != size:
            raise RuntimeReadError(
                f"short process read at 0x{address:X}: {count.value}/{size}"
            )
        return buffer.raw

    def pointer(self, address: int) -> int:
        return struct.unpack("<Q", self.read(address, 8))[0]

    def c_string(self, address: int, limit: int = 256) -> str:
        if not address:
            return ""
        raw = self.read(address, limit)
        return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")

    def managed_string(self, address: int, limit: int = 4096) -> str:
        if not address:
            return ""
        length = struct.unpack("<i", self.read(address + 0x10, 4))[0]
        if length < 0 or length > limit:
            raise RuntimeReadError(
                f"invalid managed string length {length} at 0x{address:X}"
            )
        return self.read(address + 0x14, length * 2).decode(
            "utf-16-le", errors="replace"
        )


def _object_type(reader: ProcessReader, object_address: int) -> dict[str, str]:
    if not object_address:
        return {"class": "", "namespace": ""}
    klass = reader.pointer(object_address)
    name = reader.pointer(klass + 0x10)
    namespace = reader.pointer(klass + 0x18)
    return {
        "class": reader.c_string(name),
        "namespace": reader.c_string(namespace),
    }


def _static_fields(reader: ProcessReader, module_base: int, typeinfo_rva: int) -> int:
    typeinfo = reader.pointer(module_base + typeinfo_rva)
    if not typeinfo:
        raise RuntimeReadError(f"null type-info pointer for RVA 0x{typeinfo_rva:X}")
    fields = reader.pointer(typeinfo + IL2CPP_STATIC_FIELDS_OFFSET)
    if not fields:
        raise RuntimeReadError(f"null static-fields pointer for RVA 0x{typeinfo_rva:X}")
    return fields


def inspect(pid: int, allowed_root: Path) -> dict[str, object]:
    with ProcessReader(pid, allowed_root) as reader:
        module_base = reader.module_base("GameAssembly.dll")
        flags = _static_fields(reader, module_base, BOOTSTRAP_FLAGS_TYPEINFO_RVA)
        ui = _static_fields(reader, module_base, UI_STATE_TYPEINFO_RVA)
        ui_manager = _static_fields(reader, module_base, UI_MANAGER_TYPEINFO_RVA)
        post_loading = _static_fields(reader, module_base, POST_LOADING_TYPEINFO_RVA)
        network_state = _static_fields(reader, module_base, NETWORK_STATE_TYPEINFO_RVA)
        www_helper = _static_fields(reader, module_base, WWW_HELPER_TYPEINFO_RVA)
        bootstrap_ui = reader.pointer(ui + 0x20)
        current_screen = reader.pointer(ui_manager + 0x50)
        current_type = _object_type(reader, current_screen)
        return {
            "pid": pid,
            "module_base": f"0x{module_base:X}",
            "bootstrap_flags": {
                "e1_0x188": reader.read(flags + 0x188, 1)[0],
                "e0_0x189": reader.read(flags + 0x189, 1)[0],
                "da_0x18a": reader.read(flags + 0x18A, 1)[0],
            },
            "ui_state": {
                "countdown_0x28": struct.unpack("<h", reader.read(ui + 0x28, 2))[0],
                "app_ready_0x40": reader.read(ui + 0x40, 1)[0],
                "bootstrap_ui_instance_0x20": f"0x{bootstrap_ui:X}",
            },
            "ui_manager": {
                "current_screen_0x50": f"0x{current_screen:X}",
                "current_is_bootstrap_ui": current_screen == bootstrap_ui,
                "current_screen_type": current_type,
                "current_screen_fields": {
                    "phase_a_0x30": reader.read(current_screen + 0x30, 1)[0],
                    "animation_index_0x34": struct.unpack(
                        "<i", reader.read(current_screen + 0x34, 4)
                    )[0],
                    "phase_b_0x38": reader.read(current_screen + 0x38, 1)[0],
                    "elapsed_0x3c": struct.unpack(
                        "<f", reader.read(current_screen + 0x3C, 4)
                    )[0],
                    "completion_fired_0x40": reader.read(current_screen + 0x40, 1)[0],
                },
            },
            "post_loading": {
                "asset_0x20": f"0x{reader.pointer(post_loading + 0x20):X}",
                "asset_type": _object_type(
                    reader, reader.pointer(post_loading + 0x20)
                ),
                "singleton_0x28": f"0x{reader.pointer(post_loading + 0x28):X}",
                "url_0x40": reader.managed_string(reader.pointer(post_loading + 0x40)),
                "text_0x48": reader.managed_string(reader.pointer(post_loading + 0x48)),
                "text_0x50": reader.managed_string(reader.pointer(post_loading + 0x50)),
            },
            "network_state": {
                "constant_0x10": struct.unpack(
                    "<i", reader.read(network_state + 0x10, 4)
                )[0],
                "constant_0x14": struct.unpack(
                    "<i", reader.read(network_state + 0x14, 4)
                )[0],
                "constant_0x18": struct.unpack(
                    "<i", reader.read(network_state + 0x18, 4)
                )[0],
                "current_0x1c": struct.unpack(
                    "<i", reader.read(network_state + 0x1C, 4)
                )[0],
            },
            "www_helper": {
                "request_0x0": f"0x{reader.pointer(www_helper):X}",
                "callback_0x8": f"0x{reader.pointer(www_helper + 0x8):X}",
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument(
        "--client-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "build" / "army3-local-client",
    )
    args = parser.parse_args()
    try:
        result = inspect(args.pid, args.client_root)
    except RuntimeReadError as exc:
        print(f"runtime inspection failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
