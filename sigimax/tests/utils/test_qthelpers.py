# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for utils/qthelpers.py
-----------------------------

Covers:
- get_log_contents, initialize_log_file, remove_empty_log_file (unit)
- is_running_tests (unit)
- save_restore_stds (unit)
- block_signals (gui)
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest
from guidata.qthelpers import qt_app_context
from qtpy import QtWidgets as QW

from sigimax.utils.qthelpers import (
    block_signals,
    get_log_contents,
    initialize_log_file,
    is_running_tests,
    remove_empty_log_file,
    save_restore_stds,
)

# ======================== Unit tests =========================================

pytestmark = pytest.mark.unit


class TestGetLogContents:
    """Tests for get_log_contents."""

    def test_nonexistent_file_returns_none(self):
        """Should return None for a nonexistent file."""
        assert get_log_contents("/nonexistent/path/file.log") is None

    def test_empty_file_returns_empty(self):
        """Should return empty string for an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name
        try:
            result = get_log_contents(path)
            # Empty file → empty string (stripped)
            assert result == ""
        finally:
            os.unlink(path)

    def test_file_with_content(self):
        """Should return the file contents as a string."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("error occurred at line 42\n")
            path = f.name
        try:
            result = get_log_contents(path)
            assert "error occurred" in result
        finally:
            os.unlink(path)


class TestInitializeLogFile:
    """Tests for initialize_log_file."""

    def test_no_previous_log(self):
        """Should initialize log file when no previous log exists (empty file)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name
        try:
            result = initialize_log_file(path)
            assert result is False  # Empty file → no previous log
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_with_previous_log(self):
        """Should initialize and rename previous log file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("some log content\n")
            path = f.name
        old_path = os.path.splitext(path)[0] + ".1.log"
        try:
            result = initialize_log_file(path)
            assert result is True
            assert os.path.exists(old_path)
        finally:
            for p in (path, old_path):
                if os.path.exists(p):
                    os.unlink(p)


class TestRemoveEmptyLogFile:
    """Tests for remove_empty_log_file."""

    def test_removes_empty_file(self):
        """Should remove an empty log file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name
        remove_empty_log_file(path)
        assert not os.path.exists(path)

    def test_keeps_nonempty_file(self):
        """Should not remove a file that has content."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("content\n")
            path = f.name
        try:
            remove_empty_log_file(path)
            assert os.path.exists(path)
        finally:
            os.unlink(path)


class TestIsRunningTests:
    """Tests for is_running_tests."""

    def test_returns_true_during_pytest(self):
        """Should return True when running under pytest."""
        assert is_running_tests() is True

    def test_pytest_in_modules(self):
        """Should have pytest in sys.modules during tests."""
        assert "pytest" in sys.modules


class TestSaveRestoreStds:
    """Tests for save_restore_stds context manager."""

    def test_restores_stdout(self):
        """Should restore original stdout after context."""
        original_stdout = sys.stdout
        with save_restore_stds():
            assert sys.stdout is None
        assert sys.stdout is original_stdout

    def test_restores_stderr(self):
        """Should restore original stderr after context."""
        original_stderr = sys.stderr
        with save_restore_stds():
            pass  # stdout is None inside
        assert sys.stderr is original_stderr

    def test_restores_on_exception(self):
        """Should restore even if an exception is raised inside the context."""
        original_stdout = sys.stdout
        try:
            with save_restore_stds():
                raise RuntimeError("test")
        except RuntimeError:
            pass
        assert sys.stdout is original_stdout


# ======================== GUI tests ==========================================


@pytest.mark.gui
def test_block_signals():
    """block_signals context manager blocks and unblocks signals."""
    with qt_app_context():
        widget = QW.QLineEdit()
        assert not widget.signalsBlocked()
        with block_signals(widget):
            assert widget.signalsBlocked()
        assert not widget.signalsBlocked()


@pytest.mark.gui
def test_block_signals_disabled():
    """block_signals with enable=False should not block."""
    with qt_app_context():
        widget = QW.QLineEdit()
        with block_signals(widget, enable=False):
            assert not widget.signalsBlocked()
        assert not widget.signalsBlocked()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
