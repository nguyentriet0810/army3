from __future__ import annotations

import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import inspect_runtime_state as runtime_state


class _FakeProcessReader:
    module = 0x10000000
    flags_type = 0x20000000
    flags_fields = 0x21000000
    ui_type = 0x30000000
    ui_fields = 0x31000000
    ui_manager_type = 0x40000000
    ui_manager_fields = 0x41000000
    post_loading_type = 0x60000000
    post_loading_fields = 0x61000000
    network_state_type = 0x70000000
    network_state_fields = 0x71000000
    www_helper_type = 0x72000000
    www_helper_fields = 0x73000000

    def __init__(self, pid: int, allowed_root: Path) -> None:
        self.pid = pid
        self.allowed_root = allowed_root

    def __enter__(self) -> _FakeProcessReader:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def module_base(self, module_name: str) -> int:
        if module_name != "GameAssembly.dll":
            raise AssertionError(module_name)
        return self.module

    def pointer(self, address: int) -> int:
        pointers = {
            self.module + runtime_state.BOOTSTRAP_FLAGS_TYPEINFO_RVA: self.flags_type,
            self.flags_type + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.flags_fields,
            self.module + runtime_state.UI_STATE_TYPEINFO_RVA: self.ui_type,
            self.ui_type + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.ui_fields,
            self.ui_fields + 0x20: 0x12345678,
            self.module + runtime_state.UI_MANAGER_TYPEINFO_RVA: self.ui_manager_type,
            self.ui_manager_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.ui_manager_fields,
            self.ui_manager_fields + 0x50: 0x87654321,
            self.module
            + runtime_state.POST_LOADING_TYPEINFO_RVA: self.post_loading_type,
            self.post_loading_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.post_loading_fields,
            self.post_loading_fields + 0x28: 0x62000000,
            self.post_loading_fields + 0x20: 0x62500000,
            self.post_loading_fields + 0x40: 0x63000000,
            self.post_loading_fields + 0x48: 0x64000000,
            self.post_loading_fields + 0x50: 0,
            0x62500000: 0x50000000,
            self.module
            + runtime_state.NETWORK_STATE_TYPEINFO_RVA: self.network_state_type,
            self.network_state_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.network_state_fields,
            self.module + runtime_state.WWW_HELPER_TYPEINFO_RVA: self.www_helper_type,
            self.www_helper_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.www_helper_fields,
            self.www_helper_fields: 0x74000000,
            self.www_helper_fields + 0x8: 0x75000000,
            0x87654321: 0x50000000,
            0x50000000 + 0x10: 0x51000000,
            0x50000000 + 0x18: 0x52000000,
        }
        return pointers[address]

    def managed_string(self, address: int, limit: int = 4096) -> str:
        values = {
            0x63000000: "https://local.invalid/config",
            0x64000000: "callback-data",
            0: "",
        }
        return values[address]

    def c_string(self, address: int, limit: int = 256) -> str:
        values = {
            0x51000000: "CurrentScreen",
            0x52000000: "Game.Ui",
        }
        return values[address]

    def read(self, address: int, size: int) -> bytes:
        values = {
            (self.flags_fields + 0x188, 1): b"\x01",
            (self.flags_fields + 0x189, 1): b"\x00",
            (self.flags_fields + 0x18A, 1): b"\x01",
            (self.ui_fields + 0x28, 2): struct.pack("<h", 7),
            (self.ui_fields + 0x40, 1): b"\x00",
            (0x87654321 + 0x30, 1): b"\x00",
            (0x87654321 + 0x34, 4): struct.pack("<i", 4),
            (0x87654321 + 0x38, 1): b"\x01",
            (0x87654321 + 0x3C, 4): struct.pack("<f", 6.75),
            (0x87654321 + 0x40, 1): b"\x01",
            (self.network_state_fields + 0x10, 4): struct.pack("<i", 10),
            (self.network_state_fields + 0x14, 4): struct.pack("<i", 20),
            (self.network_state_fields + 0x18, 4): struct.pack("<i", 30),
            (self.network_state_fields + 0x1C, 4): struct.pack("<i", 20),
        }
        return values[(address, size)]


class RuntimeStateInspectorTests(unittest.TestCase):
    def test_inspect_maps_native_fields_to_named_output(self) -> None:
        with patch.object(runtime_state, "ProcessReader", _FakeProcessReader):
            result = runtime_state.inspect(321, Path("build/army3-local-client"))

        self.assertEqual(result["pid"], 321)
        self.assertEqual(result["module_base"], "0x10000000")
        self.assertEqual(
            result["bootstrap_flags"],
            {"e1_0x188": 1, "e0_0x189": 0, "da_0x18a": 1},
        )
        self.assertEqual(
            result["ui_state"],
            {
                "countdown_0x28": 7,
                "app_ready_0x40": 0,
                "bootstrap_ui_instance_0x20": "0x12345678",
            },
        )
        self.assertEqual(
            result["ui_manager"],
            {
                "current_screen_0x50": "0x87654321",
                "current_is_bootstrap_ui": False,
                "current_screen_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "current_screen_fields": {
                    "phase_a_0x30": 0,
                    "animation_index_0x34": 4,
                    "phase_b_0x38": 1,
                    "elapsed_0x3c": 6.75,
                    "completion_fired_0x40": 1,
                },
            },
        )
        self.assertEqual(
            result["post_loading"],
            {
                "asset_0x20": "0x62500000",
                "asset_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "singleton_0x28": "0x62000000",
                "url_0x40": "https://local.invalid/config",
                "text_0x48": "callback-data",
                "text_0x50": "",
            },
        )
        self.assertEqual(
            result["network_state"],
            {
                "constant_0x10": 10,
                "constant_0x14": 20,
                "constant_0x18": 30,
                "current_0x1c": 20,
            },
        )
        self.assertEqual(
            result["www_helper"],
            {"request_0x0": "0x74000000", "callback_0x8": "0x75000000"},
        )

    def test_static_fields_rejects_null_type_info(self) -> None:
        class NullReader:
            @staticmethod
            def pointer(address: int) -> int:
                return 0

        with self.assertRaisesRegex(runtime_state.RuntimeReadError, "null type-info"):
            runtime_state._static_fields(NullReader(), 0x1000, 0x2000)


if __name__ == "__main__":
    unittest.main()
