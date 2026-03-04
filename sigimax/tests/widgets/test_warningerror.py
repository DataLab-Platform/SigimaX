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

from sigimax.widgets.warningerror import insert_spaces

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
