# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

# pylint: disable=protected-access

"""
Tests for the Wizard widget (:mod:`sigimax.widgets.wizard`)
-----------------------------------------------------------

Covers:
- WizardPage: title, subtitle, validity flag, add_to_layout
- Wizard: page navigation (next/back), button states, accept/reject
"""

from __future__ import annotations

import pytest
from guidata.qthelpers import qt_app_context
from qtpy import QtWidgets as QW

from sigimax.widgets.wizard import Wizard, WizardPage

pytestmark = pytest.mark.gui


# ---------------------------------------------------------------------------
# Test pages
# ---------------------------------------------------------------------------


class _PageA(WizardPage):
    """First test page — always valid."""

    def __init__(self):
        super().__init__()
        self.set_title("Page A")
        self.set_subtitle("First page")
        self._initialized = False

    def initialize_page(self):
        self._initialized = True
        super().initialize_page()


class _PageB(WizardPage):
    """Second page — validity can be toggled."""

    def __init__(self):
        super().__init__()
        self.set_title("Page B")
        self.set_subtitle("Second page")
        self.checkbox = QW.QCheckBox("Accept terms")
        self.add_to_layout(self.checkbox)
        self.set_valid(True)


class _PageInvalid(WizardPage):
    """A page that starts invalid."""

    def __init__(self):
        super().__init__()
        self.set_title("Invalid Page")
        self.set_valid(False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wizard_page_title_subtitle():
    """WizardPage title and subtitle text."""
    with qt_app_context():
        page = _PageA()
        assert page._title_label.text() == "Page A"
        assert page._subtitle_label.text() == "First page"


def test_wizard_page_validity():
    """WizardPage validity flag and signal."""
    with qt_app_context():
        page = _PageA()
        assert page.is_valid() is True
        page.set_valid(False)
        assert page.is_valid() is False
        page.set_valid(True)
        assert page.is_valid() is True


def test_wizard_page_add_widget():
    """WizardPage.add_to_layout with a QWidget."""
    with qt_app_context():
        page = WizardPage()
        btn = QW.QPushButton("Test")
        page.add_to_layout(btn)
        assert page._user_layout.count() == 1


def test_wizard_navigation_buttons():
    """Wizard button states after page navigation."""
    with qt_app_context():
        wizard = Wizard()
        wizard.add_page(_PageA())
        wizard.add_page(_PageB(), last_page=True)

        # On first page: Back disabled, Next enabled, Finish disabled
        assert not wizard._back_btn.isEnabled()
        assert wizard._next_btn.isEnabled()
        assert not wizard._finish_btn.isEnabled()

        # Move to next page
        wizard.go_to_next_page()

        # On last page: Back enabled, Next disabled, Finish enabled
        assert wizard._back_btn.isEnabled()
        assert not wizard._next_btn.isEnabled()
        assert wizard._finish_btn.isEnabled()

        # Go back
        wizard.go_to_previous_page()
        assert not wizard._back_btn.isEnabled()
        assert wizard._next_btn.isEnabled()


def test_wizard_single_page_finish():
    """A single-page wizard should have Finish enabled when page is valid."""
    with qt_app_context():
        wizard = Wizard()
        wizard.add_page(_PageA(), last_page=True)

        # Single page, last page, valid → Finish enabled
        assert wizard._finish_btn.isEnabled()
        assert not wizard._next_btn.isEnabled()
        assert not wizard._back_btn.isEnabled()


def test_wizard_invalid_page_blocks_next():
    """When a page is invalid, Next should be disabled."""
    with qt_app_context():
        wizard = Wizard()
        wizard.add_page(_PageInvalid())
        wizard.add_page(_PageB(), last_page=True)

        # First page is invalid → Next disabled
        assert not wizard._next_btn.isEnabled()
        assert not wizard._finish_btn.isEnabled()


def test_wizard_page_initialization():
    """initialize_page is called when wizard navigates to a page."""
    with qt_app_context():
        page_a = _PageA()
        page_b = _PageB()
        wizard = Wizard()
        wizard.add_page(page_a)
        wizard.add_page(page_b, last_page=True)

        # Page A is initialized when wizard is created (last_page=True triggers it
        # on page 0)
        assert page_a._initialized is True


def test_wizard_set_wizard_reference():
    """Each page should have a reference to its parent wizard."""
    with qt_app_context():
        page = _PageA()
        wizard = Wizard()
        wizard.add_page(page, last_page=True)
        assert page.get_wizard() is wizard


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
