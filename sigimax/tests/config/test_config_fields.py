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

import json
import os
import sys
import tempfile

import pytest

from sigimax.config import (
    AppOptionsContainer,
    EnumOptionField,
    FontOptionField,
    SigimaXOptions,
    TupleOptionField,
    TypedOptionField,
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
        """Getting the default value should return the initial tuple."""
        c = _MiniContainer()
        assert c.my_tuple.get(sync_env=False) == (10, 20)

    def test_get_optional_default_returns_exact_value(self):
        """A missing field returns the supplied default before normalization."""
        c = _MiniContainer()
        default = [30, 40]
        assert c.my_tuple.get(default, sync_env=False) is default
        assert c.my_tuple.get(sync_env=False) == (30, 40)

    def test_get_optional_default_does_not_replace_set_value(self):
        """An explicitly set value takes precedence over a later default."""
        c = _MiniContainer()
        c.my_tuple.set((50, 60), sync_env=False)
        assert c.my_tuple.get((1, 2), sync_env=False) == (50, 60)

    def test_get_none_does_not_initialize(self):
        """None is a non-persisting fallback and leaves the field uninitialized."""
        c = _MiniContainer()
        assert c.my_tuple.get(None, sync_env=False) == (10, 20)
        assert not c.is_option_initialized("my_tuple")

    def test_context_restores_uninitialized_state(self):
        """A temporary override must not persist initialization state."""
        c = _MiniContainer()

        with c.my_tuple.context((30, 40)):
            assert c.my_tuple.get(sync_env=False) == (30, 40)
            assert c.is_option_initialized("my_tuple")

        assert c.my_tuple.get(sync_env=False) == (10, 20)
        assert not c.is_option_initialized("my_tuple")

    def test_context_restores_state_after_exception(self):
        """Context restoration also applies when the body raises."""
        c = _MiniContainer()

        with pytest.raises(RuntimeError, match="stop"):
            with c.my_tuple.context((30, 40)):
                raise RuntimeError("stop")

        assert c.my_tuple.get(sync_env=False) == (10, 20)
        assert not c.is_option_initialized("my_tuple")

    def test_set_tuple(self):
        """Setting a new tuple value should update the stored value."""
        c = _MiniContainer()
        c.my_tuple.set((100, 200), sync_env=False)
        assert c.my_tuple.get(sync_env=False) == (100, 200)

    def test_set_list_converts_to_tuple(self):
        """Setting a list should convert it to a tuple and store it correctly."""
        c = _MiniContainer()
        c.my_tuple.set([5, 6], sync_env=False)
        assert c.my_tuple.get(sync_env=False) == (5, 6)
        assert isinstance(c.my_tuple.get(sync_env=False), tuple)

    def test_set_none(self):
        """Setting None should store None without error."""
        c = _MiniContainer()
        c.my_tuple.set(None, sync_env=False)
        assert c.my_tuple.get(sync_env=False) is None

    def test_set_invalid_type_raises(self):
        """Setting a non-iterable or non-list/tuple should raise a ValueError."""
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected tuple"):
            c.my_tuple.set("bad", sync_env=False)

    def test_set_invalid_int_raises(self):
        """Setting an integer should raise a ValueError since it's not iterable."""
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected tuple"):
            c.my_tuple.set(42, sync_env=False)


# ============================== FontOptionField ===============================


class TestFontOptionField:
    """Tests for FontOptionField."""

    def test_get_default(self):
        """Getting the default value should return the initial font tuple."""
        c = _MiniContainer()
        assert c.my_font.get(sync_env=False) == ("Arial", 12, False)

    def test_set_tuple(self):
        """Setting a new font tuple should update the stored value."""
        c = _MiniContainer()
        c.my_font.set(("Courier", 10, True), sync_env=False)
        assert c.my_font.get(sync_env=False) == ("Courier", 10, True)

    def test_set_list_converts_to_tuple(self):
        """Setting a list should convert it to a tuple and store it correctly."""
        c = _MiniContainer()
        c.my_font.set(["Mono", 14, False], sync_env=False)
        result = c.my_font.get(sync_env=False)
        assert result == ("Mono", 14, False)
        assert isinstance(result, tuple)

    def test_set_none(self):
        """Setting None should store None without error."""
        c = _MiniContainer()
        c.my_font.set(None, sync_env=False)
        assert c.my_font.get(sync_env=False) is None

    def test_set_invalid_length_raises(self):
        """Setting a tuple/list of incorrect length should raise a ValueError."""
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set(("one", "two"), sync_env=False)

    def test_set_invalid_first_element_raises(self):
        """Setting a non-string first element should raise a ValueError."""
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set((123, 12, False), sync_env=False)

    def test_set_invalid_type_raises(self):
        """Setting a non-iterable or non-list/tuple should raise a ValueError."""
        c = _MiniContainer()
        with pytest.raises(ValueError, match="expected.*family.*size.*bold"):
            c.my_font.set("bad", sync_env=False)


# ======================== AppOptionsContainer ================================


class TestAppOptionsContainer:
    """Tests for AppOptionsContainer to_dict / from_dict / reset."""

    def test_to_dict_roundtrip(self):
        """
        Setting some values and converting to dict should produce a dict that can be
        loaded back to the same values.
        """
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
        """
        Providing unknown keys in from_dict should not raise an error and should ignore
        them.
        """
        c = _MiniContainer()
        c.from_dict({"unknown_key": 999, "my_str": "ok"})
        assert c.my_str.get(sync_env=False) == "ok"

    def test_from_dict_marks_option_initialized(self):
        """Loaded values take precedence over later optional defaults."""
        c = _MiniContainer()
        c.from_dict({"my_str": "loaded"})
        assert c.my_str.get("fallback", sync_env=False) == "loaded"

    def test_external_env_marks_option_initialized(self, monkeypatch):
        """An externally supplied JSON value takes precedence over defaults."""
        c = _MiniContainer()
        monkeypatch.setenv(c.ENV_VAR, json.dumps({"my_str": "external"}))
        assert c.my_str.get("fallback") == "external"

    def test_own_env_sync_does_not_initialize_defaults(self):
        """A container's own JSON snapshot does not initialize constructor defaults."""
        c = _MiniContainer()
        c.sync_env()
        assert os.environ[c.ENV_VAR] == c.to_env_json()
        assert c.my_str.get("fallback") == "fallback"

    def test_from_dict_invalid_value_warning(self, capsys):
        """Providing an invalid value in from_dict should produce a warning."""
        c = _MiniContainer()
        c.from_dict({"my_enum": "invalid_choice"})
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "invalid" in captured.out.lower()

    def test_list_options(self):
        """list_options should return the names of all defined options."""
        c = _MiniContainer()
        names = c.list_options()
        assert "my_tuple" in names
        assert "my_font" in names
        assert "my_enum" in names
        assert "my_str" in names

    def test_save_load_roundtrip(self):
        """Saving and loading should preserve the values."""
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
        """list_options should include all expected option names."""
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
        """reset_to_defaults should restore default values for all options."""
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
        """get_old_log_fname should insert .1 before the extension."""
        assert get_old_log_fname("app.log") == "app.1.log"
        assert get_old_log_fname("/path/to/my.log") == "/path/to/my.1.log"

    def test_is_frozen_returns_bool(self):
        """is_frozen should return a boolean value."""
        result = is_frozen("sigimax")
        assert isinstance(result, bool)

    def test_get_mod_source_dir_not_none_in_dev(self):
        """get_mod_source_dir should return a directory path in development installs."""
        # In a development install, get_mod_source_dir should return a directory
        result = get_mod_source_dir()
        # Could be None in frozen builds, but in dev it should not be
        if not hasattr(sys, "_MEIPASS"):
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
