# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX HDF5 browser module

.. autoclass:: H5Browser
    :members:
.. autoclass:: H5BrowserDialog
    :members:
.. autoclass:: H5TreeWidget
    :members:
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import abc
import os
import os.path as osp
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Callable

from guidata.qthelpers import (
    add_actions,
    create_action,
    create_toolbutton,
    exec_dialog,
    get_icon,
    get_std_icon,
    win32_fix_title_bar_background,
)
from guidata.utils.misc import to_string
from guidata.widgets.arrayeditor import ArrayEditor
from plotpy.builder import make
from plotpy.plot import PlotOptions, PlotWidget
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from qtpy.compat import getopenfilename
from sigima import ImageObj, SignalObj

from sigimax.adapters_plotpy import CURVESTYLES, create_adapter_from_object
from sigimax.config import _, get_conf
from sigimax.env import execenv
from sigimax.h5 import H5Importer
from sigimax.h5.nexus import default_nxdata_path
from sigimax.h5.selection import NDView
from sigimax.h5.views import NDViewMixin, count_frames, expand_views
from sigimax.utils.qthelpers import block_signals, qt_handle_error_message

__all__ = [
    "AbstractTreeWidget",
    "H5Browser",
    "H5BrowserDialog",
    "H5FileSelector",
    "H5TreeWidget",
    "ViewSelector",
]

#: Number of frames of multidimensional datasets imported without confirmation
MAX_FRAMES_WITHOUT_CONFIRMATION = 100

if TYPE_CHECKING:
    from plotpy.plot import BasePlot

    from sigimax.h5.common import BaseNode


class AbstractTreeWidgetMeta(type(QW.QTreeWidget), abc.ABCMeta):
    """Mixed metaclass to avoid conflicts"""


class AbstractTreeWidget(QW.QTreeWidget, metaclass=AbstractTreeWidgetMeta):
    """One-column tree widget with context menu, ..."""

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(parent)
        self.setItemsExpandable(True)
        self.itemActivated.connect(self.activated)
        self.itemClicked.connect(self.clicked)
        # Setup context menu
        self.menu = QW.QMenu(self)
        self.collapse_all_action = None
        self.collapse_selection_action = None
        self.expand_all_action = None
        self.expand_selection_action = None
        self.common_actions = self.setup_common_actions()

        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.item_selection_changed()

    @abc.abstractmethod
    def activated(self, item: QW.QTreeWidgetItem) -> None:
        """Double-click event"""

    @abc.abstractmethod
    def clicked(self, item: QW.QTreeWidgetItem) -> None:
        """Item was clicked"""

    @abc.abstractmethod
    def get_actions_from_items(
        self, items: list[QW.QTreeWidgetItem]
    ) -> list[QW.QAction]:
        """Get actions from item"""
        # Right here: add other actions if necessary (reimplement this method)
        return []

    def setup_common_actions(self) -> list[QW.QAction]:
        """Setup context menu common actions"""
        self.collapse_all_action = create_action(
            self,
            _("Collapse all"),
            icon=get_icon("collapse.svg"),
            triggered=self.collapseAll,
        )
        self.expand_all_action = create_action(
            self, _("Expand all"), icon=get_icon("expand.svg"), triggered=self.expandAll
        )
        self.restore_action = create_action(
            self,
            _("Restore"),
            tip=_("Restore original tree layout"),
            icon=get_icon("restore.svg"),
            triggered=self.restore,
        )
        self.collapse_selection_action = create_action(
            self,
            _("Collapse selection"),
            icon=get_icon("collapse_selection.svg"),
            triggered=self.collapse_selection,
        )
        self.expand_selection_action = create_action(
            self,
            _("Expand selection"),
            icon=get_icon("expand_selection.svg"),
            triggered=self.expand_selection,
        )
        return [
            self.collapse_all_action,
            self.expand_all_action,
            self.restore_action,
            None,
            self.collapse_selection_action,
            self.expand_selection_action,
        ]

    def update_menu(self) -> None:
        """Update context menu"""
        self.menu.clear()
        items = self.selectedItems()
        actions = self.get_actions_from_items(items)
        if actions:
            actions.append(None)
        actions += self.common_actions
        add_actions(self.menu, actions)

    def restore(self) -> None:
        """Restore tree state"""
        self.collapseAll()
        for item in self.get_top_level_items():
            self.expandItem(item)

    def __expand_item(self, item: QW.QTreeWidgetItem) -> None:  # pragma: no cover
        """Expand item tree branch"""
        self.expandItem(item)
        for index in range(item.childCount()):
            child = item.child(index)
            self.__expand_item(child)

    def expand_selection(self) -> None:  # pragma: no cover
        """Expand selection"""
        items = self.selectedItems()
        if not items:
            items = self.get_top_level_items()
        for item in items:
            self.__expand_item(item)
        if items:
            self.scrollToItem(items[0])

    def __collapse_item(self, item: QW.QTreeWidgetItem) -> None:  # pragma: no cover
        """Collapse item tree branch"""
        self.collapseItem(item)
        for index in range(item.childCount()):
            child = item.child(index)
            self.__collapse_item(child)

    def collapse_selection(self) -> None:  # pragma: no cover
        """Collapse selection"""
        items = self.selectedItems()
        if not items:
            items = self.get_top_level_items()
        for item in items:
            self.__collapse_item(item)
        if items:
            self.scrollToItem(items[0])

    def item_selection_changed(self) -> None:
        """Item selection has changed"""
        is_selection = len(self.selectedItems()) > 0
        self.expand_selection_action.setEnabled(is_selection)
        self.collapse_selection_action.setEnabled(is_selection)

    def get_top_level_items(self) -> list[QW.QTreeWidgetItem]:
        """Iterate over top level items"""
        return [self.topLevelItem(_i) for _i in range(self.topLevelItemCount())]

    def find_all_items(self):
        """Find all items"""
        return self.findItems("", QC.Qt.MatchContains | QC.Qt.MatchRecursive)

    def contextMenuEvent(self, event: QG.QContextMenuEvent) -> None:
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())


