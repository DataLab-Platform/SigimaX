# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 browser view selector test
-------------------------------

The default NXdata group of a NeXus file is selected when the file is opened.
Multidimensional datasets are shown with a view selector: their frames are
previewed, and imported once enabled, which makes their item checkable; the
item expands into one node per frame when importing.
"""

from __future__ import annotations

import uuid

import h5py
import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from sigimax.h5.views import FrameNode
from sigimax.widgets.h5browser import H5BrowserDialog

pytestmark = pytest.mark.gui


def _write_file(fname: str) -> None:
    """Write a NeXus file with a default 1D NXdata group and an image stack"""
    with h5py.File(fname, "w") as h5file:
        h5file.attrs["default"] = "entry"
        entry = h5file.create_group("entry")
        entry.attrs.update(NX_class="NXentry", default="data")
        data = entry.create_group("data")
        data.attrs.update(NX_class="NXdata", signal="y")
        data["y"] = np.arange(5.0)
        stack = entry.create_group("stack")
        stack.attrs.update(NX_class="NXdata", signal="frames")
        stack.attrs["axes"] = np.array([b"theta", b".", b"."])
        stack["frames"] = np.arange(4 * 3 * 2, dtype=np.uint16).reshape(4, 3, 2)
        stack["theta"] = np.array([0.0, 0.1, 0.2, 0.3])


def test_view_selector(tmp_path) -> None:
    """Frames of a stack are imported once enabled in the view selector."""
    fname = str(tmp_path / f"{uuid.uuid4()}.nxs")
    _write_file(fname)
    with qt_app_context():
        dialog = H5BrowserDialog()
        try:
            dialog.open_file(fname)
            browser, tree = dialog.browser, dialog.browser.tree
            assert tree.currentItem().data(0, QC.Qt.UserRole) == "/entry/data"
            selector = browser.viewselector
            assert selector.node is None
            item = tree.find_node_item(tree.topLevelItem(0), "/entry/stack")
            assert not item.flags() & QC.Qt.ItemIsUserCheckable
            tree.clicked(item)
            node = selector.node
            assert node is tree.get_node(item) and not selector.isHidden()
            assert node.frame_count() == 4
            selector.last_spin.setValue(1)
            assert node.frame_count() == 2 and not node.import_view
            selector.import_check.setChecked(True)
            assert item.checkState(0) == QC.Qt.Checked and node.import_view
            frames = tree.get_nodes()
            assert [type(frame) for frame in frames] == [FrameNode, FrameNode]
            assert [frame.name for frame in frames] == [
                "stack[0, :, :]",
                "stack[1, :, :]",
            ]
            # Signals along the first axis: views are images of pairs of axes,
            # then signals along each axis
            selector.view_combo.setCurrentIndex(3)
            assert node.view.displayed == (0,) and node.frame_count() == 3
            assert dialog.bbox.button(QW.QDialogButtonBox.Ok).isEnabled()
            item.setCheckState(0, QC.Qt.Unchecked)
            assert not node.import_view and not selector.import_check.isChecked()
            assert not item.flags() & QC.Qt.ItemIsUserCheckable
            assert not tree.get_nodes()
            data_item = tree.find_node_item(tree.topLevelItem(0), "/entry/data")
            tree.clicked(data_item)
            assert selector.node is None and selector.isHidden()
        finally:
            dialog.browser.plotpreview.wait()
            dialog.cleanup()
            dialog.close()
