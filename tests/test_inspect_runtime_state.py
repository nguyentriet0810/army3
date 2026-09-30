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
    account_state_type = 0x76000000
    account_state_fields = 0x77000000
    account_menu_data_type = 0x7C000000
    account_menu_data_fields = 0x7D000000
    file_io_type = 0x78000000
    file_io_fields = 0x79000000
    item_templates_type = 0x7A000000
    item_templates_fields = 0x7B000000
    localization_type = 0x7E000000
    localization_fields = 0x7F000000
    localization_cache = 0x7F100000

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
            0x12345678: 0x35000000,
            0x35000000 + 0x10: 0x35100000,
            0x35000000 + 0x18: 0x35200000,
            0x35000000 + 0x1A8: self.module + 0x43BDD0,
            self.module + runtime_state.UI_MANAGER_TYPEINFO_RVA: self.ui_manager_type,
            self.ui_manager_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.ui_manager_fields,
            self.ui_manager_fields + 0x50: 0x87654321,
            self.ui_manager_fields + 0x58: 0x87650000,
            self.ui_manager_fields + 0x60: 0,
            self.ui_manager_fields + 0x70: 0x87654321,
            self.ui_manager_fields + 0x80: 0x87658000,
            self.ui_manager_fields + 0x88: 0,
            self.ui_manager_fields + 0x98: 0,
            self.ui_manager_fields + 0xA0: 0,
            self.ui_manager_fields + 0xA8: 0,
            self.ui_manager_fields + 0xD0: 0,
            0x87654321 + 0x30: 0x88000000,
            0x88000000 + 0x20: 0x88100000,
            0x88000000 + 0x28: 0x88200000,
            0x88100000 + 0x18: 0x89100000,
            0x88200000 + 0x18: 0x89200000,
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
            self.module
            + runtime_state.ACCOUNT_STATE_TYPEINFO_RVA: self.account_state_type,
            self.account_state_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.account_state_fields,
            self.account_state_fields + 0x30: 0x76100000,
            self.module
            + runtime_state.ACCOUNT_MENU_DATA_TYPEINFO_RVA: self.account_menu_data_type,
            self.account_menu_data_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.account_menu_data_fields,
            self.account_menu_data_fields + 0x48: 0x7D100000,
            self.account_menu_data_fields + 0x70: 0x7D200000,
            0x76100000: 0x50000000,
            0x7A100000: 0x50000000,
            0x7B100000: 0x50000000,
            self.module + runtime_state.FILE_IO_TYPEINFO_RVA: self.file_io_type,
            self.file_io_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.file_io_fields,
            self.file_io_fields + 0x8: 0x79100000,
            self.file_io_fields + 0x10: 0x79200000,
            self.module
            + runtime_state.ITEM_TEMPLATES_TYPEINFO_RVA: self.item_templates_type,
            self.item_templates_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.item_templates_fields,
            self.module
            + runtime_state.LOCALIZATION_TYPEINFO_RVA: self.localization_type,
            self.localization_type
            + runtime_state.IL2CPP_STATIC_FIELDS_OFFSET: self.localization_fields,
            self.localization_fields + 0x18: self.localization_cache,
            self.localization_cache + 0x20 + 0x2B9 * 8: 0x7F200000,
            self.localization_cache + 0x20 + 0x3DB * 8: 0x7F210000,
            self.localization_cache + 0x20 + 0x609 * 8: 0x7F220000,
            self.localization_cache + 0x20 + 0x692 * 8: 0x7F230000,
            self.localization_cache + 0x20 + 0x846 * 8: 0x7F240000,
            self.localization_cache + 0x20 + 0x88E * 8: 0x7F250000,
            self.flags_fields + 0x20: 0x7A100000,
            self.item_templates_fields: 0x7B100000,
            0x7B100000 + 0x10: 0x7B200000,
            0x87654321: 0x50000000,
            0x87658000: 0x55000000,
            0x50000000 + 0x10: 0x51000000,
            0x50000000 + 0x18: 0x52000000,
            0x50000000 + 0x1A8: self.module + 0x1961E0,
            0x55000000 + 0x10: 0x55100000,
            0x55000000 + 0x18: 0x55200000,
            0x55000000 + 0x1A8: self.module + 0x200000,
        }
        return pointers[address]

    def managed_string(self, address: int, limit: int = 4096) -> str:
        values = {
            0x63000000: "https://local.invalid/config",
            0x64000000: "callback-data",
            0x89100000: "First",
            0x89200000: "Second",
            0: "",
            0x79200000: "C:/cache/dataItem",
            0x7F200000: "Label 2B9",
            0x7F210000: "Label 3DB",
            0x7F220000: "Label 609",
            0x7F230000: "Label 692",
            0x7F240000: "Label 846",
            0x7F250000: "Label 88E",
        }
        return values[address]

    def c_string(self, address: int, limit: int = 256) -> str:
        values = {
            0x51000000: "CurrentScreen",
            0x52000000: "Game.Ui",
            0x55100000: "NewPlayerScreen",
            0x55200000: "Game.Ui",
            0x35100000: "BootstrapUi",
            0x35200000: "Game.Ui",
        }
        return values[address]

    def read(self, address: int, size: int) -> bytes:
        values = {
            (self.flags_fields + 0x188, 1): b"\x01",
            (self.flags_fields + 0x189, 1): b"\x00",
            (self.flags_fields + 0x18A, 1): b"\x01",
            (self.flags_fields + 0x300, 4): struct.pack("<i", 9),
            (self.flags_fields + 0x304, 1): struct.pack("<b", 9),
            (self.ui_fields + 0x28, 2): struct.pack("<h", 7),
            (self.ui_fields + 0x40, 1): b"\x00",
            (self.post_loading_fields + 0x84, 1): b"\x01",
            (0x87654321 + 0x30, 1): b"\x00",
            (0x87654321 + 0x34, 4): struct.pack("<i", 4),
            (0x87654321 + 0x38, 1): b"\x01",
            (0x87654321 + 0x3C, 4): struct.pack("<f", 6.75),
            (0x87654321 + 0x40, 1): b"\x01",
            (0x88000000 + 0x18, 4): struct.pack("<i", 2),
            (0x88100000 + 0x40, 4): struct.pack("<i", 10),
            (0x88100000 + 0x44, 4): struct.pack("<i", 20),
            (0x88100000 + 0x48, 4): struct.pack("<i", 160),
            (0x88100000 + 0x50, 4): struct.pack("<i", 80),
            (0x88200000 + 0x40, 4): struct.pack("<i", 30),
            (0x88200000 + 0x44, 4): struct.pack("<i", 40),
            (0x88200000 + 0x48, 4): struct.pack("<i", 160),
            (0x88200000 + 0x50, 4): struct.pack("<i", 80),
            (self.network_state_fields + 0x10, 4): struct.pack("<i", 10),
            (self.network_state_fields + 0x14, 4): struct.pack("<i", 20),
            (self.network_state_fields + 0x18, 4): struct.pack("<i", 30),
            (self.network_state_fields + 0x1C, 4): struct.pack("<i", 20),
            (0x76100000 + 0x358, 4): struct.pack("<i", 3),
            (self.account_menu_data_fields, 1): struct.pack("<b", 2),
            (self.account_menu_data_fields + 0x3, 1): struct.pack("<b", 8),
            (self.account_menu_data_fields + 0x50, 4): struct.pack("<i", 2),
            (0x7D100000 + 0x18, 4): struct.pack("<i", 9),
            (0x7D200000 + 0x18, 4): struct.pack("<i", 4),
            (self.file_io_fields, 4): struct.pack("<i", 0),
            (0x79100000 + 0x18, 4): struct.pack("<i", 4),
            (0x7A100000 + 0x18, 4): struct.pack("<i", 2),
            (0x7B200000 + 0x18, 4): struct.pack("<i", 17),
            (self.flags_fields + 0x2F0, 4): struct.pack("<i", 2),
            (self.localization_cache + 0x18, 4): struct.pack("<i", 0x900),
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
            {
                "e1_0x188": 1,
                "e0_0x189": 0,
                "da_0x18a": 1,
                "c4_cached_version_0x300": 9,
                "c4_revision_0x304": 9,
            },
        )
        self.assertEqual(
            result["ui_state"],
            {
                "countdown_0x28": 7,
                "app_ready_0x40": 0,
                "bootstrap_ui_instance_0x20": "0x12345678",
                "bootstrap_ui_type": {
                    "class": "BootstrapUi",
                    "namespace": "Game.Ui",
                },
                "activation_slot_0x1a8": "0x1043BDD0",
                "activation_rva": "0x43BDD0",
            },
        )
        self.assertEqual(
            result["ui_manager"],
            {
                "current_screen_0x50": "0x87654321",
                "splash_screen_0x58": "0x87650000",
                "c4_target_screen_0x70": "0x87654321",
                "input_dialog_screen_0x80": "0x87658000",
                "input_dialog_screen_type": {
                    "class": "NewPlayerScreen",
                    "namespace": "Game.Ui",
                },
                "input_dialog_activation_slot_0x1a8": "0x10200000",
                "input_dialog_activation_rva": "0x200000",
                "screen_0x60": "0x0",
                "screen_0x60_type": {"class": "", "namespace": ""},
                "current_is_bootstrap_ui": False,
                "current_is_splash_screen": False,
                "current_is_c4_target_screen": True,
                "current_screen_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "aux_0x88": "0x0",
                "aux_0x88_type": {"class": "", "namespace": ""},
                "aux_0x98": "0x0",
                "aux_0x98_type": {"class": "", "namespace": ""},
                "overlay_0xa0": "0x0",
                "overlay_0xa0_type": {"class": "", "namespace": ""},
                "area_screen_0xa8": "0x0",
                "area_screen_type": {"class": "", "namespace": ""},
                "area_record_0x230": "0x0",
                "area_record_type": {"class": "", "namespace": ""},
                "area_record_fields": None,
                "aux_0xd0": "0x0",
                "aux_0xd0_type": {"class": "", "namespace": ""},
                "current_activation_slot_0x1a8": "0x101961E0",
                "current_activation_rva": "0x1961E0",
                "controls": [
                    {
                        "index": 0,
                        "address": "0x88100000",
                        "label": "First",
                        "x": 10,
                        "y": 20,
                        "width": 160,
                        "height": 80,
                    },
                    {
                        "index": 1,
                        "address": "0x88200000",
                        "label": "Second",
                        "x": 30,
                        "y": 40,
                        "width": 160,
                        "height": 80,
                    },
                ],
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
                "cache_hit_0x84": 1,
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
        self.assertEqual(
            result["account_state"],
            {
                "selected_profile_0x30": "0x76100000",
                "selected_profile_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "entry_count_0x358": 3,
            },
        )
        self.assertEqual(
            result["account_menu_data"],
            {
                "selector_0x0": 2,
                "selector_boundary_0x3": 8,
                "selected_index_0x50": 2,
                "entry_array_0x48": "0x7D100000",
                "entry_count": 9,
                "active_values_0x70": "0x7D200000",
                "active_value_count": 4,
            },
        )
        self.assertEqual(
            result["file_io"],
            {
                "state_0x0": 0,
                "buffer_0x8": "0x79100000",
                "buffer_length": 4,
                "path_0x10": "C:/cache/dataItem",
            },
        )
        self.assertEqual(
            result["item_data"],
            {
                "group_array_0x20": "0x7A100000",
                "group_array_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "group_count": 2,
                "template_dictionary": "0x7B100000",
                "template_dictionary_type": {
                    "class": "CurrentScreen",
                    "namespace": "Game.Ui",
                },
                "template_count": 17,
                "stored_revision_0x2f0": 2,
            },
        )
        self.assertEqual(
            result["e4_localization"],
            {
                "0x2B9": "Label 2B9",
                "0x3DB": "Label 3DB",
                "0x609": "Label 609",
                "0x692": "Label 692",
                "0x846": "Label 846",
                "0x88E": "Label 88E",
            },
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