class H5TreeWidget(AbstractTreeWidget):
    """HDF5 Browser Tree Widget

    Args:
        parent: Parent widget
    """

    SIG_SELECTED = QC.Signal(QW.QTreeWidgetItem)

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(parent)
        title = _("HDF5 Browser")
        self.setColumnCount(4)
        self.setWindowTitle(title)
        self.setHeaderLabels([_("Name"), _("Size"), _("Type"), _("Value")])
        self.header().setSectionResizeMode(0, QW.QHeaderView.Stretch)
        self.header().setStretchLastSection(False)
        self.fnames: list[str] = []
        self.h5importers: list[H5Importer] = []

    def add_root(self, fname: str) -> QW.QTreeWidgetItem | None:
        """Add HDF5 root (new file)

        Args:
            fname: HDF5 file name

        Returns:
            Item of the default NeXus ``NXdata`` group of the file (``@default``
            attributes), expanded, or None
        """
        self.fnames.append(osp.abspath(fname))
        importer = H5Importer(fname)
        self.h5importers.append(importer)
        self.add_root_to_tree(importer)
        # Temporarily expand all items to calculate proper column widths
        rootitem = self.topLevelItem(self.topLevelItemCount() - 1)
        self.expand_all_children(rootitem)
        for col in range(4):
            self.resizeColumnToContents(col)
        # Restore to default state (only root and its immediate children expanded)
        for index in range(rootitem.childCount()):
            child = rootitem.child(index)
            self.collapseItem(child)
        path = default_nxdata_path(importer.h5file)
        if path is None:
            return None
        item = self.find_node_item(rootitem, path)
        if item is not None:
            parent = item.parent()
            while parent is not None:
                self.expandItem(parent)
                parent = parent.parent()
        return item

    def find_node_item(
        self, rootitem: QW.QTreeWidgetItem, node_id: str
    ) -> QW.QTreeWidgetItem | None:
        """Return the item of a node of a file, by node id

        Args:
            rootitem: root item of the file
            node_id: node id
        """
        items = [rootitem]
        while items:
            item = items.pop()
            if item.data(0, QC.Qt.UserRole) == node_id:
                return item
            items.extend(item.child(index) for index in range(item.childCount()))
        return None

    def set_item_importable(self, item: QW.QTreeWidgetItem, state: bool) -> None:
        """Make the item of a multidimensional node checkable and checked, once
        the import of its frames is enabled, or neither of them

        Args:
            item: tree item
            state: True if the frames of the node are to be imported
        """
        node = self.get_node(item)
        with block_signals(self):
            if state:
                item.setFlags(
                    QC.Qt.ItemIsEnabled
                    | QC.Qt.ItemIsSelectable
                    | QC.Qt.ItemIsUserCheckable
                )
                item.setCheckState(0, QC.Qt.Checked)
            else:
                item.setData(0, QC.Qt.CheckStateRole, None)
                item.setFlags(QC.Qt.ItemIsEnabled)
            item.setIcon(0, get_icon(node.icon_name))
        self.itemChanged.emit(item, 0)

    def remove_root(self, fname: str) -> None:
        """Remove HDF5 root

        Args:
            fname: HDF5 file name
        """
        index = self.fnames.index(osp.abspath(fname))
        self.fnames.pop(index)
        importer = self.h5importers.pop(index)
        importer.close()
        # Remove root item associated with file
        item = self.topLevelItem(index)
        self.takeTopLevelItem(index)
        del item

    def cleanup(self) -> None:
        """Clean up widget"""
        for importer in self.h5importers:
            importer.close()
        self.fnames: list[str] = []
        self.h5importers: list[H5Importer] = []
        self.clear()

    def __get_top_level_item(self, item: QW.QTreeWidgetItem) -> QW.QTreeWidgetItem:
        """Get top level item associated to item

        Args:
            item: Tree item

        Returns:
            Top level item
        """
        while item.parent():
            item = item.parent()
        return item

    def get_node(self, item: QW.QTreeWidgetItem) -> BaseNode:
        """Get HDF5 dataset associated to item

        Args:
            item: Tree item

        Returns:
            HDF5 node
        """
        toplevel_item = self.__get_top_level_item(item)
        toplevel_index = self.indexOfTopLevelItem(toplevel_item)
        node_id = item.data(0, QC.Qt.UserRole)
        if node_id:
            importer = self.h5importers[toplevel_index]
            return importer.get(node_id)
        return None

    def get_nodes(
        self, only_checked_items: bool = True, expand: bool = True
    ) -> list[BaseNode]:
        """Get all nodes associated to checked items

        Multidimensional nodes are replaced by the nodes of the frames of their
        view (see :func:`sigimax.h5.views.expand_views`), unless ``expand`` is
        False.

        Args:
            only_checked_items: If True, only checked items are returned
            expand: If True, multidimensional nodes are replaced by the nodes of
             their frames

        Returns:
            List of HDF5 nodes
        """
        datasets = []
        for item in self.find_all_items():
            if item.flags() & QC.Qt.ItemIsUserCheckable:
                if only_checked_items and item.checkState(0) == QC.Qt.Unchecked:
                    continue
                if item is not self.topLevelItem(0):
                    node = self.get_node(item)
                    datasets.append(node)
        return expand_views(datasets) if expand else datasets

    def activated(self, item: QW.QTreeWidgetItem) -> None:
        """Double-click event"""
        if item is not self.topLevelItem(0):
            self.SIG_SELECTED.emit(item)

    def clicked(self, item: QW.QTreeWidgetItem) -> None:
        """Click event"""
        self.activated(item)

    def get_actions_from_items(self, items):  # pylint: disable=W0613
        """Get actions from item"""
        return []

    def is_empty(self) -> bool:
        """Return True if tree is empty"""
        return len(self.find_all_items()) == 1

    def is_any_item_checked(self) -> bool:
        """Return True if any item is checked"""
        for item in self.find_all_items():
            if item.checkState(0) != QC.Qt.Unchecked:
                return True
        return False

    def select_all(self, state: bool) -> None:
        """Select all items

        Args:
            state: If True, all items are selected
        """
        for item in self.find_all_items():
            if item.flags() & QC.Qt.ItemIsUserCheckable:
                item.setSelected(state)
                if state:
                    self.clicked(item)

    def toggle_all(self, state: bool) -> None:
        """Toggle all item state from 'unchecked' to 'checked'
        (or vice-versa)

        Args:
            state: If True, all items are checked
        """
        for item in self.find_all_items():
            if item.flags() & QC.Qt.ItemIsUserCheckable:
                item.setCheckState(0, QC.Qt.Checked if state else QC.Qt.Unchecked)

    @staticmethod
    def __create_node(node: BaseNode) -> QW.QTreeWidgetItem:
        """Create tree node from HDF5 node

        Args:
            node: HDF5 node

        Returns:
            Tree widget node
        """
        text = to_string(node.text)
        if len(text) > 30:
            text = text[:30] + "..."
        treeitem = QW.QTreeWidgetItem([node.name, node.shape_str, node.dtype_str, text])
        treeitem.setData(0, QC.Qt.UserRole, node.id)
        if node.description:
            for col in range(treeitem.columnCount()):
                treeitem.setToolTip(col, node.description)
        return treeitem

    @staticmethod
    def __recursive_popfunc(parent_item: QW.QTreeWidgetItem, node: BaseNode) -> None:
        """Recursive HDF5 analysis

        Args:
            parent_item: Parent tree item
            node: HDF5 node
        """
        tree_item = H5TreeWidget.__create_node(node)
        if node.is_supported():
            tree_item.setCheckState(0, QC.Qt.Unchecked)
        else:
            tree_item.setFlags(QC.Qt.ItemIsEnabled)
        tree_item.setIcon(0, get_icon(node.icon_name))
        parent_item.addChild(tree_item)
        for child in node.children:
            H5TreeWidget.__recursive_popfunc(tree_item, child)

    def expand_all_children(self, item: QW.QTreeWidgetItem) -> None:
        """Expand all children (recursively)

        Args:
            item: Tree item
        """
        self.expandItem(item)
        for index in range(item.childCount()):
            child = item.child(index)
            self.expand_all_children(child)

    def add_root_to_tree(self, importer: H5Importer) -> None:
        """Add root to tree

        Args:
            importer: HDF5 importer
        """
        root = importer.root
        rootitem = QW.QTreeWidgetItem([root.name])
        rootitem.setToolTip(0, root.description)
        rootitem.setData(0, QC.Qt.UserRole, root.id)
        rootitem.setFlags(QC.Qt.ItemIsEnabled)
        rootitem.setIcon(0, get_icon(root.icon_name))
        self.addTopLevelItem(rootitem)
        for node in root.children:
            self.__recursive_popfunc(rootitem, node)
        self.expandItem(rootitem)

    def toggle_show_only_checkable_items(self, state: bool) -> None:
        """Show only checkable items

        Args:
            state: If True, only checkable items are shown
        """
        for item in self.find_all_items():
            item.setHidden(state)
        if state:
            # Iterate over checkable items and show them (and their parents)
            for item in self.find_all_items():
                if item.flags() & QC.Qt.ItemIsUserCheckable:
                    item.setHidden(False)
                    parent = item.parent()
                    while parent:
                        parent.setHidden(False)
                        parent = parent.parent()

    def toggle_show_values(self, state: bool) -> None:
        """Show values

        Args:
            state: If True, values are shown
        """
        # Hide or show the "Value" column
        self.setColumnHidden(3, not state)

    def set_current_file(self, fname: str) -> None:
        """Set current file

        Args:
            fname: HDF5 file name
        """
        index = self.fnames.index(osp.abspath(fname))
        item = self.topLevelItem(index)
        self.setCurrentItem(item)
        self.scrollToItem(item, QW.QAbstractItemView.PositionAtTop)


