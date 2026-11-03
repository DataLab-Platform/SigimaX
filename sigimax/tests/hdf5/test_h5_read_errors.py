# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 read error tests
---------------------

Datasets that cannot be read (truncated or corrupted file, missing external data
file...) are reported with their path when their object is created or previewed,
instead of being skipped silently or reported with an unrelated error. Files
containing such datasets can still be browsed, and the other datasets are imported
before the errors are reported.
"""

from __future__ import annotations

import os

import h5py
import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from sigimax.h5 import H5Importer
from sigimax.h5.selection import NDSelection, read_selection
from sigimax.tests import sigimax_test_app_context
from sigimax.widgets import h5browser
from sigimax.widgets.h5browser import H5Browser, H5TreeWidget

pytestmark = pytest.mark.unit

#: Datasets that cannot be read, by path
BROKEN = ("/sig_ext", "/img_ext", "/cube_ext", "/sig_gz", "/img_gz")


@pytest.fixture(name="h5fname")
def fixture_h5fname(tmp_path) -> str:
    """HDF5 file with datasets that cannot be read, and a readable signal.

    The data of the ``*_ext`` datasets is stored in external files, which are
    removed. The last chunk of the ``*_gz`` compressed datasets is overwritten, so
    that their first elements can still be read.
    """
    fname = str(tmp_path / "broken.h5")
    shapes = {"sig_ext": (100,), "img_ext": (20, 30), "cube_ext": (3, 20, 30)}
    with h5py.File(fname, "w") as h5file:
        h5file["good"] = np.arange(10.0)
        for name, shape in shapes.items():
            raw = str(tmp_path / f"{name}.bin")
            np.zeros(shape).tofile(raw)
            h5file.create_dataset(
                name, shape=shape, dtype="f8", external=[(raw, 0, h5py.h5f.UNLIMITED)]
            )
        rng = np.random.default_rng(0)
        for name, shape in (("sig_gz", (5000,)), ("img_gz", (200, 300))):
            h5file.create_dataset(
                name, data=rng.random(shape), chunks=True, compression="gzip"
            )
    for name in shapes:
        os.remove(str(tmp_path / f"{name}.bin"))
    chunks = []
    with h5py.File(fname, "r") as h5file:
        for name in ("sig_gz", "img_gz"):
            dsid = h5file[name].id
            info = dsid.get_chunk_info(dsid.get_num_chunks() - 1)
            chunks.append((info.byte_offset, info.size))
    with open(fname, "r+b") as fobj:
        for offset, size in chunks:
            fobj.seek(offset)
            fobj.write(b"\xff" * size)
    return fname


def _message(path: str) -> str:
    """Return the beginning of the error message of a dataset (regex)"""
    return f"Unable to read dataset '{path}' \\(broken.h5\\)"


def test_unreadable_datasets_are_reported(h5fname: str) -> None:
    """Creating or previewing the object of a dataset that cannot be read raises an
    error naming the dataset, every time (nothing is cached)."""
    importer = H5Importer(h5fname)
    try:
        nodes = {node.id: node for node in importer.nodes}
        for path in ("/sig_ext", "/img_ext", "/sig_gz", "/img_gz"):
            node = nodes[path]
            assert node.is_supported(), path
            for _attempt in range(2):
                with pytest.raises(OSError, match=_message(path)):
                    node.get_native_object()
            with pytest.raises(OSError, match=_message(path)):
                node.create_preview_object(1000)
        cube = nodes["/cube_ext"]
        selection = NDSelection((1, 2), (0,))
        with pytest.raises(OSError, match=_message("/cube_ext")):
            read_selection(cube.dset, selection)
        with pytest.raises(OSError, match=_message("/cube_ext")):
            cube.create_view_object(selection, "frame")
        assert nodes["/good"].get_native_object().y.size == 10
    finally:
        importer.close()


def test_unreadable_datasets_are_described(h5fname: str) -> None:
    """Textual previews of datasets that cannot be read do not raise errors."""
    importer = H5Importer(h5fname)
    try:
        nodes = {node.id: node for node in importer.nodes}
        for path in ("/sig_ext", "/img_ext", "/cube_ext"):
            assert nodes[path].text == "<unreadable data>"
        # The first elements of the corrupted compressed datasets can be read
        for path in ("/sig_gz", "/img_gz"):
            assert nodes[path].text.endswith(" ...")
    finally:
        importer.close()


def _tree_item(browser: H5Browser, node_id: str) -> QW.QTreeWidgetItem:
    """Return the tree item of a node"""
    item = browser.tree.find_node_item(browser.tree.topLevelItem(0), node_id)
    assert item is not None, node_id
    return item


def _process_events_until(condition, timeout: float = 10.0) -> None:
    """Process events until condition is true"""
    timer = QC.QElapsedTimer()
    timer.start()
    while not condition():
        if timer.elapsed() > timeout * 1000:
            raise TimeoutError("Condition not met")
        QW.QApplication.processEvents()
        QC.QThread.msleep(10)


@pytest.mark.gui
def test_browser_reports_read_errors(h5fname: str, monkeypatch) -> None:
    """The browser opens files with datasets that cannot be read, and reports the
    read errors of their preview and of "Show array"."""
    reported: list[Exception] = []
    monkeypatch.setattr(
        h5browser, "qt_handle_error_message", lambda _w, exc: reported.append(exc)
    )
    with qt_app_context():
        browser = H5Browser()
        browser.open_file(h5fname)
        for path in BROKEN:
            _tree_item(browser, path)
        item = _tree_item(browser, "/sig_ext")
        browser.tree.setCurrentItem(item)
        browser.tree.clicked(item)
        _process_events_until(lambda: reported)
        assert str(reported[-1]).startswith("Unable to read dataset '/sig_ext'")
        reported.clear()
        browser.show_array()
        assert len(reported) == 1
        assert str(reported[0]).startswith("Unable to read dataset '/sig_ext'")
        browser.cleanup()
        browser.close()


@pytest.mark.gui
def test_failed_file_opening_is_undone(h5fname: str, monkeypatch) -> None:
    """When the tree of a file cannot be built, its partial tree is removed and the
    file is closed, so that the other files are still browsed."""
    importers: list[H5Importer] = []
    original = H5TreeWidget.add_root_to_tree

    def failing(tree: H5TreeWidget, importer: H5Importer) -> None:
        importers.append(importer)
        original(tree, importer)
        raise RuntimeError("Tree cannot be built")

    with qt_app_context():
        browser = H5Browser()
        monkeypatch.setattr(H5TreeWidget, "add_root_to_tree", failing)
        with pytest.raises(RuntimeError, match="Tree cannot be built"):
            browser.open_file(h5fname)
        assert browser.tree.topLevelItemCount() == 0
        assert not browser.tree.fnames and not browser.tree.h5importers
        assert not importers[0].h5file.id.valid
        monkeypatch.setattr(H5TreeWidget, "add_root_to_tree", original)
        browser.open_file(h5fname)
        assert browser.tree.get_node(_tree_item(browser, "/good")).id == "/good"
        browser.cleanup()
        browser.close()


@pytest.mark.app
@pytest.mark.parametrize("browse", [False, True])
def test_import_reports_read_errors(h5fname: str, monkeypatch, browse: bool) -> None:
    """The readable datasets are imported, then the datasets that cannot be read
    are reported at once."""

    def accept_all(dialog: h5browser.H5BrowserDialog) -> int:
        dialog.browser.tree.toggle_all(True)
        dialog.accept()
        return QW.QDialog.Accepted

    monkeypatch.setattr("sigimax.mainwindow.exec_dialog", accept_all)
    received: list = []
    with sigimax_test_app_context(console=False, exec_loop=False) as win:
        win.SIG_SEND_OBJECTLIST.connect(received.extend)
        with pytest.raises(ValueError) as excinfo:
            if browse:
                win.browse_h5_files([h5fname])
            else:
                win.import_all_from_h5_file(h5fname)
        lines = str(excinfo.value).splitlines()
        assert [line.split(":")[0] for line in lines] == sorted(
            path for path in BROKEN if path != "/cube_ext"
        )
        assert all("Unable to read dataset" in line for line in lines)
        assert len(received) == 1 and received[0].y.size == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
