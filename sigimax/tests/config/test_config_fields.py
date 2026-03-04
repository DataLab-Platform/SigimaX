# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for config.py option field classes and helpers
----------------------------------------------------

Covers:
- TupleOptionField: set/get, list→tuple conversion, validation
- FontOptionField: set/get, validation
- AppOptionsContainer: to_dict/from_dict roundtrip, reset_to_defaults
- get_old_log_fname, is_frozen, get_mod_source_dir
- SigimaXOptions.list_options completeness
"""

from __future__ import annotations

import sys
import tempfile

import pytest
from sigima.config import TypedOptionField

from sigimax.config import (
    AppOptionsContainer,
    EnumOptionField,
    FontOptionField,
    SigimaXOptions,
    TupleOptionField,
    get_mod_source_dir,
    get_old_log_fname,
    is_frozen,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers: minimal container for isolated field tests
# ---------------------------------------------------------------------------


class _MiniContainer(AppOptionsContainer):
    ENV_VAR = "_MINI_TEST_JSON"
    APP_NAME = "MiniTest"

    def __init__(self):
        super().__init__()
        self.my_tuple = TupleOptionField(
            self, "my_tuple", default=(10, 20), description="A tuple option"
        )
        self.my_font = FontOptionField(
            self, "my_font", default=("Arial", 12, False), description="A font option"
        )
        self.my_enum = EnumOptionField(
            self,
            "my_enum",
            default="a",
            choices=["a", "b", "c"],
            description="An enum option",
        )
        self.my_str = TypedOptionField(
            self, "my_str", default="hello", expected_type=str, description="A string"
        )


# ============================== TupleOptionField ==============================


class TestTupleOptionField:
    """Tests for TupleOptionField."""

    def test_get_default(self):
        c = _MiniContainer()
        assert c.my_tuple.get(sync_env=False) == (10, 20)

    def test_set_tuple(self):
        c = _MiniContainer()
        c.my_tuple.set((100, 200), sync_env=False)
        assert c.my_tuple.get(sync_env=False) == (100, 200)

    def test_set_list_converts_to_tuple(self):
        c = _MiniContainer()
        c.my_tuple.set([5, 6], sync_env=False)
        assert c.my_tuple.get(sync_env=False) == (5, 6)
        assert isinstance(c.my_tuple.get(sync_env=False), tuple)

    def test_set_none(self):
        c = _MiniContainer()
        c.my_tuple.set(None, sync_env=False)
        assert c.my_tuple.get(sync_env=False) is None

    def test_set_invalid_type_raises(self):
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected tuple"):
            c.my_tuple.set("bad", sync_env=False)

    def test_set_invalid_int_raises(self):
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected tuple"):
            c.my_tuple.set(42, sync_env=False)


# ============================== FontOptionField ===============================


class TestFontOptionField:
    """Tests for FontOptionField."""

    def test_get_default(self):
        c = _MiniContainer()
        assert c.my_font.get(sync_env=False) == ("Arial", 12, False)

    def test_set_tuple(self):
        c = _MiniContainer()
        c.my_font.set(("Courier", 10, True), sync_env=False)
        assert c.my_font.get(sync_env=False) == ("Courier", 10, True)

    def test_set_list_converts_to_tuple(self):
        c = _MiniContainer()
        c.my_font.set(["Mono", 14, False], sync_env=False)
        result = c.my_font.get(sync_env=False)
        assert result == ("Mono", 14, False)
        assert isinstance(result, tuple)

    def test_set_none(self):
        c = _MiniContainer()
        c.my_font.set(None, sync_env=False)
        assert c.my_font.get(sync_env=False) is None

    def test_set_invalid_length_raises(self):
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set(("one", "two"), sync_env=False)

    def test_set_invalid_first_element_raises(self):
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set((123, 12, False), sync_env=False)

    def test_set_invalid_type_raises(self):
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set("bad", sync_env=False)


# ======================== AppOptionsContainer ================================


class TestAppOptionsContainer:
    """Tests for AppOptionsContainer to_dict / from_dict / reset."""

    def test_to_dict_roundtrip(self):
        c = _MiniContainer()
        c.my_str.set("world", sync_env=False)
        c.my_tuple.set((1, 2), sync_env=False)
        d = c.to_dict()
        assert d["my_str"] == "world"
        assert d["my_tuple"] == (1, 2)

        c2 = _MiniContainer()
        c2.from_dict(d)
        assert c2.my_str.get(sync_env=False) == "world"
        assert c2.my_tuple.get(sync_env=False) == (1, 2)

    def test_from_dict_ignores_unknown_keys(self):
        c = _MiniContainer()
        c.from_dict({"unknown_key": 999, "my_str": "ok"})
        assert c.my_str.get(sync_env=False) == "ok"

    def test_from_dict_invalid_value_warning(self, capsys):
        c = _MiniContainer()
        c.from_dict({"my_enum": "invalid_choice"})
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "invalid" in captured.out.lower()

    def test_list_options(self):
        c = _MiniContainer()
        names = c.list_options()
        assert "my_tuple" in names
        assert "my_font" in names
        assert "my_enum" in names
        assert "my_str" in names

    def test_save_load_roundtrip(self):
        c = _MiniContainer()
        c.my_str.set("persisted", sync_env=False)
        c.my_tuple.set((99, 100), sync_env=False)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        c.save(path)

        c2 = _MiniContainer()
        c2.load(path)
        assert c2.my_str.get(sync_env=False) == "persisted"
        assert c2.my_tuple.get(sync_env=False) == (99, 100)


# ======================== SigimaXOptions =====================================


class TestSigimaXOptions:
    """Tests for the full SigimaXOptions CONF singleton."""

    def test_list_options_contains_expected(self):
        opts = SigimaXOptions()
        names = opts.list_options()
        # Check a representative sample of expected options
        expected = [
            "app_name",
            "color_mode",
            "console_enabled",
            "window_maximized",
            "ima_def_colormap",
        ]
        for name in expected:
            assert name in names, f"Expected option '{name}' not in list_options()"

    def test_reset_to_defaults(self):
        opts = SigimaXOptions()
        original = opts.ima_def_colormap.get(sync_env=False)
        opts.ima_def_colormap.set("gray", sync_env=False)
        assert opts.ima_def_colormap.get(sync_env=False) == "gray"
        opts.reset_to_defaults()
        assert opts.ima_def_colormap.get(sync_env=False) == original


# ======================== Module-level helpers ===============================


class TestModuleHelpers:
    """Tests for get_old_log_fname, is_frozen, get_mod_source_dir."""

    def test_get_old_log_fname(self):
        assert get_old_log_fname("app.log") == "app.1.log"
        assert get_old_log_fname("/path/to/my.log") == "/path/to/my.1.log"

    def test_is_frozen_returns_bool(self):
        result = is_frozen("sigimax")
        assert isinstance(result, bool)

    def test_get_mod_source_dir_not_none_in_dev(self):
        # In a development install, get_mod_source_dir should return a directory
        result = get_mod_source_dir()
        # Could be None in frozen builds, but in dev it should not be
        if not hasattr(sys, "_MEIPASS"):
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