class PlotPreview(QW.QStackedWidget):
    """Plot preview

    Preview data is read in a worker thread, so that the browser stays responsive
    while a large dataset is read. Nodes may provide a decimated preview object
    for datasets larger than :attr:`MAX_ITEMS` (see
    :meth:`sigimax.h5.common.BaseNode.create_preview_object`). The preview of a
    node replaces any pending one: previews of nodes selected meanwhile are not
    read.
    """

    #: Maximum number of data elements read for a preview
    MAX_ITEMS = 2**24

    SIG_LOADED = QC.Signal(int, object, object)

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(parent)
        self.__generation = 0
        self.__executor: ThreadPoolExecutor | None = None
        self.__pending: Future | None = None
        self.SIG_LOADED.connect(self.__show_loaded_object)
        self.curvewidget = PlotWidget(
            self,
            options=PlotOptions(
                type="curve",
                curve_antialiasing=True,
                show_axes_tab=False,
                autoscale_margin_percent=get_conf().sig_autoscale_margin_percent.get(),
            ),
        )
        self.addWidget(self.curvewidget)
        self.imagewidget = PlotWidget(
            self,
            options=PlotOptions(
                type="image",
                show_contrast=True,
                show_axes_tab=False,
                autoscale_margin_percent=get_conf().ima_autoscale_margin_percent.get(),
            ),
        )
        self.addWidget(self.imagewidget)

    def cleanup(self) -> None:
        """Clean up widget, and stop its worker thread"""
        self.wait()
        if self.__executor is not None:
            self.__executor.shutdown(wait=True)
            self.__executor = None
        for widget in (self.imagewidget, self.curvewidget):
            widget.get_plot().del_all_items()

    def discard(self) -> None:
        """Discard the pending previews, without waiting: the preview being read,
        if any, is not shown and the previews not started yet are not read"""
        self.__generation += 1
        if self.__pending is not None:
            self.__pending.cancel()
            self.__pending = None

    def clear_preview(self) -> None:
        """Discard the pending previews and clear the plot, without waiting (for
        nodes that cannot be previewed)"""
        self.discard()
        plot: BasePlot = self.currentWidget().get_plot()
        plot.del_all_items()
        plot.replot()

    def wait(self) -> None:
        """Discard the pending previews and wait until no data is read
        (before closing HDF5 files or importing objects)"""
        self.discard()
        if self.__executor is not None:
            # The single worker runs calls in order: once this one is done, the
            # previous ones are done or were discarded
            self.__executor.submit(int).result()

    def __load_object(self, generation: int, node: BaseNode) -> None:
        """Create the preview object of a node (worker thread)"""
        if generation != self.__generation:
            return  # Another node was selected meanwhile: do not read this one
        obj, error = None, None
        try:
            obj = node.create_preview_object(self.MAX_ITEMS)
        except Exception as exc:  # pylint: disable=broad-except
            error = exc
        try:
            self.SIG_LOADED.emit(generation, obj, error)
        except RuntimeError:
            pass  # Widget deleted while the data was read

    def __show_message(self, text: str) -> None:
        """Show a message instead of the preview"""
        label = make.label(text, "C", (0, 0), "C")
        plot: BasePlot = self.currentWidget().get_plot()
        plot.del_all_items()
        plot.add_item(label)
        plot.replot()

    def update_plot_preview(self, node: BaseNode) -> None:
        """Update plot preview widget"""
        self.__generation += 1
        if self.__pending is not None:
            self.__pending.cancel()
        self.__show_message(_("Loading..."))
        if self.__executor is None:
            self.__executor = ThreadPoolExecutor(1, thread_name_prefix="h5preview")
        self.__pending = self.__executor.submit(
            self.__load_object, self.__generation, node
        )

    def __show_loaded_object(
        self, generation: int, obj: SignalObj | ImageObj | None, error: Exception
    ) -> None:
        """Show the preview object, unless another node was selected meanwhile"""
        if generation != self.__generation:
            return
        if error is not None:
            self.__show_message(_("Unsupported data"))
            qt_handle_error_message(self, error)
            return
        if obj is None:
            # An error occurred while creating the object (invalid data, ...)
            self.__show_message(_("Unsupported data"))
            return
        if isinstance(obj, SignalObj):
            obj: SignalObj
            widget = self.curvewidget
        else:
            obj: ImageObj
            widget = self.imagewidget
        with CURVESTYLES.suspend():
            item = create_adapter_from_object(obj).make_item()
        plot = widget.get_plot()
        plot.del_all_items()
        plot.add_item(item)
        plot.set_active_item(item)
        item.unselect()
        plot.do_autoscale()
        self.setCurrentWidget(widget)


