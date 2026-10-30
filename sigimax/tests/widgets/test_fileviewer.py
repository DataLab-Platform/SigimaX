# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for fileviewer.py utilities and widget
--------------------------------------------

Covers:
- read_text_file: reads UTF-8, latin1, cp1252 and Unicode files with a byte order
  mark, converting line endings
- get_title_contents: returns (title, contents) tuple
- FileViewerWidget: basic construction and set_data
"""

from __future__ import annotations

import codecs
import os
import tempfile

import pytest
from guidata.qthelpers import qt_app_context

from sigimax.widgets.fileviewer import (
    FileViewerWidget,
    get_title_contents,
    read_text_file,
)

# ======================== Unit tests =========================================


class TestReadTextFile:
    """Unit tests for read_text_file."""

    pytestmark = pytest.mark.unit

    def test_read_utf8(self):
        """Should read UTF-8 encoded files correctly."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello café")
            path = f.name
        try:
            result = read_text_file(path)
            assert "Hello café" in result
        finally:
            os.unlink(path)

    def test_read_latin1(self):
        """Should read Latin-1 encoded files correctly."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("résumé".encode("latin1"))
            path = f.name
        try:
            result = read_text_file(path)
            assert "sum" in result  # content should be readable
        finally:
            os.unlink(path)

    def test_read_ascii(self):
        """Should read ASCII encoded files correctly."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="ascii"
        ) as f:
            f.write("plain ascii")
            path = f.name
        try:
            result = read_text_file(path)
            assert result == "plain ascii"
        finally:
            os.unlink(path)

    @pytest.mark.parametrize(
        "encoding", ["utf-8-sig", "utf-16", "utf-16-be", "utf-32", "cp1252"]
    )
    def test_read_encodings(self, tmp_path, encoding: str):
        """Files with a byte order mark and Windows (cp1252) files are decoded
        with their encoding."""
        # "—" and "€" are encoded differently in cp1252 and latin1
        text = "Température : 25 °C — 3 €\nfin"
        path = tmp_path / "file.txt"
        data = text.encode(encoding)
        if encoding == "utf-16-be":
            data = codecs.BOM_UTF16_BE + data
        path.write_bytes(data)
        assert read_text_file(str(path)) == text

    def test_read_line_endings(self, tmp_path):
        """Windows and old Mac line endings are converted."""
        path = tmp_path / "file.txt"
        path.write_bytes(b"a\r\nb\rc\n")
        assert read_text_file(str(path)) == "a\nb\nc\n"

    def test_read_binary(self, tmp_path):
        """Any file can be read (bytes which are not text are decoded as latin1)."""
        path = tmp_path / "file.bin"
        path.write_bytes(bytes(range(256)))
        assert len(read_text_file(str(path))) > 0


class TestGetTitleContents:
    """Unit tests for get_title_contents."""

    pytestmark = pytest.mark.unit

    def test_returns_tuple(self):
        """Should return a (title, contents) tuple."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("file body")
            path = f.name
        try:
            title, contents = get_title_contents(path)
            assert isinstance(title, str)
            assert "file body" in contents
            assert path in title or os.path.basename(path) in title
        finally:
            os.unlink(path)


# ======================== GUI tests ==========================================


@pytest.mark.gui
def test_file_viewer_widget():
    """FileViewerWidget: construct and set data without crashing."""
    with qt_app_context():
        widget = FileViewerWidget()
        widget.set_data("Title text", "Some file contents\nLine 2")
        assert widget.label.text() == "Title text"
        assert "Some file contents" in widget.editor.toPlainText()
        widget.show()
        widget.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
