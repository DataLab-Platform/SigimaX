# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for env.py execution environment
---------------------------------------

Covers:
- VerbosityLevels enum values
- SGMXExecEnv.print with different verbosity levels
- SGMXExecEnv.pprint output
- SGMXExecEnv.to_dict
- SGMXExecEnv.context manager
"""

from __future__ import annotations

import io

import pytest

from sigimax.env import VerbosityLevels, execenv

pytestmark = pytest.mark.unit


class TestVerbosityLevels:
    """Tests for VerbosityLevels enum."""

    def test_quiet_value(self):
        """The QUIET level should have the value 'quiet'."""
        assert VerbosityLevels.QUIET.value == "quiet"

    def test_normal_value(self):
        """The NORMAL level should have the value 'normal'."""
        assert VerbosityLevels.NORMAL.value == "normal"

    def test_debug_value(self):
        """The DEBUG level should have the value 'debug'."""
        assert VerbosityLevels.DEBUG.value == "debug"

    def test_all_values(self):
        """All enum values should be present and correct."""
        values = {v.value for v in VerbosityLevels}
        assert values == {"quiet", "normal", "debug"}


class TestSGMXExecEnv:
    """Tests for the SGMXExecEnv singleton behavior."""

    def test_to_dict_returns_dict(self):
        """to_dict should return a dictionary with key properties."""
        d = execenv.to_dict()
        assert isinstance(d, dict)
        # Should contain at least the key properties
        assert "unattended" in d
        assert "verbose" in d

    def test_print_normal_verbosity(self):
        """In normal verbosity, print() should output."""
        old_verbose = execenv.verbose
        try:
            execenv.verbose = VerbosityLevels.NORMAL.value
            buf = io.StringIO()
            execenv.print("test output", file=buf)
            assert "test output" in buf.getvalue()
        finally:
            execenv.verbose = old_verbose

    def test_print_quiet_suppresses(self):
        """In quiet verbosity, print() should suppress output."""
        old_verbose = execenv.verbose
        try:
            execenv.verbose = VerbosityLevels.QUIET.value
            buf = io.StringIO()
            execenv.print("should not appear", file=buf)
            assert buf.getvalue() == ""
        finally:
            execenv.verbose = old_verbose

    def test_pprint_normal_verbosity(self):
        """In normal verbosity, pprint() should produce output."""
        old_verbose = execenv.verbose
        try:
            execenv.verbose = VerbosityLevels.NORMAL.value
            buf = io.StringIO()
            execenv.pprint({"key": "value"}, stream=buf)
            assert "key" in buf.getvalue()
        finally:
            execenv.verbose = old_verbose

    def test_pprint_quiet_suppresses(self):
        """In quiet verbosity, pprint() should suppress output."""
        old_verbose = execenv.verbose
        try:
            execenv.verbose = VerbosityLevels.QUIET.value
            buf = io.StringIO()
            execenv.pprint({"key": "value"}, stream=buf)
            assert buf.getvalue() == ""
        finally:
            execenv.verbose = old_verbose

    def test_context_manager_restores(self):
        """Context manager should restore previous state on exit."""
        old_unattended = execenv.unattended
        old_verbose = execenv.verbose
        with execenv.context(unattended=True, verbose="debug"):
            assert execenv.unattended is True
            assert execenv.verbose == "debug"
        assert execenv.unattended == old_unattended
        assert execenv.verbose == old_verbose

    def test_str_representation(self):
        """__str__ should return a non-empty string."""
        s = str(execenv)
        assert len(s) > 0

    def test_demo_mode(self):
        """enable_demo_mode / disable_demo_mode toggle."""
        old_unattended = execenv.unattended
        old_delay = execenv.delay
        try:
            execenv.enable_demo_mode(delay=500)
            assert execenv.demo_mode is True
            assert execenv.unattended is True
            assert execenv.delay == 500

            execenv.disable_demo_mode()
            assert execenv.demo_mode is False
            assert execenv.unattended is False
            assert execenv.delay == 0
        finally:
            execenv.unattended = old_unattended
            execenv.delay = old_delay


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
