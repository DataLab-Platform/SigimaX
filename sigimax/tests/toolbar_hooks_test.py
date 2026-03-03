# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Toolbar hooks functional test
------------------------------

Verify that a derived application can fully customize the main toolbar
by overriding ``_create_global_actions()`` and ``_get_main_toolbar_actions()``
hooks provided by :class:`SGMXMainWindow`.

The test builds a minimal derived window that:

- Adds a custom "Settings" action via ``_create_global_actions``.
- Reorders toolbar actions and inserts a separator via
  ``_get_main_toolbar_actions``.
- Verifies toolbar content matches the expected layout.
- Verifies that default H5 actions are still present and functional.
"""

# guitest: show

from __future__ import annotations

from guidata.configtools import get_icon
from guidata.qthelpers import create_action
from qtpy import QtWidgets as QW

from sigimax.config import CONF as Conf
from sigimax.config import _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth

# =============================================================================
# Derived window with custom toolbar hooks
# =============================================================================


class CustomToolbarWindow(SGMXMainWindow):
    """Derived window exercising toolbar action hooks."""

    def __init__(self) -> None:
        Conf.app_name.set("ToolbarHookTest")
        Conf.app_version.set("0.0.1")

        self.settings_action: QW.QAction | None = None
        self.import_csv_action: QW.QAction | None = None

        super().__init__(console=False)

    # -- Global action hooks ---------------------------------------------------

    def _create_global_actions(self) -> None:
        """Create default actions, then add custom ones."""
        super()._create_global_actions()

        self.settings_action = create_action(
            self,
            _("Settings..."),
            icon=get_icon("libre-gui-settings.svg"),
            tip=_("Open settings dialog"),
        )
        self.import_csv_action = create_action(
            self,
            _("Import CSV..."),
            icon=get_icon("fileopen_signal.svg"),
            tip=_("Import data from a CSV file"),
        )

    def _get_main_toolbar_actions(self) -> list[QW.QAction | None]:
        """Custom toolbar: open, save, browse, separator, import CSV, settings."""
        return [
            self.openh5_action,
            self.saveh5_action,
            self.browseh5_action,
            None,  # separator
            self.import_csv_action,
            None,  # separator
            self.settings_action,
        ]


# =============================================================================
# Derived window that removes H5 actions from toolbar
# =============================================================================


class MinimalToolbarWindow(SGMXMainWindow):
    """Derived window with a minimal toolbar (no H5 actions)."""

    def __init__(self) -> None:
        Conf.app_name.set("MinimalToolbarTest")
        Conf.app_version.set("0.0.1")

        self.custom_action: QW.QAction | None = None

        super().__init__(console=False)

    def _create_global_actions(self) -> None:
        """Create default actions plus a single custom action."""
        super()._create_global_actions()

        self.custom_action = create_action(
            self,
            _("My Action"),
            tip=_("A custom action"),
        )

    def _get_main_toolbar_actions(self) -> list[QW.QAction | None]:
        """Only show the custom action in the toolbar."""
        return [self.custom_action]


# =============================================================================
# Helpers
# =============================================================================


def _get_toolbar_action_texts(toolbar: QW.QToolBar) -> list[str | None]:
    """Return action texts from a toolbar (None for separators)."""
    result: list[str | None] = []
    for action in toolbar.actions():
        if action.isSeparator():
            result.append(None)
        else:
            result.append(action.text())
    return result


# =============================================================================
# Test
# =============================================================================


def test_toolbar_hooks_custom():
    """Verify that toolbar hook overrides produce the expected toolbar layout."""
    with qth.sigimax_app_context(exec_loop=False):
        win = CustomToolbarWindow()
        win.resize(1000, 600)
        win.show()

        texts = _get_toolbar_action_texts(win.main_toolbar)

        # -- Default H5 actions must still be present -------------------------
        assert _("Open HDF5 files...") in texts, f"Missing Open HDF5: {texts}"
        assert _("Save to HDF5 file...") in texts, f"Missing Save HDF5: {texts}"
        assert _("Browse HDF5 file...") in texts, f"Missing Browse HDF5: {texts}"

        # -- Custom actions must be present -----------------------------------
        assert _("Import CSV...") in texts, f"Missing Import CSV: {texts}"
        assert _("Settings...") in texts, f"Missing Settings: {texts}"

        # -- Separators must be present (at least 2) --------------------------
        sep_count = texts.count(None)
        assert sep_count >= 2, f"Expected at least 2 separators, got {sep_count}"

        # -- Order: Open < Save < Browse < separator < Import CSV < separator < Settings
        idx_open = texts.index(_("Open HDF5 files..."))
        idx_save = texts.index(_("Save to HDF5 file..."))
        idx_browse = texts.index(_("Browse HDF5 file..."))
        idx_csv = texts.index(_("Import CSV..."))
        idx_settings = texts.index(_("Settings..."))

        assert idx_open < idx_save < idx_browse, (
            f"H5 actions out of order: {idx_open}, {idx_save}, {idx_browse}"
        )
        assert idx_browse < idx_csv < idx_settings, (
            f"Custom actions out of order: {idx_browse}, {idx_csv}, {idx_settings}"
        )

        # -- H5 actions are still usable (not None) --------------------------
        assert win.openh5_action is not None
        assert win.saveh5_action is not None
        assert win.browseh5_action is not None

        # -- Clean close ------------------------------------------------------
        win.set_modified(False)
        win.close()

    print("Toolbar hooks (custom) test passed.")


def test_toolbar_hooks_minimal():
    """Verify that a derived app can replace the toolbar entirely."""
    with qth.sigimax_app_context(exec_loop=False):
        win = MinimalToolbarWindow()
        win.resize(800, 500)
        win.show()

        texts = _get_toolbar_action_texts(win.main_toolbar)

        # -- Only the custom action should be in the toolbar ------------------
        real_actions = [t for t in texts if t is not None]
        assert real_actions == [_("My Action")], (
            f"Expected only 'My Action', got: {real_actions}"
        )

        # -- H5 actions should still exist (just not in toolbar) --------------
        assert win.openh5_action is not None, "openh5_action should still be created"
        assert win.saveh5_action is not None, "saveh5_action should still be created"
        assert win.browseh5_action is not None, (
            "browseh5_action should still be created"
        )

        # -- H5 actions are NOT in the toolbar --------------------------------
        assert _("Open HDF5 files...") not in texts, (
            "Open HDF5 should NOT be in minimal toolbar"
        )

        # -- Clean close ------------------------------------------------------
        win.set_modified(False)
        win.close()

    print("Toolbar hooks (minimal) test passed.")


if __name__ == "__main__":
    test_toolbar_hooks_custom()
    test_toolbar_hooks_minimal()