class ViewSelector(QW.QGroupBox):
    """View of the multidimensional dataset selected in the HDF5 browser

    The view shows frames of the dataset: signals along one axis or images of two
    axes, taken along another axis from a first to a last index with a step, the
    other axes being fixed. Its first frame is previewed; the frames are imported
    once "Import these frames" is checked.
    """

    #: Emitted when the view is changed (to update the preview)
    SIG_VIEW_CHANGED = QC.Signal()
    #: Emitted when the import of the frames is enabled or disabled
    SIG_IMPORT_CHANGED = QC.Signal(bool)

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(_("Multidimensional data"), parent)
        self.node: NDViewMixin | None = None
        self.__views: list[tuple[int, ...]] = []
        self.__hidden: list[int] = []
        self.view_combo = QW.QComboBox(self)
        self.frame_combo = QW.QComboBox(self)
        self.first_spin = QW.QSpinBox(self)
        self.last_spin = QW.QSpinBox(self)
        self.step_spin = QW.QSpinBox(self)
        self.step_spin.setMinimum(1)
        self.fixed_spins: dict[int, QW.QSpinBox] = {}
        self.fixed_layout = QW.QHBoxLayout()
        self.count_label = QW.QLabel(self)
        self.import_check = QW.QCheckBox(_("Import these frames"), self)
        frames = QW.QHBoxLayout()
        for label, spin in (
            (_("First"), self.first_spin),
            (_("Last"), self.last_spin),
            (_("Step"), self.step_spin),
        ):
            frames.addWidget(QW.QLabel(label, self))
            frames.addWidget(spin)
        frames.addStretch()
        layout = QW.QFormLayout(self)
        layout.addRow(_("View"), self.view_combo)
        layout.addRow(_("Frames along"), self.frame_combo)
        layout.addRow("", frames)
        layout.addRow(_("Fixed indices"), self.fixed_layout)
        layout.addRow(self.count_label, self.import_check)
        self.view_combo.currentIndexChanged.connect(self.__view_combo_changed)
        self.frame_combo.currentIndexChanged.connect(self.__frame_combo_changed)
        for spin in (self.first_spin, self.last_spin, self.step_spin):
            spin.valueChanged.connect(self.__view_edited)
        self.import_check.toggled.connect(self.__import_toggled)
        self.setVisible(False)

    @property
    def ndim(self) -> int:
        """Return the number of dimensions of the dataset"""
        return len(self.node.nd_shape)

    def set_node(self, node: BaseNode | None) -> None:
        """Show the view of a node, or hide the selector if the node has no view

        Args:
            node: HDF5 node
        """
        if not isinstance(node, NDViewMixin) or node.view is None:
            self.node = None
            self.setVisible(False)
            return
        self.node = node
        view = node.view
        self.__views = [
            (row, column)
            for row in range(self.ndim)
            for column in range(row + 1, self.ndim)
        ] + [(dim,) for dim in range(self.ndim)]
        if view.displayed not in self.__views:
            self.__views.append(view.displayed)
        with block_signals(self.view_combo):
            self.view_combo.clear()
            for displayed in self.__views:
                self.view_combo.addItem(self.__view_text(displayed))
            self.view_combo.setCurrentIndex(self.__views.index(view.displayed))
        self.__set_hidden_axes(view)
        with block_signals(self.import_check):
            self.import_check.setChecked(node.import_view)
        self.__update_count()
        self.setVisible(True)

    def __view_text(self, displayed: tuple[int, ...]) -> str:
        """Return the text of a view of the view combo box"""
        labels = [self.node.axis_label(dim) for dim in displayed]
        if len(displayed) == 1:
            return _("Signals along axis %s") % labels[0]
        return _("Images: rows along axis %s, columns along axis %s") % tuple(labels)

    def __set_hidden_axes(self, view: NDView) -> None:
        """Set the frame axis combo box and the fixed index spin boxes from a view"""
        shape = self.node.nd_shape
        self.__hidden = view.hidden_axes(self.ndim)
        indices = dict(zip(self.__hidden, view.indices))
        with block_signals(self.frame_combo):
            self.frame_combo.clear()
            for dim in self.__hidden:
                self.frame_combo.addItem(_("axis %s") % self.node.axis_label(dim))
            frame_axis = view.frame_axis
            if frame_axis is None:
                frame_axis = self.__hidden[0]
            self.frame_combo.setCurrentIndex(self.__hidden.index(frame_axis))
        for spin in self.fixed_spins.values():
            self.fixed_layout.removeWidget(spin)
            spin.deleteLater()
        self.fixed_spins = {}
        for dim in self.__hidden:
            if dim == frame_axis:
                continue
            spin = QW.QSpinBox(self)
            spin.setRange(0, shape[dim] - 1)
            spin.setValue(indices[dim])
            spin.setPrefix(f"{dim}: ")
            spin.valueChanged.connect(self.__view_edited)
            self.fixed_spins[dim] = spin
            self.fixed_layout.addWidget(spin)
        last = view.last if view.frame_axis is not None else shape[frame_axis] - 1
        self.__set_range(shape[frame_axis], indices[frame_axis], last, view.step)

    def __set_range(self, size: int, first: int, last: int, step: int) -> None:
        """Set the frame range spin boxes"""
        spins = (self.first_spin, self.last_spin, self.step_spin)
        for spin in spins:
            spin.blockSignals(True)
        try:
            self.first_spin.setRange(0, size - 1)
            self.last_spin.setRange(0, size - 1)
            self.step_spin.setRange(1, max(1, size))
            self.first_spin.setValue(first)
            self.last_spin.setValue(last)
            self.step_spin.setValue(step)
        finally:
            for spin in spins:
                spin.blockSignals(False)

    def current_view(self) -> NDView:
        """Return the view set in the selector"""
        displayed = self.__views[self.view_combo.currentIndex()]
        frame_axis = self.__hidden[self.frame_combo.currentIndex()]
        indices = tuple(
            self.first_spin.value()
            if dim == frame_axis
            else self.fixed_spins[dim].value()
            for dim in self.__hidden
        )
        last = max(self.last_spin.value(), self.first_spin.value())
        return NDView(displayed, indices, frame_axis, last, self.step_spin.value())

    def __view_combo_changed(self, index: int) -> None:
        """Displayed axes changed: every frame along the first hidden axis"""
        displayed = self.__views[index]
        hidden = [dim for dim in range(self.ndim) if dim not in displayed]
        last = self.node.nd_shape[hidden[0]] - 1
        view = NDView(displayed, tuple(0 for _dim in hidden), hidden[0], last)
        self.__set_hidden_axes(view)
        self.__view_edited()

    def __frame_combo_changed(self, index: int) -> None:
        """Frame axis changed: every frame along the new axis, the former frame axis
        being fixed at the first frame"""
        displayed = self.__views[self.view_combo.currentIndex()]
        frame_axis = self.__hidden[index]
        previous = {dim: spin.value() for dim, spin in self.fixed_spins.items()}
        indices = tuple(
            0 if dim == frame_axis else previous.get(dim, self.first_spin.value())
            for dim in self.__hidden
        )
        last = self.node.nd_shape[frame_axis] - 1
        view = NDView(displayed, indices, frame_axis, last)
        self.__set_hidden_axes(view)
        self.__view_edited()

    def __update_count(self) -> None:
        """Show the number of frames of the view"""
        count = self.node.frame_count()
        kind = _("images") if len(self.node.view.displayed) == 2 else _("signals")
        self.count_label.setText(_("%d frame(s) as %s") % (count, kind))

    def __view_edited(self) -> None:
        """Apply the view set in the selector to the node"""
        if self.node is None:
            return
        try:
            self.node.set_view(self.current_view(), self.node.import_view)
        except ValueError:
            return
        self.__update_count()
        self.SIG_VIEW_CHANGED.emit()

    def __import_toggled(self, state: bool) -> None:
        """Enable or disable the import of the frames"""
        if self.node is None:
            return
        self.node.set_view(self.current_view(), state)
        self.SIG_IMPORT_CHANGED.emit(state)


