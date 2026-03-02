# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Local PDF doc path unit tests
------------------------------

Tests for the ``__get_local_doc_path`` static method on ``SGMXMainWindow``,
which resolves a configurable path pattern to a locale-aware PDF file.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from qtpy import QtCore as QC

from sigimax.config import CONF as Conf
from sigimax.gui.main import SGMXMainWindow

# Access the name-mangled static method without instantiating a window
_get_local_doc_path = (
    SGMXMainWindow._SGMXMainWindow__get_local_doc_path  # pylint: disable=protected-access
)


@pytest.fixture(autouse=True)
def _reset_doc_path():
    """Reset app_local_doc_path to empty after each test."""
    yield
    Conf.app_local_doc_path.set("")


@pytest.fixture()
def pdf_files(tmp_path):  # pylint: disable=redefined-outer-name
    """Create fake locale-aware PDF files and return the directory."""
    (tmp_path / "MyApp_fr.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "MyApp_en.pdf").write_text("fake", encoding="utf-8")
    return tmp_path


class TestLocalDocPath:
    """Tests for SGMXMainWindow.__get_local_doc_path."""

    def test_empty_config_returns_none(self):
        """No path configured → None."""
        Conf.app_local_doc_path.set("")
        assert _get_local_doc_path() is None

    def test_lang_placeholder_resolves_locale(
        self,
        pdf_files,  # pylint: disable=redefined-outer-name
    ):
        """Pattern with {lang} resolves to the system locale file."""
        pattern = str(pdf_files / "MyApp_{lang}.pdf")
        Conf.app_local_doc_path.set(pattern)

        with patch.object(
            QC.QLocale, "system", return_value=QC.QLocale(QC.QLocale.French)
        ):
            result = _get_local_doc_path()
            assert result is not None
            assert result.endswith("MyApp_fr.pdf")

    def test_lang_placeholder_falls_back_to_en(
        self,
        pdf_files,  # pylint: disable=redefined-outer-name
    ):
        """Pattern with {lang} falls back to 'en' when locale file is missing."""
        pattern = str(pdf_files / "MyApp_{lang}.pdf")
        Conf.app_local_doc_path.set(pattern)

        # Japanese locale → no MyApp_ja.pdf → should fall back to MyApp_en.pdf
        with patch.object(
            QC.QLocale, "system", return_value=QC.QLocale(QC.QLocale.Japanese)
        ):
            result = _get_local_doc_path()
            assert result is not None
            assert result.endswith("MyApp_en.pdf")

    def test_lang_placeholder_no_file_returns_none(self, tmp_path):
        """Pattern with {lang} but no matching file at all → None."""
        pattern = str(tmp_path / "Missing_{lang}.pdf")
        Conf.app_local_doc_path.set(pattern)
        assert _get_local_doc_path() is None

    def test_direct_path_existing_file(
        self,
        pdf_files,  # pylint: disable=redefined-outer-name
    ):
        """Pattern without {lang} pointing to an existing file → that path."""
        path = str(pdf_files / "MyApp_en.pdf")
        Conf.app_local_doc_path.set(path)
        assert _get_local_doc_path() == path

    def test_direct_path_missing_file(self, tmp_path):
        """Pattern without {lang} pointing to a missing file → None."""
        Conf.app_local_doc_path.set(str(tmp_path / "nonexistent.pdf"))
        assert _get_local_doc_path() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
