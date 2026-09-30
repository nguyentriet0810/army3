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
ACCOUNT_STATE_TYPEINFO_RVA = 0x1454640
ACCOUNT_MENU_DATA_TYPEINFO_RVA = 0x1454D90
FILE_IO_TYPEINFO_RVA = 0x1457D00
ITEM_TEMPLATES_TYPEINFO_RVA = 0x1455B10
LOCALIZATION_TYPEINFO_RVA = 0x1454648
IL2CPP_STATIC_FIELDS_OFFSET = 0xA0

E4_LOCALIZATION_IDS = (0x2B9, 0x3DB, 0x609, 0x692, 0x846, 0x88E)


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


def _virtual_method(reader: ProcessReader, object_address: int, slot_offset: int) -> int:
    if not object_address:
        return 0
    klass = reader.pointer(object_address)
    return reader.pointer(klass + slot_offset)


def _screen_controls(
    reader: ProcessReader, screen_address: int, limit: int = 8
) -> list[dict[str, object]]:
    array = reader.pointer(screen_address + 0x30)
    if not array:
        return []
    count = struct.unpack("<i", reader.read(array + 0x18, 4))[0]
    if count < 0 or count > limit:
        return [
            {
                "array": f"0x{array:X}",
                "reported_count": count,
                "error": "control array layout is not confirmed for this object",
            }
        ]
    controls: list[dict[str, object]] = []
    for index in range(count):
        control = reader.pointer(array + 0x20 + index * 8)
        label = reader.managed_string(reader.pointer(control + 0x18))
        x = struct.unpack("<i", reader.read(control + 0x40, 4))[0]
        y = struct.unpack("<i", reader.read(control + 0x44, 4))[0]
        width = struct.unpack("<i", reader.read(control + 0x48, 4))[0]
        height = struct.unpack("<i", reader.read(control + 0x50, 4))[0]
        controls.append(
            {
                "index": index,
                "address": f"0x{control:X}",
                "label": label,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }
        )
    return controls


def _static_fields(reader: ProcessReader, module_base: int, typeinfo_rva: int) -> int:
    typeinfo = reader.pointer(module_base + typeinfo_rva)
    if not typeinfo:
        raise RuntimeReadError(f"null type-info pointer for RVA 0x{typeinfo_rva:X}")
    fields = reader.pointer(typeinfo + IL2CPP_STATIC_FIELDS_OFFSET)
    if not fields:
        raise RuntimeReadError(f"null static-fields pointer for RVA 0x{typeinfo_rva:X}")
    return fields


def _array_length(reader: ProcessReader, array: int) -> int:
    if not array:
        raise RuntimeReadError("null managed array")
    length = struct.unpack("<i", reader.read(array + 0x18, 4))[0]
    if length < 0:
        raise RuntimeReadError(f"negative managed array length {length}")
    return length