class TablePreview(QW.QWidget):
    """Table preview

    Args:
        title: Group title
        parent: Parent widget
    """

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(parent)
        self.setLayout(QW.QVBoxLayout())
        self.table = QW.QTableWidget(self)
        self.table.setEditTriggers(QW.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout().addWidget(self.table)

    def clear(self) -> None:
        """Clear table"""
        self.table.clear()

    def update_table_preview(self, data: dict[str, Any]) -> None:
        """Update table preview widget

        Args:
            node: HDF5 node
        """
        self.clear()
        self.table.setRowCount(len(data))
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels([_("Value")])
        self.table.setVerticalHeaderLabels(list(data.keys()))
        for row, value in enumerate(data.values()):
            self.table.setItem(row, 0, QW.QTableWidgetItem(str(value)))
        self.table.resizeRowsToContents()


class GroupAndAttributes(QW.QTabWidget):
    """Group and attributes

    Args:
        parent: Parent widget
        show_array_callback: Callback to show array
    """

    def __init__(self, parent: QW.QWidget, show_array_callback: Callable) -> None:
        super().__init__(parent)
        self.group = TablePreview(self)
        self.addTab(self.group, get_icon("h5group.svg"), _("Group"))
        self.attrs = TablePreview(self)
        self.addTab(self.attrs, get_icon("h5attrs.svg"), _("Attributes"))
        # Add a button as corner widget to show the array (if any):
        self.__show_array_btn = create_toolbutton(
            self,
            icon=get_icon("show_results.svg"),
            text=_("Show array"),
            autoraise=False,
            triggered=show_array_callback,
        )
        self.__show_array_btn.setEnabled(False)
        self.setCornerWidget(self.__show_array_btn, QC.Qt.TopRightCorner)

    def cleanup(self) -> None:
        """Clean up widget"""
        self.group.clear()
        self.attrs.clear()
        self.__show_array_btn.setEnabled(False)

    def update_from_node(self, node: BaseNode) -> None:
        """Update widget from node

        Args:
            node: HDF5 node
        """
        # Update group =================================================================
        text = to_string(node.text)
        if text:
            lines = text.splitlines()[:5]
            if len(lines) == 5:
                lines += ["[...]"]
            text = os.linesep.join(lines)
        data = {
            _("Path"): node.id,
            _("Name"): node.name,
            _("Description"): node.description,
            _("Textual preview"): text,
            # "Raw": repr(node.data),
        }
        self.group.update_table_preview(data)

        # Update attributes ============================================================
        self.attrs.update_table_preview(node.metadata)

        # Update show array button =====================================================
        self.__show_array_btn.setEnabled(node.IS_ARRAY)


class H5FileSelector(QW.QWidget):
    """HDF5 file selector

    Args:
        parent: Parent widget
    """

    SIG_ADD_FILENAME = QC.Signal(str)
    SIG_REMOVE_FILENAME = QC.Signal(str)
    SIG_CURRENT_CHANGED = QC.Signal(str)

    def __init__(self, parent: QW.QWidget) -> None:
        super().__init__(parent)
        self.setLayout(QW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.combo = QW.QComboBox(self)
        self.combo.currentTextChanged.connect(self.current_file_changed)
        self.layout().addWidget(self.combo)
        self.btn_add = create_toolbutton(
            self,
            icon=get_std_icon("DirOpenIcon"),
            text=_("Open") + " ...",
            autoraise=False,
            triggered=lambda _checked=False: self.add_file(),
        )
        self.btn_add.setSizePolicy(QW.QSizePolicy.Fixed, QW.QSizePolicy.Fixed)
        self.layout().addWidget(self.btn_add)
        self.btn_rmv = create_toolbutton(
            self,
            icon=get_std_icon("DialogCloseButton"),
            text=_("Close"),
            autoraise=False,
            triggered=self.remove_file,
        )
        self.btn_rmv.setSizePolicy(QW.QSizePolicy.Fixed, QW.QSizePolicy.Fixed)
        self.layout().addWidget(self.btn_rmv)
        self.btn_rmv.setEnabled(False)

    def set_current_fname(self, fname: str) -> None:
        """Set current file name

        Args:
            fname: HDF5 file name
        """
        index = self.combo.findText(fname)
        if index >= 0:
            self.combo.setCurrentIndex(index)

    def get_current_fname(self) -> str:
        """Return current file name

        Returns:
            HDF5 file name
        """
        return self.combo.currentText()

    def current_file_changed(self, fname: str) -> None:
        """Current file changed

        Args:
            fname: HDF5 file name
        """
        self.SIG_CURRENT_CHANGED.emit(fname)

    def add_fname(self, fname: str) -> None:
        """Add file name

        Args:
            fname: HDF5 file name
        """
        self.combo.addItem(get_icon("h5file.svg"), fname)
        self.btn_rmv.setEnabled(True)

    def remove_fname(self, fname: str) -> None:
        """Remove file name

        Args:
            fname: HDF5 file name
        """
        index = self.combo.findText(fname)
        if index >= 0:
            self.combo.removeItem(index)
        if self.combo.count() == 0:
            self.btn_rmv.setEnabled(False)

    def add_file(self, fname: str | None = None) -> None:
        """Browse file

        Args:
            fname: HDF5 file name. Default is None.
             (this is used for testing only)
        """
        if fname is None:
            fname = getopenfilename(
                self,
                _("Select HDF5 file"),
                "",
                _("HDF5 files (*.h5 *.hdf5 *.hdf *.he5 *.nxs *.nx5);;All files (*)"),
            )[0]
        if fname:
            self.SIG_ADD_FILENAME.emit(osp.abspath(fname))

    def remove_file(self, fname: str | None = None) -> None:
        """Remove file name

        Args:
            fname: HDF5 file name
        """
        if fname is None:
            fname = self.combo.currentText()
        self.SIG_REMOVE_FILENAME.emit(fname)


class H5Browser(QW.QSplitter):
    """HDF5 Browser Widget

    Args:
        parent: Parent widget
    """

    SIG_SELECT_NEW_FILE = QC.Signal(str)
    SIG_REMOVE_FILE = QC.Signal(str)

    def __init__(self, parent: QW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.__current_item: QW.QTreeWidgetItem | None = None
        if parent is None:
            self.setWindowIcon(get_icon(get_conf().app_logo_path.get()))
        self.selector = H5FileSelector(self)
        self.selector.SIG_ADD_FILENAME.connect(self.__add_new_file)
        self.selector.SIG_REMOVE_FILENAME.connect(self.__remove_file)
        self.selector.SIG_CURRENT_CHANGED.connect(self.__selector_current_file_changed)
        self.tree = H5TreeWidget(self)
        self.tree.SIG_SELECTED.connect(self.__item_selected_on_tree)
        selectorandtree = QW.QFrame(self)
        selectorandtree.setLayout(QW.QVBoxLayout())
        selectorandtree.layout().addWidget(self.selector)
        # Add toolbar with tree actions
        toolbar = self.__create_toolbar()
        selectorandtree.layout().addWidget(toolbar)
        selectorandtree.layout().addWidget(self.tree)
        selectorandtree.layout().setContentsMargins(0, 0, 0, 0)
        self.addWidget(selectorandtree)
        preview = QW.QSplitter(self)
        preview.setOrientation(QC.Qt.Vertical)
        self.addWidget(preview)
        self.plotpreview = PlotPreview(self)
        self.viewselector = ViewSelector(self)
        self.viewselector.SIG_VIEW_CHANGED.connect(self.__view_changed)
        self.viewselector.SIG_IMPORT_CHANGED.connect(self.__view_import_changed)
        plotandview = QW.QWidget(self)
        plotandview.setLayout(QW.QVBoxLayout())
        plotandview.layout().setContentsMargins(0, 0, 0, 0)
        plotandview.layout().addWidget(self.plotpreview)
        plotandview.layout().addWidget(self.viewselector)
        preview.addWidget(plotandview)
        self.groupandattrs = GroupAndAttributes(self, self.show_array)
        preview.addWidget(self.groupandattrs)
        preview.setSizes([int(self.size().height() / 2)] * 2)
        self.tree.itemChanged.connect(self.__item_changed)

    def __create_toolbar(self) -> QW.QToolBar:
        """Create toolbar with tree actions

        Returns:
            Toolbar widget
        """
        toolbar = QW.QToolBar(self)
        toolbar.setToolButtonStyle(QC.Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QC.QSize(16, 16))
        toolbar.setStyleSheet("QToolBar { padding: 2px; spacing: 2px; }")
        toolbar.addAction(self.tree.expand_all_action)
        toolbar.addAction(self.tree.collapse_all_action)
        toolbar.addAction(self.tree.restore_action)
        toolbar.addSeparator()
        toolbar.addAction(self.tree.expand_selection_action)
        toolbar.addAction(self.tree.collapse_selection_action)
        return toolbar

    def open_file(self, fname: str) -> None:
        """Open HDF5 file, and select its default NeXus ``NXdata`` group, if any

        Args:
            fname: HDF5 file name
        """
        default_item = self.tree.add_root(fname)
        self.selector.add_fname(fname)
        if default_item is not None:
            self.tree.setCurrentItem(default_item)
            self.tree.scrollToItem(default_item)
            self.__item_selected_on_tree(default_item)

    def close_file(self, fname: str) -> None:
        """Close HDF5 file

        Args:
            fname: HDF5 file name
        """
        self.plotpreview.wait()
        self.__current_item = None
        self.groupandattrs.cleanup()
        self.viewselector.set_node(None)
        self.tree.remove_root(fname)
        self.selector.remove_fname(fname)

    def __add_new_file(self, fname: str) -> None:
        """Add new file

        Args:
            fname: HDF5 file name
        """
        self.open_file(fname)
        self.selector.set_current_fname(fname)
        self.SIG_SELECT_NEW_FILE.emit(fname)

    def __remove_file(self, fname: str) -> None:
        """Remove file

        Args:
            fname: HDF5 file name
        """
        self.close_file(fname)
        self.SIG_REMOVE_FILE.emit(fname)

    def cleanup(self) -> None:
        """Clean up widget"""
        self.plotpreview.cleanup()
        self.tree.cleanup()

    def get_node(self, item: QW.QTreeWidgetItem | None = None) -> BaseNode:
        """Return (selected) dataset

        Args:
            item: Tree item

        Returns:
            HDF5 node
        """
        if item is None:
            item = self.tree.currentItem()
        return self.tree.get_node(item)

    def __item_selected_on_tree(self, item: QW.QTreeWidgetItem) -> None:
        """Item selected on tree

        Args:
            item: Tree item
        """
        # View the selected item
        node = self.get_node(item)
        self.__current_item = item
        # Discard the previous preview first: its pending read is not started,
        # so that reading the node description below does not wait for it
        self.plotpreview.discard()
        self.groupandattrs.update_from_node(node)
        self.viewselector.set_node(node)
        if node.can_preview():
            self.plotpreview.update_plot_preview(node)
        else:
            self.plotpreview.clear_preview()
        # Update the file selector combo box
        with block_signals(self.selector.combo):
            # Avoid triggering current file changed signal, which would result in
            # loosing the current selection on the tree (side effect: "Show array"
            # button would still be enabled if the previous node was an array, except
            # that now the current node is not an array, thus causing an error if
            # the user clicks on the button).
            self.selector.set_current_fname(node.h5file.filename)

    def __selector_current_file_changed(self, fname: str) -> None:
        """Selector current file changed

        Args:
            fname: HDF5 file name
        """
        if fname:
            self.tree.set_current_file(fname)

    def __view_changed(self) -> None:
        """View of the current multidimensional node changed: preview it"""
        self.plotpreview.update_plot_preview(self.viewselector.node)

    def __view_import_changed(self, state: bool) -> None:
        """Import of the frames of the current multidimensional node enabled or
        disabled: make its item checkable and checked, or not"""
        if self.__current_item is not None:
            self.tree.set_item_importable(self.__current_item, state)

    def __item_changed(self, item: QW.QTreeWidgetItem, _column: int = 0) -> None:
        """Item check state changed: an unchecked multidimensional node is not
        imported any more"""
        node = self.tree.get_node(item)
        if not isinstance(node, NDViewMixin) or not node.import_view:
            return
        if item.checkState(0) == QC.Qt.Unchecked:
            node.import_view = False
            self.tree.set_item_importable(item, False)
            if self.viewselector.node is node:
                self.viewselector.set_node(node)

    def show_array(self) -> None:
        """Show array of the current node, if it is an array

        The "Show array" button is enabled when an array is selected with the
        mouse: the current node may have changed since (e.g. with the keyboard).
        """
        item = self.tree.currentItem()
        node = None if item is None else self.get_node(item)
        if node is None or not node.IS_ARRAY:
            return
        arrayeditor = ArrayEditor(self)
        arrayeditor.setup_and_check(
            node.data, title=node.name, readonly=True, add_title_suffix=False
        )
        exec_dialog(arrayeditor)


class H5BrowserDialog(QW.QDialog):
    """HDF5 Browser Dialog

    Args:
        parent: Parent widget
        size: Dialog size
    """

    def __init__(
        self, parent: QW.QWidget | None = None, size: tuple[int, int] = (1150, 700)
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(QC.Qt.Window)
        self.setObjectName("h5browser")
        self.setWindowTitle(_("HDF5 Browser"))
        self.setWindowIcon(get_icon("h5browser.svg"))
        win32_fix_title_bar_background(self)
        vlayout = QW.QVBoxLayout()
        self.setLayout(vlayout)
        self.button_layout: QW.QHBoxLayout | None = None
        self.bbox: QW.QDialogButtonBox | None = None
        self.nodes: list[BaseNode] = []
        self.checkbox_show_only: QW.QCheckBox | None = None
        self.checkbox_show_values: QW.QCheckBox | None = None

        self.browser = H5Browser(self)
        self.browser.SIG_SELECT_NEW_FILE.connect(self.select_new_file)
        self.browser.SIG_REMOVE_FILE.connect(self.remove_file)
        vlayout.addWidget(self.browser)

        self.browser.tree.itemChanged.connect(lambda item: self.refresh_buttons())

        self.install_button_layout()

        self.setMinimumSize(QC.QSize(900, 500))
        self.resize(QC.QSize(*size))
        self.browser.setSizes([int(self.size().height() / 2)] * 2)
        self.refresh_buttons()

    def accept(self) -> None:
        """Accept changes, once confirmed if many frames of multidimensional
        datasets are to be imported (the frames are counted, and only created
        once confirmed)"""
        nodes = self.browser.tree.get_nodes(expand=False)
        frames = count_frames(nodes)
        if (
            frames > MAX_FRAMES_WITHOUT_CONFIRMATION
            and not execenv.unattended
            and QW.QMessageBox.question(
                self,
                self.windowTitle(),
                _("%d frames of multidimensional datasets will be imported.") % frames
                + "\n"
                + _("Do you want to continue?"),
            )
            != QW.QMessageBox.Yes
        ):
            return
        self.nodes = expand_views(nodes)
        QW.QDialog.accept(self)

    def done(self, result: int) -> None:
        """Close dialog, once the preview being read is done: the selected nodes
        are then read by the caller, and the files closed"""
        self.browser.plotpreview.wait()
        super().done(result)

    def is_empty(self) -> bool:
        """Return True if tree is empty"""
        return self.browser.tree.is_empty()

    def cleanup(self) -> None:
        """Cleanup dialog"""
        self.browser.cleanup()

    def refresh_buttons(self) -> None:
        """Refresh buttons"""
        state = self.browser.tree.is_any_item_checked()
        self.bbox.button(QW.QDialogButtonBox.Ok).setEnabled(state)

    def show_only_checkable_items(self, state: int) -> None:
        """Show only checkable items

        Args:
            state: If True, only checkable items are shown
        """
        self.browser.tree.toggle_show_only_checkable_items(state)
        fname = self.browser.selector.get_current_fname()
        if fname:
            self.browser.tree.set_current_file(fname)

    def __finalize_setup(self) -> None:
        """Finalize setup"""
        tree = self.browser.tree
        tree.toggle_show_only_checkable_items(self.checkbox_show_only.isChecked())
        tree.toggle_show_values(self.checkbox_show_values.isChecked())

    def open_file(self, fname: str) -> None:
        """Open file

        Args:
            fname: HDF5 file name
        """
        self.browser.open_file(fname)
        self.__finalize_setup()

    def open_files(self, fnames: list[str]) -> None:
        """Open files

        Args:
            fnames: HDF5 file names
        """
        for fname in fnames:
            self.browser.open_file(fname)
        self.__finalize_setup()

    def select_new_file(self, fname: str) -> None:  # pylint:disable=unused-argument
        """Select new file

        Args:
            fname: HDF5 file name
        """
        self.__finalize_setup()
        self.refresh_buttons()

    def remove_file(self, fname: str) -> None:  # pylint:disable=unused-argument
        """Remove file

        Args:
            fname: HDF5 file name
        """
        self.refresh_buttons()

    def get_all_nodes(self) -> list[BaseNode]:
        """Return all supported datasets

        Returns:
            List of HDF5 nodes
        """
        return self.browser.tree.get_nodes(only_checked_items=False)

    def get_nodes(self) -> list[BaseNode]:
        """Return datasets

        Returns:
            List of HDF5 nodes
        """
        return self.nodes

    def install_button_layout(self) -> None:
        """Install button layout"""
        bbox = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok | QW.QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)

        btn_check_all = create_toolbutton(
            self,
            icon=get_icon("check_all.svg"),
            text=_("Check all"),
            autoraise=False,
            shortcut=QG.QKeySequence.SelectAll,
            triggered=lambda checked=True: self.browser.tree.toggle_all(checked),
        )
        btn_uncheck_all = create_toolbutton(
            self,
            icon=get_icon("uncheck_all.svg"),
            text=_("Uncheck all"),
            autoraise=False,
            triggered=lambda checked=False: self.browser.tree.toggle_all(checked),
        )
        self.checkbox_show_only = QW.QCheckBox(_("Show only supported data"))
        self.checkbox_show_only.stateChanged.connect(self.show_only_checkable_items)
        self.checkbox_show_values = QW.QCheckBox(_("Show values"))
        self.checkbox_show_values.stateChanged.connect(
            self.browser.tree.toggle_show_values
        )

        self.button_layout = QW.QHBoxLayout()
        self.button_layout.addWidget(self.checkbox_show_only)
        self.button_layout.addWidget(self.checkbox_show_values)
        self.button_layout.addSpacing(10)
        self.button_layout.addWidget(btn_check_all)
        self.button_layout.addWidget(btn_uncheck_all)
        self.button_layout.addStretch()
        self.button_layout.addWidget(bbox)
        self.bbox = bbox

        vlayout: QW.QVBoxLayout = self.layout()
        vlayout.addSpacing(10)
        vlayout.addLayout(self.button_layout)
