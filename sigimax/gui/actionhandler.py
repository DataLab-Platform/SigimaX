# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Action handler
==============

The :mod:`sigimax.gui.actionhandler` module handles all application actions
(menus, toolbars, context menu). These actions point to SigimaX panels, processors,
objecthandler, ...

Utility classes
---------------

.. autoclass:: SelectCond
    :members:

.. autoclass:: ActionCategory
    :members:

Handler classes
---------------

.. autoclass:: SignalActionHandler
    :members:
    :inherited-members:

.. autoclass:: ImageActionHandler
    :members:
    :inherited-members:
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import abc
import enum
from collections.abc import Generator
from contextlib import contextmanager

from guidata.configtools import get_icon
from guidata.qthelpers import add_actions
from qtpy import QtWidgets as QW


class ActionCategory(enum.Enum):
    """Action categories"""

    FILE = enum.auto()
    CREATE = enum.auto()
    EDIT = enum.auto()
    VIEW = enum.auto()
    OPERATION = enum.auto()
    PROCESSING = enum.auto()
    ANALYSIS = enum.auto()
    CONTEXT_MENU = enum.auto()
    VIEW_TOOLBAR = enum.auto()
    SUBMENU = enum.auto()  # temporary


class BaseActionHandler(metaclass=abc.ABCMeta):
    """Object handling panel GUI interactions: actions, menus, ...

    Args:
        panel: Panel to handle
        panel_toolbar: Panel toolbar (actions related to the panel objects management)
        view_toolbar: View toolbar (actions related to the panel view, i.e. plot)
    """

    OBJECT_STR = ""  # e.g. "signal"
    OBJECT_STR_PLURAL = ""  # e.g. "signals"

    def __init__(
        self,
        view_toolbar: QW.QToolBar,
    ):
        self.view_toolbar = view_toolbar
        self.feature_actions = {}
        self.operation_end_actions = None
        self.__category_in_progress: ActionCategory = None
        self.__submenu_in_progress = False
        self.__submenu_stack: list[dict[str, any]] = []  # Stack for nested submenus
        self.__submenus: dict[str, QW.QMenu] = {}
        # Store reference to show label action (for settings dialog)
        self.show_label_action: QW.QAction | None = None

    @property
    def object_suffix(self) -> str:
        """Object suffix (e.g. "sig" for signal, "ima" for image)"""
        return self.__class__.__name__[:3].lower()

    @contextmanager
    def new_category(self, category: ActionCategory) -> Generator[None, None, None]:
        """Context manager for creating a new menu.

        Args:
            category: Action category

        Yields:
            None
        """
        self.__category_in_progress = category
        try:
            yield
        finally:
            self.__category_in_progress = None

    @contextmanager
    def new_menu(
        self,
        title: str,
        icon_name: str | None = None,
        store_ref: str | None = None,
    ) -> Generator[None, None, None]:
        """Context manager for creating a new menu.

        Args:
            title: Menu title
            icon_name: Menu icon name. Defaults to None.
            store_ref: Optional attribute name to store menu reference.
             Defaults to None.

        Yields:
            None
        """
        # Create a unique key for this submenu level
        parent_key = ""
        if self.__submenu_stack:
            parent_key = self.__submenu_stack[-1]["key"] + "/"
        elif self.__category_in_progress:
            parent_key = self.__category_in_progress.name + "/"

        key = parent_key + title
        is_new = key not in self.__submenus

        if is_new:
            self.__submenus[key] = menu = QW.QMenu(title)
            if icon_name:
                menu.setIcon(get_icon(icon_name))
            # Store reference to menu if requested
            if store_ref is not None:
                setattr(self, store_ref, menu)
        else:
            menu = self.__submenus[key]

        # Save current submenu state and push new submenu onto stack
        submenu_state = {
            "key": key,
            "menu": menu,
            "is_new": is_new,
            "actions": [],  # Actions for this submenu level
        }
        self.__submenu_stack.append(submenu_state)
        self.__submenu_in_progress = True

        try:
            yield
        finally:
            # Pop the current submenu from stack
            current_submenu = self.__submenu_stack.pop()

            # Get actions for this specific submenu level
            submenu_actions = current_submenu.get("actions", [])

            # Also get any actions that were added to the generic SUBMENU category
            # while this submenu was the active one
            generic_submenu_actions = self.feature_actions.pop(
                ActionCategory.SUBMENU, []
            )
            submenu_actions.extend(generic_submenu_actions)

            add_actions(current_submenu["menu"], submenu_actions)

            # Update submenu in progress status BEFORE adding to parent
            self.__submenu_in_progress = len(self.__submenu_stack) > 0

            if current_submenu["is_new"]:
                # Add this submenu to its parent (either category or parent submenu)
                if self.__submenu_stack:
                    # We're in a nested submenu, add to parent submenu's actions
                    parent_submenu = self.__submenu_stack[-1]
                    parent_submenu["actions"].append(current_submenu["menu"])
                else:
                    # We're at the top level, add to category actions
                    # Force using the current category, not SUBMENU
                    self.add_to_action_list(
                        current_submenu["menu"], category=self.__category_in_progress
                    )

    def add_to_action_list(
        self,
        action: QW.QAction,
        category: ActionCategory | None = None,
        pos: int | None = None,
        sep: bool = False,
    ) -> None:
        """Add action to list of actions.

        Args:
            action: action to add
            category: action category. Defaults to None.
             If None, action is added to the current category.
            pos: add action to menu at this position. Defaults to None.
             If None, action is added at the end of the list.
            sep: add separator before action in menu
             (or after if pos is positive). Defaults to False.
        """
        if category is None:
            if self.__submenu_in_progress and self.__submenu_stack:
                # Add directly to the current submenu's action list
                current_submenu = self.__submenu_stack[-1]
                actionlist = current_submenu["actions"]
                if pos is None:
                    pos = -1
                add_separator_after = pos >= 0
                if pos < 0:
                    pos = len(actionlist) + pos + 1
                actionlist.insert(pos, action)
                if sep:
                    if add_separator_after:
                        pos += 1
                    actionlist.insert(pos, None)
                return
            if self.__category_in_progress is not None:
                category = self.__category_in_progress
            else:
                raise ValueError("No category specified")
        if pos is None:
            pos = -1
        actionlist = self.feature_actions.setdefault(category, [])
        add_separator_after = pos >= 0
        if pos < 0:
            pos = len(actionlist) + pos + 1
        actionlist.insert(pos, action)
        if sep:
            if add_separator_after:
                pos += 1
            actionlist.insert(pos, None)
