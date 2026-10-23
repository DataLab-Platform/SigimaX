# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 browser preview test
-------------------------

Previews are read in a worker thread: the last selected node is shown, the
previews of nodes selected before are discarded without being read, and closing
a file or the browser dialog waits for the preview being read.
"""

from __future__ import annotations

import threading
import time
import uuid

import h5py
import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from plotpy.items import BaseImageItem, CurveItem
from qtpy import QtWidgets as QW
from sigima.objects import create_signal

from sigimax.widgets.h5browser import H5Browser, H5BrowserDialog, PlotPreview

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


class _SpyNode:
    """Node whose preview is read when the test releases it."""

    def __init__(self, release: threading.Event) -> None:
        self.release = release
        self.started = threading.Event()
        self.reads = 0
        self.done = False

    def create_preview_object(self, max_items: int):  # pylint: disable=unused-argument
        """Return a small signal, once released."""
        self.reads += 1
        self.started.set()
        assert self.release.wait(10.0)
        self.done = True
        return create_signal("Spy", np.arange(3.0), np.arange(3.0))


def _wait_until(condition, timeout: float = 10.0) -> None:
    """Process events until condition is true."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError("Condition not met")
        QW.QApplication.processEvents()
        time.sleep(0.01)


def test_stale_previews_are_not_read() -> None:
    """Nodes selected while a preview is read are skipped: only the last one is
    read after it, and the worker thread is stopped on cleanup."""
    with qt_app_context():
        preview = PlotPreview(None)
        threads = set(threading.enumerate())
        release = threading.Event()
        nodes = [_SpyNode(release) for _index in range(5)]
        for node in nodes:
            preview.update_plot_preview(node)
        assert nodes[0].started.wait(10.0)
        workers = set(threading.enumerate()) - threads
        release.set()
        _wait_until(lambda: nodes[-1].done)
        assert [node.reads for node in nodes] == [1, 0, 0, 0, 1]
        preview.cleanup()
        assert not any(thread.is_alive() for thread in workers)
        # The preview may be used again after cleanup
        node = _SpyNode(release)
        preview.update_plot_preview(node)
        _wait_until(lambda: node.done)
        preview.cleanup()
        preview.close()


@pytest.mark.parametrize("method", ["accept", "reject"])
def test_dialog_waits_for_preview(method: str) -> None:
    """Closing the dialog waits for the preview being read, so that the caller
    does not read the file concurrently."""
    with qt_app_context():
        dialog = H5BrowserDialog(None)
        release = threading.Event()
        node = _SpyNode(release)
        dialog.browser.plotpreview.update_plot_preview(node)
        assert node.started.wait(10.0)
        timer = threading.Timer(0.2, release.set)
        timer.start()
        getattr(dialog, method)()
        assert node.done
        timer.join()
        dialog.cleanup()
        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