def _localization_text(reader: ProcessReader, fields: int, text_id: int) -> str:
    """Decode one localization entry without invoking code in the client.

    ``FUN_1801BA350`` caches decoded strings in the array at ``+0x18``.  If an
    entry has not been requested yet, it reconstructs encrypted UTF-16LE bytes
    from three primitive arrays at ``+0x0``, ``+0x8`` and ``+0x10``.  Mirroring
    that read-only algorithm lets the runtime probe name UI controls without
    modifying the copied client process.
    """

    if text_id < 0:
        raise RuntimeReadError(f"negative localization id {text_id}")

    cache = reader.pointer(fields + 0x18)
    if text_id >= _array_length(reader, cache):
        raise RuntimeReadError(f"localization id 0x{text_id:X} exceeds cache")
    cached = reader.pointer(cache + 0x20 + text_id * 8)
    if cached:
        return reader.managed_string(cached)

    packed = reader.pointer(fields)
    offsets = reader.pointer(fields + 0x8)
    lengths = reader.pointer(fields + 0x10)
    if text_id >= _array_length(reader, offsets):
        raise RuntimeReadError(f"localization id 0x{text_id:X} exceeds offsets")
    if text_id >= _array_length(reader, lengths):
        raise RuntimeReadError(f"localization id 0x{text_id:X} exceeds lengths")

    byte_length = struct.unpack(
        "<i", reader.read(lengths + 0x20 + text_id * 4, 4)
    )[0]
    packed_offset = struct.unpack(
        "<i", reader.read(offsets + 0x20 + text_id * 4, 4)
    )[0]
    if byte_length < 0 or byte_length > 0x10000:
        raise RuntimeReadError(
            f"invalid localization byte length {byte_length} for 0x{text_id:X}"
        )
    required_words = (byte_length + 3) // 4
    if packed_offset < 0 or packed_offset + required_words > _array_length(
        reader, packed
    ):
        raise RuntimeReadError(f"invalid localization span for 0x{text_id:X}")

    encrypted = bytearray(byte_length)
    for index in range(byte_length):
        word = struct.unpack(
            "<I",
            reader.read(packed + 0x20 + (packed_offset + index // 4) * 4, 4),
        )[0]
        encrypted[index] = (word >> ((index & 3) * 8)) & 0xFF

    state = ((text_id * -0x7A143589 + 0x85EBCA77) & 0xFFFFFFFF) ^ 0x046480DF
    for index in range(byte_length):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        state &= 0xFFFFFFFF
        encrypted[index] ^= state & 0xFF
    if byte_length % 2:
        raise RuntimeReadError(
            f"odd UTF-16 localization byte length {byte_length} for 0x{text_id:X}"
        )
    return encrypted.decode("utf-16-le", errors="replace")


def inspect(pid: int, allowed_root: Path) -> dict[str, object]:
    with ProcessReader(pid, allowed_root) as reader:
        module_base = reader.module_base("GameAssembly.dll")
        flags = _static_fields(reader, module_base, BOOTSTRAP_FLAGS_TYPEINFO_RVA)
        ui = _static_fields(reader, module_base, UI_STATE_TYPEINFO_RVA)
        ui_manager = _static_fields(reader, module_base, UI_MANAGER_TYPEINFO_RVA)
        post_loading = _static_fields(reader, module_base, POST_LOADING_TYPEINFO_RVA)
        network_state = _static_fields(reader, module_base, NETWORK_STATE_TYPEINFO_RVA)
        www_helper = _static_fields(reader, module_base, WWW_HELPER_TYPEINFO_RVA)
        account_state = _static_fields(
            reader, module_base, ACCOUNT_STATE_TYPEINFO_RVA
        )
        account_menu_data = _static_fields(
            reader, module_base, ACCOUNT_MENU_DATA_TYPEINFO_RVA
        )
        file_io = _static_fields(reader, module_base, FILE_IO_TYPEINFO_RVA)
        item_templates = _static_fields(
            reader, module_base, ITEM_TEMPLATES_TYPEINFO_RVA
        )
        localization = _static_fields(
            reader, module_base, LOCALIZATION_TYPEINFO_RVA
        )
        bootstrap_ui = reader.pointer(ui + 0x20)
        bootstrap_activation = _virtual_method(reader, bootstrap_ui, 0x1A8)
        current_screen = reader.pointer(ui_manager + 0x50)
        splash_screen = reader.pointer(ui_manager + 0x58)
        c4_target_screen = reader.pointer(ui_manager + 0x70)
        input_dialog_screen = reader.pointer(ui_manager + 0x80)
        ui_aux_88 = reader.pointer(ui_manager + 0x88)
        ui_aux_98 = reader.pointer(ui_manager + 0x98)
        ui_overlay_a0 = reader.pointer(ui_manager + 0xA0)
        area_screen = reader.pointer(ui_manager + 0xA8)
        ui_screen_60 = reader.pointer(ui_manager + 0x60)
        ui_aux_d0 = reader.pointer(ui_manager + 0xD0)
        current_type = _object_type(reader, current_screen)
        current_activation = _virtual_method(reader, current_screen, 0x1A8)
        input_dialog_activation = _virtual_method(
            reader, input_dialog_screen, 0x1A8
        )
        area_record = reader.pointer(area_screen + 0x230) if area_screen else 0
        selected_profile = reader.pointer(account_state + 0x30)
        account_menu_entries = reader.pointer(account_menu_data + 0x48)
        account_menu_active_values = reader.pointer(account_menu_data + 0x70)
        file_buffer = reader.pointer(file_io + 0x8)
        item_groups = reader.pointer(flags + 0x20)
        item_dictionary = reader.pointer(item_templates)
        item_hashtable = (
            reader.pointer(item_dictionary + 0x10) if item_dictionary else 0
        )
        return {
            "pid": pid,
            "module_base": f"0x{module_base:X}",
            "bootstrap_flags": {
                "e1_0x188": reader.read(flags + 0x188, 1)[0],
                "e0_0x189": reader.read(flags + 0x189, 1)[0],
                "da_0x18a": reader.read(flags + 0x18A, 1)[0],
                "c4_cached_version_0x300": struct.unpack(
                    "<i", reader.read(flags + 0x300, 4)
                )[0],
                "c4_revision_0x304": struct.unpack(
                    "<b", reader.read(flags + 0x304, 1)
                )[0],
            },
            "ui_state": {
                "countdown_0x28": struct.unpack("<h", reader.read(ui + 0x28, 2))[0],
                "app_ready_0x40": reader.read(ui + 0x40, 1)[0],
                "bootstrap_ui_instance_0x20": f"0x{bootstrap_ui:X}",
                "bootstrap_ui_type": _object_type(reader, bootstrap_ui),
                "activation_slot_0x1a8": f"0x{bootstrap_activation:X}",
                "activation_rva": (
                    f"0x{bootstrap_activation - module_base:X}"
                    if bootstrap_activation >= module_base
                    else ""
                ),
            },
            "ui_manager": {
                "current_screen_0x50": f"0x{current_screen:X}",
                "splash_screen_0x58": f"0x{splash_screen:X}",
                "c4_target_screen_0x70": f"0x{c4_target_screen:X}",
                "input_dialog_screen_0x80": f"0x{input_dialog_screen:X}",
                "input_dialog_screen_type": _object_type(
                    reader, input_dialog_screen
                ),
                "input_dialog_activation_slot_0x1a8": (
                    f"0x{input_dialog_activation:X}"
                ),
                "input_dialog_activation_rva": (
                    f"0x{input_dialog_activation - module_base:X}"
                    if input_dialog_activation >= module_base
                    else ""
                ),
                "screen_0x60": f"0x{ui_screen_60:X}",
                "screen_0x60_type": _object_type(reader, ui_screen_60),
                "current_is_bootstrap_ui": current_screen == bootstrap_ui,
                "current_is_splash_screen": current_screen == splash_screen,
                "current_is_c4_target_screen": current_screen == c4_target_screen,
                "current_screen_type": current_type,
                "aux_0x88": f"0x{ui_aux_88:X}",
                "aux_0x88_type": _object_type(reader, ui_aux_88),
                "aux_0x98": f"0x{ui_aux_98:X}",
                "aux_0x98_type": _object_type(reader, ui_aux_98),
                # FUN_18043E3D0 suppresses the login panel while this pointer
                # is non-null, so it is a candidate loading/modal overlay.
                "overlay_0xa0": f"0x{ui_overlay_a0:X}",
                "overlay_0xa0_type": _object_type(reader, ui_overlay_a0),
                "area_screen_0xa8": f"0x{area_screen:X}",
                "area_screen_type": _object_type(reader, area_screen),
                "area_record_0x230": f"0x{area_record:X}",
                "area_record_type": _object_type(reader, area_record),
                "area_record_fields": (
                    {
                        "area_id_0x10": struct.unpack(
                            "<b", reader.read(area_record + 0x10, 1)
                        )[0],
                        "flag_0x11": reader.read(area_record + 0x11, 1)[0],
                        "derived_0x12": struct.unpack(
                            "<b", reader.read(area_record + 0x12, 1)
                        )[0],
                        "flag_0x13": reader.read(area_record + 0x13, 1)[0],
                        "name_0x18": reader.managed_string(
                            reader.pointer(area_record + 0x18)
                        ),
                        "money_0x30": struct.unpack(
                            "<I", reader.read(area_record + 0x30, 4)
                        )[0],
                    }
                    if area_record
                    else None
                ),
                "aux_0xd0": f"0x{ui_aux_d0:X}",
                "aux_0xd0_type": _object_type(reader, ui_aux_d0),
                "current_activation_slot_0x1a8": f"0x{current_activation:X}",
                "current_activation_rva": (
                    f"0x{current_activation - module_base:X}"
                    if current_activation >= module_base
                    else ""
                ),
                # The +0x30 control-array layout is confirmed only for the
                # 0xC4 target screen. Other screen classes reuse that offset.
                "controls": (
                    _screen_controls(reader, current_screen)
                    if current_screen == c4_target_screen
                    else []
                ),
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
                "cache_hit_0x84": reader.read(post_loading + 0x84, 1)[0],
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
            "account_state": {
                "selected_profile_0x30": f"0x{selected_profile:X}",
                "selected_profile_type": _object_type(reader, selected_profile),
                # FUN_1801A2DB0 branches on this field when the first menu
                # action (the visible \"Chơi mới\" button) is activated.
                "entry_count_0x358": (
                    struct.unpack("<i", reader.read(selected_profile + 0x358, 4))[0]
                    if selected_profile
                    else None
                ),
            },
            "account_menu_data": {
                # FUN_1801A7C90 uses entries 6 and 8 while constructing the
                # local "Choi moi" view, depending on these selector bytes.
                "selector_0x0": struct.unpack(
                    "<b", reader.read(account_menu_data, 1)
                )[0],
                "selector_boundary_0x3": struct.unpack(
                    "<b", reader.read(account_menu_data + 0x3, 1)
                )[0],
                "selected_index_0x50": struct.unpack(
                    "<i", reader.read(account_menu_data + 0x50, 4)
                )[0],
                "entry_array_0x48": f"0x{account_menu_entries:X}",
                "entry_count": (
                    struct.unpack(
                        "<i", reader.read(account_menu_entries + 0x18, 4)
                    )[0]
                    if account_menu_entries
                    else None
                ),
                "active_values_0x70": f"0x{account_menu_active_values:X}",
                "active_value_count": (
                    struct.unpack(
                        "<i", reader.read(account_menu_active_values + 0x18, 4)
                    )[0]
                    if account_menu_active_values
                    else None
                ),
            },
            "file_io": {
                # The helper uses 2 for a pending write, 3 for a pending read,
                # 1 while executing and 0 when idle.
                "state_0x0": struct.unpack("<i", reader.read(file_io, 4))[0],
                "buffer_0x8": f"0x{file_buffer:X}",
                "buffer_length": (
                    struct.unpack("<i", reader.read(file_buffer + 0x18, 4))[0]
                    if file_buffer
                    else None
                ),
                "path_0x10": reader.managed_string(reader.pointer(file_io + 0x10)),
            },
            "item_data": {
                "group_array_0x20": f"0x{item_groups:X}",
                "group_array_type": _object_type(reader, item_groups),
                "group_count": (
                    struct.unpack("<i", reader.read(item_groups + 0x18, 4))[0]
                    if item_groups
                    else None
                ),
                "template_dictionary": f"0x{item_dictionary:X}",
                "template_dictionary_type": _object_type(
                    reader, item_dictionary
                ),
                "template_count": (
                    struct.unpack("<i", reader.read(item_hashtable + 0x18, 4))[0]
                    if item_hashtable
                    else None
                ),
                "stored_revision_0x2f0": struct.unpack(
                    "<i", reader.read(flags + 0x2F0, 4)
                )[0],
            },
            "e4_localization": {
                f"0x{text_id:X}": _localization_text(
                    reader, localization, text_id
                )
                for text_id in E4_LOCALIZATION_IDS
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
