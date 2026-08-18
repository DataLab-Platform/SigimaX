# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for warningerror.py utilities
------------------------------------

Covers:
- insert_spaces: pure text utility
- WarningErrorMessageBox: basic construction with sample error/warning
"""

from __future__ import annotations

import pytest
from guidata.qthelpers import exec_dialog, qt_app_context
from qtpy import QtWidgets as QW

from sigimax.widgets.warningerror import WarningErrorMessageBox, insert_spaces

pytestmark = pytest.mark.unit


class TestInsertSpaces:
    """Tests for the insert_spaces pure-text utility."""

    def test_short_text_unchanged(self):
        """
        Short text should be returned unchanged
        (except for a possible trailing space).
        """
        result = insert_spaces("hi", 80)
        # Short text should pass through with at most a trailing space
        assert "hi" in result

    def test_long_text_gets_spaces(self):
        """Long text should have spaces inserted."""
        text = "a" * 200
        result = insert_spaces(text, 40)
        # Should contain spaces breaking up the text
        assert " " in result
        # The content characters should all still be present
        assert result.replace(" ", "") == text

    def test_special_chars_trigger_break(self):
        """Special chars should trigger breaks even if text is short."""
        text = "hello,world-foo+bar"
        result = insert_spaces(text, 5)
        assert " " in result

    def test_empty_string(self):
        """Empty string should return empty string."""
        result = insert_spaces("", 10)
        assert result == ""

    def test_exact_nbchars(self):
        """Text with exactly nbchars should get a space added."""
        text = "abcde"
        result = insert_spaces(text, 5)
        # With exactly nbchars, one iteration adds space
        assert "abcde" in result


def _show_message_box(category: str) -> None:
    """Construct and show a WarningErrorMessageBox for the given category."""
    with qt_app_context():
        win = QW.QMainWindow()
        win.setWindowTitle(f"SigimaX {category.capitalize()} Message Box test")
        win.show()
        if category == "error":
            try:
                raise ValueError("Test error message box")
            except ValueError:
                context = "Test_error_message_box." * 5
                tip = "This error may occured when testing the error message box. " * 10
                dlg = WarningErrorMessageBox(win, "error", context, tip=tip)
                exec_dialog(dlg)
        else:
            context = "Test_warning_message_box." * 5
            message = "Test warning message box" * 10
            dlg = WarningErrorMessageBox(win, "warning", context, message)
            exec_dialog(dlg)


@pytest.mark.gui
class TestWarningErrorMessageBox:
    """Tests for the WarningErrorMessageBox dialog construction."""

    def test_error_message_box(self):
        """An error message box can be constructed and shown."""
        _show_message_box("error")

    def test_warning_message_box(self):
        """A warning message box can be constructed and shown."""
        _show_message_box("warning")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
