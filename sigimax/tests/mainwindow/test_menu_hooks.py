# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Menu hooks functional test
--------------------------

Verify that a derived application can fully customize all menus
(file, view, help) by overriding the ``_get_*_menu_actions()`` and
``_update_*_menu()`` hooks provided by :class:`SGMXMainWindow`.

The test builds a minimal derived window that:

- Prepends a "New project" action to the file menu.
- Inserts a custom action between the H5 group and settings in the file menu.
- Overrides ``_is_save_enabled`` to always return ``False``.
- Appends a "Preferences" action to the view menu.
- Inserts a "Release notes" action before "About..." in the help menu.
- Adds a "Web API" separator + action after the default file menu via
  ``_update_file_menu`` override.
"""

# guitest: show

from __future__ import annotations

import pytest
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action
from qtpy import QtWidgets as QW

from sigimax.config import CONF as Conf
from sigimax.config import _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth

pytestmark = pytest.mark.app

# =============================================================================
# Derived window with custom menu hooks
# =============================================================================


class CustomMenuWindow(SGMXMainWindow):
    """Derived window exercising every menu hook."""

    def __init__(self) -> None:
        Conf.app_name.set("MenuHookTest")
        Conf.app_version.set("0.0.1")

        # Custom actions must be created BEFORE super().__init__() because
        # __add_menus() → _get_help_menu_actions() is called during setup().
        # We can use QWidget.__init__ indirectly — create_action only needs a
        # QObject parent, and ``self`` is already a valid QObject at this point
        # thanks to Python's MRO (QMainWindow.__init__ hasn't run yet, but
        # the C++ QObject exists after type.__call__ allocates the instance).
        # However, since create_action may depend on the widget being fully
        # initialized, we initialize the attributes to None first and create
        # the actions in a dedicated method called before super().__init__().
        self.new_project_action: QW.QAction | None = None
        self.import_csv_action: QW.QAction | None = None
        self.webapi_action: QW.QAction | None = None
        self.preferences_action: QW.QAction | None = None
        self.release_notes_action: QW.QAction | None = None

        super().__init__(console=False)

        # Now create actions (parent widget is fully initialized)
        self._create_custom_actions()

        # Rebuild help menu with our custom actions (it was built during
        # __add_menus with None placeholders)
        self.help_menu.clear()
        add_actions(self.help_menu, self._get_help_menu_actions())

    def _create_custom_actions(self) -> None:
        """Create custom actions after the widget is fully initialized."""
        self.new_project_action = create_action(
            self,
            _("New project"),
            icon=get_icon("libre-gui-add.svg"),
            tip=_("Create a new empty project"),
        )
        self.import_csv_action = create_action(
            self,
            _("Import CSV..."),
            icon=get_icon("fileopen_signal.svg"),
            tip=_("Import data from a CSV file"),
        )
        self.webapi_action = create_action(
            self,
            _("Web API status"),
            tip=_("Show Web API connection status"),
        )
        self.preferences_action = create_action(
            self,
            _("Preferences..."),
            tip=_("Edit application preferences"),
        )
        self.release_notes_action = create_action(
            self,
            _("Release notes"),
            tip=_("Show release notes"),
        )

    # -- File menu hooks -------------------------------------------------------

    def _is_save_enabled(self) -> bool:
        """Save is disabled when the workspace has no objects."""
        return False  # For testing: always disabled

    def _get_file_menu_actions(self) -> list[QW.QAction | None]:
        """Prepend 'New project' and insert 'Import CSV' after browse."""
        return [
            self.new_project_action,
            None,
            self.openh5_action,
            self.saveh5_action,
            self.browseh5_action,
            None,
            self.import_csv_action,
        ]

    def _update_file_menu(self) -> None:
        """Append Web API action after default population."""
        super()._update_file_menu()
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.webapi_action)

    # -- View menu hooks -------------------------------------------------------

    def _get_view_menu_actions(self) -> list[QW.QAction | None]:
        """Append 'Preferences' at the end of the view menu."""
        return super()._get_view_menu_actions() + [None, self.preferences_action]

    # -- Help menu hooks -------------------------------------------------------

    def _get_help_menu_actions(self) -> list[QW.QAction | None]:
        """Insert 'Release notes' just before 'About...'."""
        actions = super()._get_help_menu_actions()
        # During super().__init__(), custom actions are still None — skip
        if self.release_notes_action is None:
            return actions
        # Find the "About..." action (last one) and insert before it
        actions.insert(-1, None)
        actions.insert(-1, self.release_notes_action)
        return actions


# =============================================================================
# Helpers
# =============================================================================


def _get_action_texts(menu: QW.QMenu) -> list[str | None]:
    """Return action texts from a menu (None for separators)."""
    result: list[str | None] = []
    for action in menu.actions():
        if action.isSeparator():
            result.append(None)
        else:
            result.append(action.text())
    return result


# =============================================================================
# Test
# =============================================================================


def test_menu_hooks():
    """Verify that menu hook overrides produce the expected menu layout."""
    with qth.sigimax_app_context(exec_loop=False):
        win = CustomMenuWindow()
        win.resize(1000, 600)
        win.show()

        # -- Trigger file menu rebuild (simulates aboutToShow) ----------------
        win._update_file_menu()  # pylint: disable=protected-access
        file_texts = _get_action_texts(win.file_menu)

        # "New project" must be first real action (after leading separator)
        assert _("New project") in file_texts, f"Missing 'New project': {file_texts}"

        # "Import CSV..." must be present
        assert _("Import CSV...") in file_texts, f"Missing 'Import CSV': {file_texts}"

        # "Web API status" must be near the end (added by _update_file_menu)
        assert _("Web API status") in file_texts, (
            f"Missing 'Web API status': {file_texts}"
        )

        # "New project" before HDF5 actions
        idx_new = file_texts.index(_("New project"))
        idx_open = file_texts.index(_("Open HDF5 files..."))
        assert idx_new < idx_open, "New project should appear before Open HDF5"

        # "Import CSV..." between browse and settings
        idx_csv = file_texts.index(_("Import CSV..."))
        idx_browse = file_texts.index(_("Browse HDF5 file..."))
        assert idx_csv > idx_browse, "Import CSV should appear after Browse HDF5"

        # Save should be disabled
        assert not win.saveh5_action.isEnabled(), "Save should be disabled"

        # -- Trigger view menu rebuild ----------------------------------------
        win._update_view_menu()  # pylint: disable=protected-access
        view_texts = _get_action_texts(win.view_menu)

        assert _("Preferences...") in view_texts, f"Missing 'Preferences': {view_texts}"
        # Preferences should be last real action
        real_actions = [t for t in view_texts if t is not None]
        assert real_actions[-1] == _("Preferences...")

        # -- Verify help menu (built once at construction) --------------------
        help_texts = _get_action_texts(win.help_menu)

        assert _("Release notes") in help_texts, (
            f"Missing 'Release notes': {help_texts}"
        )
        assert _("About...") in help_texts, f"Missing 'About': {help_texts}"

        # "Release notes" must appear before "About..."
        idx_rn = help_texts.index(_("Release notes"))
        idx_about = help_texts.index(_("About..."))
        assert idx_rn < idx_about, "Release notes should appear before About"

        # -- Clean close ------------------------------------------------------
        win.set_modified(False)
        win.close()

    print("Menu hooks test passed.")


if __name__ == "__main__":
    test_menu_hooks()
