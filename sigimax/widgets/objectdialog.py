# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Object dialog
-------------

This module provides a dialog box to select an object (signal or image) from
a remote DataLab-derived application, using
:class:`sigima.client.SimpleRemoteProxy` (or any proxy exposing the same
``get_group_titles_with_object_info``/``get_current_panel``/
``set_current_panel`` methods).

.. autoclass:: GetObjectDialog
    :members:
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING

from guidata.qthelpers import block_signals
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from sigimax.config import _
from sigimax.utils.svg_icons import GROUP, IMAGE, SIGNAL, svgtext_to_icon

if TYPE_CHECKING:  # pragma: no cover
    from sigima.client import SimpleRemoteProxy

__all__ = ["GetObjectDialog", "SimpleObjectTree"]


class SimpleObjectTree(QW.QTreeWidget):
    """Object list tree widget, populated from a remote proxy's groups/objects.

    Args:
        parent: Parent widget
    """

    SIG_ITEM_DOUBLECLICKED = QC.Signal(str)
    SIG_CONTEXT_MENU = QC.Signal(QC.QPoint)

    def __init__(self, parent: QW.QWidget) -> None:
        self.__obj_uuids: list[list[str]] = []
        self.__obj_titles: list[list[str]] = []
        self.__grp_titles: list[str] = []
        self.__panel_name: str = ""
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)
        self.itemDoubleClicked.connect(self.item_double_clicked)

    def __str__(self) -> str:
        """Return string representation"""
        textlist = []
        for tl_index in range(self.topLevelItemCount()):
            tl_item = self.topLevelItem(tl_index)
            textlist.append(tl_item.text(0))
            for index in range(tl_item.childCount()):
                textlist.append("    " + tl_item.child(index).text(0))
        return os.linesep.join(textlist)

    def initialize(self, proxy: SimpleRemoteProxy) -> None:
        """Initialize tree with objects, using proxy"""
        grp_titles, obj_uuids, obj_titles = proxy.get_group_titles_with_object_info()
        self.__grp_titles = grp_titles
        self.__obj_uuids = obj_uuids
        self.__obj_titles = obj_titles
        self.__panel_name = proxy.get_current_panel()
        self.populate_tree()

    def iter_items(
        self, item: QW.QTreeWidgetItem | None = None
    ) -> Iterator[QW.QTreeWidgetItem]:
        """Recursively iterate over all items"""
        if item is None:
            for index in range(self.topLevelItemCount()):
                yield from self.iter_items(self.topLevelItem(index))
        else:
            yield item
            for index in range(item.childCount()):
                yield from self.iter_items(item.child(index))

    def get_item_from_id(self, item_id) -> QW.QTreeWidgetItem:
        """Return QTreeWidgetItem from id (stored in item's data)"""
        for item in self.iter_items():
            if item.data(0, QC.Qt.UserRole) == item_id:
                return item
        return None

    def get_current_item_id(self, object_only: bool = False) -> str | None:
        """Return current item id"""
        item = self.currentItem()
        if item is not None and (not object_only or item.parent() is not None):
            return item.data(0, QC.Qt.UserRole)
        return None

    def set_current_item_id(self, uuid: str, extend: bool = False) -> None:
        """Set current item by id"""
        item = self.get_item_from_id(uuid)
        if extend:
            self.setCurrentItem(item, 0, QC.QItemSelectionModel.Select)
        else:
            self.setCurrentItem(item)

    @staticmethod
    def __update_item(
        item: QW.QTreeWidgetItem, number: int, prefix: str, title: str, uuid: str
    ) -> None:
        """Update item"""
        item.setText(0, f"{prefix}{number:03d}: {title}")
        item.setData(0, QC.Qt.UserRole, uuid)

    def populate_tree(self) -> None:
        """Populate tree with objects"""
        uuid = self.get_current_item_id()
        with block_signals(widget=self, enable=True):
            self.clear()
        for grp_idx, (grp_title, obj_uuids, obj_titles) in enumerate(
            zip(self.__grp_titles, self.__obj_uuids, self.__obj_titles)
        ):
            self.add_group_item(grp_idx + 1, grp_title, obj_uuids, obj_titles)
        if uuid is not None:
            self.set_current_item_id(uuid)

    def __add_to_group_item(
        self, number: int, obj_uuid: str, obj_title: str, group_item: QW.QTreeWidgetItem
    ) -> None:
        """Add object to group item"""
        item = QW.QTreeWidgetItem()
        prefix = self.__panel_name[0]
        svgtext = SIGNAL if prefix == "s" else IMAGE
        item.setIcon(0, svgtext_to_icon(svgtext))
        self.__update_item(item, number, prefix, obj_title, obj_uuid)
        group_item.addChild(item)

    def add_group_item(
        self, number: int, title: str, obj_uuids: list[str], obj_titles: list[str]
    ) -> None:
        """Add group item"""
        group_item = QW.QTreeWidgetItem()
        group_item.setIcon(0, svgtext_to_icon(GROUP))
        self.__update_item(group_item, number, "g", title, "")
        self.addTopLevelItem(group_item)
        group_item.setExpanded(True)
        for obj_idx, (obj_uuid, obj_title) in enumerate(zip(obj_uuids, obj_titles)):
            self.__add_to_group_item(obj_idx + 1, obj_uuid, obj_title, group_item)

    def item_double_clicked(self, item: QW.QTreeWidgetItem) -> None:
        """Item was double-clicked: emit signal for parent dialog to handle"""
        if item.parent() is not None:
            oid = item.data(0, QC.Qt.UserRole)
            self.SIG_ITEM_DOUBLECLICKED.emit(oid)

    def contextMenuEvent(self, event: QG.QContextMenuEvent) -> None:  # pylint: disable=invalid-name
        """Override Qt method"""
        self.SIG_CONTEXT_MENU.emit(event.globalPos())


