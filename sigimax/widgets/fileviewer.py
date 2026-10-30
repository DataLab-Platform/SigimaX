# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Module providing a file viewer widget
"""

from __future__ import annotations

import codecs
from pathlib import Path

from guidata.configtools import get_icon
from guidata.widgets.codeeditor import CodeEditor
from qtpy import QtWidgets as QW

from sigimax.config import _, get_conf

__all__ = [
    "FileViewerWidget",
    "get_title_contents",
    "read_text_file",
]


def read_text_file(path: str) -> str:
    """Read text file, guessing its encoding

    Files starting with a byte order mark are decoded with the corresponding
    Unicode encoding (UTF-8, UTF-16 or UTF-32). Other files are decoded as UTF-8,
    then as cp1252 (Windows), and finally as latin1, which decodes any file.
    Line endings are converted to ``"\\n"``.

    Args:
        path (str): path to file

    Returns:
        str: file contents
    """
    data = Path(path).read_bytes()
    # UTF-32 byte order marks must be checked before UTF-16 ones (same prefix)
    for bom, encoding in (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if data.startswith(bom):
            text = data.decode(encoding, errors="replace")
            break
    else:
        for encoding in ("utf-8", "cp1252"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                pass
        else:
            text = data.decode("latin1")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def get_title_contents(path: str) -> tuple[str, str]:
    """Get title and contents for log filename

    Args:
        path (str): path to file

    Returns:
        tuple[str, str]: title and contents
    """
    contents = read_text_file(path)
    pathobj = Path(path)
    uri_path = pathobj.absolute().as_uri()
    prefix = _("Contents of file")
    text = f'{prefix} <a href="{uri_path}">{path}</a>:'
    return text, contents


class FileViewerWidget(QW.QWidget):
    """File viewer widget

    Args:
        parent (QW.QWidget | None): parent widget. Defaults to None.
    """

    def __init__(self, language: str | None = None, parent: QW.QWidget = None) -> None:
        super().__init__(parent)
        if parent is None:
            self.setWindowIcon(get_icon(get_conf().app_logo_path.get()))
        self.editor = CodeEditor(language=language)
        self.editor.setReadOnly(True)
        layout = QW.QVBoxLayout()
        self.label = QW.QLabel("")
        layout.addWidget(self.label)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def set_data(self, text: str, contents: str) -> None:
        """Set log data

        Args:
            text (str): text to display
            contents (str): contents to display
        """
        self.label.setText(text)
        self.label.setOpenExternalLinks(True)
        self.editor.setPlainText(contents)
