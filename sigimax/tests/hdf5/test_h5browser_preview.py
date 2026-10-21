# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 browser preview test
-------------------------

Previews are read in a worker thread: the last selected node is shown, the
previews of nodes selected before are discarded, and closing a file waits for
the preview being read.
"""

from __future__ import annotations

import time
import uuid

import h5py
import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.items import BaseImageItem, CurveItem
from qtpy import QtWidgets as QW

from sigimax.widgets.h5browser import H5Browser

pytestmark = pytest.mark.gui


def _wait_for_item(plot, item_type: type, timeout: float = 10.0):
    """Process events until the plot shows an item of the given type."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QW.QApplication.processEvents()
        items = [item for item in plot.get_items() if isinstance(item, item_type)]
        if items:
            return items[0]
        time.sleep(0.01)
    raise TimeoutError(f"No {item_type.__name__} shown in preview")


def test_h5browser_preview(tmp_path) -> None:
    """The last selected node is previewed, decimated beyond the limit."""
    fname = str(tmp_path / f"{uuid.uuid4()}.h5")
    with h5py.File(fname, "w") as h5file:
        h5file["image"] = np.ones((300, 400), dtype=np.uint16)
        h5file["signal"] = np.arange(5000.0)
    with qt_app_context():
        browser = H5Browser()
        browser.plotpreview.MAX_ITEMS = 1000
        browser.open_file(fname)
        importer = browser.tree.h5importers[0]
        preview = browser.plotpreview
        preview.update_plot_preview(importer.get("/image"))
        preview.update_plot_preview(importer.get("/signal"))
        curve = _wait_for_item(preview.curvewidget.get_plot(), CurveItem)
        x, _y = curve.get_data()
        assert len(x) <= 1000
        QW.QApplication.processEvents()
        image_items = [
            item
            for item in preview.imagewidget.get_plot().get_items()
            if isinstance(item, BaseImageItem)
        ]
        assert not image_items, "Stale image preview must be discarded"

        preview.update_plot_preview(importer.get("/image"))
        image = _wait_for_item(preview.imagewidget.get_plot(), BaseImageItem)
        assert image.data.shape == (25, 34)

        preview.update_plot_preview(importer.get("/signal"))
        browser.close_file(fname)
        QW.QApplication.processEvents()
        browser.cleanup()
        browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