class GetObjectDialog(QW.QDialog):
    """Get object dialog box

    Args:
        parent: Parent widget
        proxy: Remote proxy
        panel: Panel to retrieve objects from ('signal', 'image' or None for both)
        title: Dialog title
    """

    def __init__(
        self,
        parent: QW.QWidget,
        proxy: SimpleRemoteProxy,
        panel: str | None = None,
        title: str | None = None,
    ) -> None:
        super().__init__(parent)
        assert panel in (None, "signal", "image")
        self.__proxy = proxy
        self.__current_object_uuid: str | None = None
        self.setWindowTitle(_("Select object") if title is None else title)
        vlayout = QW.QVBoxLayout()
        self.setLayout(vlayout)

        panelgroup = None
        if panel is None:
            panelgroup = QW.QWidget()
            panellayout = QW.QHBoxLayout()
            panellayout.setContentsMargins(0, 0, 0, 0)
            panelgroup.setLayout(panellayout)
            panelcombo = QW.QComboBox()
            panelcombo.addItem(svgtext_to_icon(SIGNAL), _("Signals"))
            panelcombo.addItem(svgtext_to_icon(IMAGE), _("Images"))
            if proxy.get_current_panel() == "image":
                panelcombo.setCurrentIndex(1)
            panelcombo.currentIndexChanged.connect(self.__change_panel)
            panellabel = QW.QLabel(_("Active panel:"))
            panellayout.addWidget(panellabel)
            panellayout.addWidget(panelcombo)
            panellayout.setStretch(1, 1)
        else:
            self.__proxy.set_current_panel(panel)

        self.tree = SimpleObjectTree(parent)
        self.tree.initialize(proxy)
        self.tree.SIG_ITEM_DOUBLECLICKED.connect(lambda oid: self.accept())
        self.tree.itemSelectionChanged.connect(self.__current_object_changed)

        if panelgroup is not None:
            vlayout.addWidget(panelgroup)
        vlayout.addWidget(self.tree)

        bbox = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok | QW.QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        self.ok_btn = bbox.button(QW.QDialogButtonBox.Ok)
        vlayout.addSpacing(10)
        vlayout.addWidget(bbox)
        # Update OK button state:
        self.__current_object_changed()

    def __change_panel(self, index: int) -> None:
        """Change panel"""
        self.__proxy.set_current_panel("signal" if index == 0 else "image")
        self.tree.initialize(self.__proxy)
        self.__current_object_changed()

    def __current_object_changed(self) -> None:
        """Item selection has changed"""
        self.__current_object_uuid = self.tree.get_current_item_id()
        self.ok_btn.setEnabled(bool(self.__current_object_uuid))

    def get_current_object_uuid(self) -> str:
        """Return current object uuid"""
        return self.__current_object_uuid
