# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Derived application with HDF5 workspace serialization test
-----------------------------------------------------------

This test demonstrates how a derived application can:

1. Connect :data:`SIG_SEND_OBJECTLIST` to populate a simple data model.
2. Override :meth:`save_h5_workspace` to serialize objects using
   :class:`guidata.io.HDF5Writer`.
3. Re-open the saved file with :class:`guidata.io.HDF5Reader` and verify
   the round-trip.

The data model is intentionally minimal — a plain list of
:class:`SignalObj` / :class:`ImageObj` — to serve as a starting point for
downstream applications.
"""

# guitest: show

from __future__ import annotations

import os.path as osp
import tempfile

import h5py
import numpy as np
import pytest
from guidata.io import HDF5Reader, HDF5Writer
from plotpy.constants import PlotType
from sigima import ImageObj, SignalObj

from sigimax.config import CONF as Conf
from sigimax.env import execenv
from sigimax.mainwindow import SGMXMainWindow
from sigimax.tests import helpers
from sigimax.utils import qthelpers as qth
from sigimax.widgets.plotdock import DockablePlotWidget

# Workspace HDF5 key used to store the application version
_VERSION_ATTR = "app_version"

# Group names inside the workspace file
_SIGNALS_GROUP = "signals"
_IMAGES_GROUP = "images"


# =============================================================================
# Minimal data model
# =============================================================================


class SimpleObjectStore:
    """Minimal object store: two ordered lists (signals + images).

    This is the simplest useful data model for a SigimaX-based application.
    Downstream projects can replace it with a richer structure (UUID-keyed
    dict, groups, etc.) without changing the serialization contract.
    """

    def __init__(self) -> None:
        self.signals: list[SignalObj] = []
        self.images: list[ImageObj] = []

    # -- Mutation ----------------------------------------------------------

    def add_objects(self, objects: list[SignalObj | ImageObj]) -> None:
        """Dispatch a list of mixed objects into the appropriate sub-list.

        Args:
            objects: list of :class:`SignalObj` and/or :class:`ImageObj`
        """
        for obj in objects:
            if isinstance(obj, SignalObj):
                self.signals.append(obj)
            elif isinstance(obj, ImageObj):
                self.images.append(obj)

    def clear(self) -> None:
        """Remove all objects."""
        self.signals.clear()
        self.images.clear()

    # -- Query -------------------------------------------------------------

    @property
    def count(self) -> int:
        """Total number of objects."""
        return len(self.signals) + len(self.images)

    # -- Serialization -----------------------------------------------------

    def serialize(self, writer: HDF5Writer) -> None:
        """Write all objects into the currently open HDF5 writer.

        Layout::

            /signals/
                000/  ← SignalObj.serialize()
                001/
            /images/
                000/  ← ImageObj.serialize()

        Args:
            writer: an open :class:`guidata.io.HDF5Writer`
        """
        with writer.group(_SIGNALS_GROUP):
            for idx, sig in enumerate(self.signals):
                with writer.group(f"{idx:03d}"):
                    sig.serialize(writer)
        with writer.group(_IMAGES_GROUP):
            for idx, ima in enumerate(self.images):
                with writer.group(f"{idx:03d}"):
                    ima.serialize(writer)

    def deserialize(self, reader: HDF5Reader) -> None:
        """Read all objects from the currently open HDF5 reader.

        Clears the store before loading.

        Args:
            reader: an open :class:`guidata.io.HDF5Reader`
        """
        self.clear()

        # Signals
        if _SIGNALS_GROUP in reader.h5:
            with reader.group(_SIGNALS_GROUP):
                idx = 0
                while True:
                    group_name = f"{idx:03d}"
                    current = reader.h5["/" + "/".join(reader.option)]
                    if group_name not in current:
                        break
                    with reader.group(group_name):
                        obj = SignalObj()
                        obj.deserialize(reader)
                        self.signals.append(obj)
                    idx += 1

        # Images
        if _IMAGES_GROUP in reader.h5:
            with reader.group(_IMAGES_GROUP):
                idx = 0
                while True:
                    group_name = f"{idx:03d}"
                    current = reader.h5["/" + "/".join(reader.option)]
                    if group_name not in current:
                        break
                    with reader.group(group_name):
                        obj = ImageObj()
                        obj.deserialize(reader)
                        self.images.append(obj)
                    idx += 1


# =============================================================================
# Derived main window
# =============================================================================


class DerivedAppWindow(SGMXMainWindow):
    """Example derived main window with a data model and workspace save/load.

    Demonstrates:
    - Connecting ``SIG_SEND_OBJECTLIST`` to populate the data model
    - Overriding ``save_h5_workspace`` using ``guidata.io.HDF5Writer``
    - A helper ``load_h5_workspace`` method using ``guidata.io.HDF5Reader``
    """

    def __init__(
        self,
        console: bool | None = None,
        hide_on_close: bool = False,
    ) -> None:
        # Configure global Conf before super().__init__()
        Conf.app_name.set("DerivedH5App")
        Conf.app_version.set("0.1.0")

        self.curve_dock = None

        super().__init__(console=console, hide_on_close=hide_on_close)

        # --- Wire the signal emitted by browse_h5_files / import_h5_file ---
        self.SIG_SEND_OBJECTLIST.connect(self._on_objects_received)

    def _setup_docks(self) -> None:
        """Add a curve dock for visual feedback."""
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.curve_dock, "Preview", name="preview")

    def _before_setup(self, console: bool) -> None:
        """Create the data model before generic setup hooks may use it."""
        super()._before_setup(console)
        self.object_store = SimpleObjectStore()

    # ------------------------------------------------------------------
    # Signal handler
    # ------------------------------------------------------------------

    def _on_objects_received(self, objects: list[SignalObj | ImageObj]) -> None:
        """Slot connected to :data:`SIG_SEND_OBJECTLIST`.

        Stores objects in the data model and updates the status bar.
        """
        self.object_store.add_objects(objects)
        execenv.print(
            f"Object store now contains {self.object_store.count} object(s) "
            f"({len(self.object_store.signals)} signals, "
            f"{len(self.object_store.images)} images)"
        )

    # ------------------------------------------------------------------
    # Workspace serialization (override)
    # ------------------------------------------------------------------

    def save_h5_workspace(self, filename: str) -> None:
        """Save workspace to HDF5 using :class:`guidata.io.HDF5Writer`.

        Overrides the base no-op to actually serialize all objects held in
        :attr:`object_store`.

        Args:
            filename: HDF5 filename to save to
        """
        filename = self._check_h5file(filename, "save")
        with HDF5Writer(filename) as writer:
            writer.h5.attrs[_VERSION_ATTR] = Conf.app_version.get()
            self.object_store.serialize(writer)
        self.set_modified(False)
        execenv.print(
            f"Workspace saved to '{filename}' ({self.object_store.count} object(s))"
        )

    def load_h5_workspace(self, filename: str) -> None:
        """Load workspace from an HDF5 file previously saved by this app.

        Args:
            filename: HDF5 filename to load from
        """
        filename = self._check_h5file(filename, "load")
        with HDF5Reader(filename) as reader:
            self.object_store.deserialize(reader)
        self.set_modified(False)
        execenv.print(
            f"Workspace loaded from '{filename}' ({self.object_store.count} object(s))"
        )

    def import_dataset_from_file(
        self,
        filename: str,
        dsetname: str | None,
        import_all: bool | None,
        reset_all: bool,
    ) -> None:
        """Import a specific dataset from a generic HDF5 file.

        Reads a raw HDF5 dataset by name and wraps it as a
        :class:`SignalObj` (1-D) or :class:`ImageObj` (2-D).

        Args:
            filename: Path to the HDF5 file (already validated)
            dsetname: Dataset name to import, or ``None`` to import all
            import_all: If ``True``, import all datasets without browsing
            reset_all: If ``True``, clear workspace before importing
        """
        if reset_all:
            self.object_store.clear()

        objects: list[SignalObj | ImageObj] = []
        with h5py.File(filename, "r") as h5:
            if dsetname is not None:
                names = [dsetname]
            else:
                names = [k for k, v in h5.items() if isinstance(v, h5py.Dataset)]
            for name in names:
                if name not in h5:
                    execenv.print(f"Dataset '{name}' not found in '{filename}'")
                    continue
                node = h5[name]
                if not isinstance(node, h5py.Dataset):
                    continue
                data = node[()]
                if data.ndim == 1:
                    obj = SignalObj()
                    obj.set_xydata(
                        np.arange(len(data), dtype=float), data.astype(float)
                    )
                    obj.title = name
                    objects.append(obj)
                elif data.ndim == 2:
                    obj = ImageObj()
                    obj.data = data
                    obj.title = name
                    objects.append(obj)

        if objects:
            self.SIG_SEND_OBJECTLIST.emit(objects)
            self.set_modified(True)
            execenv.print(f"Imported {len(objects)} dataset(s) from '{filename}'")


# =============================================================================
# Test helpers
# =============================================================================


def _create_test_signal(index: int) -> SignalObj:
    """Create a simple test signal."""
    x = np.linspace(0, 10, 200)
    y = np.sin(x * (index + 1)) + 0.05 * np.random.randn(len(x))
    obj = SignalObj()
    obj.set_xydata(x, y)
    obj.title = f"Test signal #{index}"
    return obj


def _create_test_image(index: int) -> ImageObj:
    """Create a simple test image."""
    data = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
    obj = ImageObj()
    obj.data = data
    obj.title = f"Test image #{index}"
    return obj


def _create_h5_with_datasets(path: str) -> None:
    """Create an HDF5 file with raw named datasets for dataset-import tests.

    Layout::

        /sine       (1-D float64, 200 points)
        /cosine     (1-D float64, 200 points)
        /checkerboard (2-D uint8, 64×64)
    """
    x = np.linspace(0, 2 * np.pi, 200)
    with h5py.File(path, "w") as h5:
        h5.create_dataset("sine", data=np.sin(x))
        h5.create_dataset("cosine", data=np.cos(x))
        h5.create_dataset(
            "checkerboard",
            data=np.indices((64, 64)).sum(axis=0).astype(np.uint8) % 2 * 255,
        )


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.app
def test_base_window_cannot_acknowledge_workspace_save() -> None:
    """Test that base save keeps the workspace marked as modified."""
    with qth.sigimax_app_context(exec_loop=False):
        win = SGMXMainWindow(console=False)
        win.set_modified(True)
        assert not win._is_save_enabled()  # pylint: disable=protected-access
        with pytest.raises(NotImplementedError, match="save_h5_workspace"):
            win.save_h5_workspace("workspace.h5")
        assert win.is_modified()
        win.close()


@pytest.mark.unit
def test_object_store_serialize_roundtrip() -> None:
    """Test SimpleObjectStore serialize/deserialize without GUI."""
    store = SimpleObjectStore()
    store.add_objects(
        [
            _create_test_signal(0),
            _create_test_signal(1),
            _create_test_image(0),
        ]
    )
    assert store.count == 3
    assert len(store.signals) == 2
    assert len(store.images) == 1

    with tempfile.TemporaryDirectory() as tmpdir:
        path = osp.join(tmpdir, "roundtrip_test.h5")

        # Write
        with HDF5Writer(path) as writer:
            store.serialize(writer)

        # Read into a fresh store
        store2 = SimpleObjectStore()
        with HDF5Reader(path) as reader:
            store2.deserialize(reader)

        assert store2.count == 3
        assert len(store2.signals) == 2
        assert len(store2.images) == 1

        # Verify data integrity
        np.testing.assert_array_almost_equal(
            store.signals[0].xydata, store2.signals[0].xydata
        )
        np.testing.assert_array_almost_equal(
            store.signals[1].xydata, store2.signals[1].xydata
        )
        np.testing.assert_array_equal(store.images[0].data, store2.images[0].data)

        # Verify titles
        assert store2.signals[0].title == "Test signal #0"
        assert store2.signals[1].title == "Test signal #1"
        assert store2.images[0].title == "Test image #0"

    execenv.print("Object store round-trip test passed.")


@pytest.mark.app
def test_derived_app_h5_workspace() -> None:
    """Test derived app: import → save → reload round-trip."""
    with qth.sigimax_app_context(exec_loop=False):
        win = DerivedAppWindow(console=False)
        win.resize(1200, 700)
        win.show()

        # Populate the data model via the signal
        test_objects = [
            _create_test_signal(0),
            _create_test_signal(1),
            _create_test_signal(2),
            _create_test_image(0),
            _create_test_image(1),
        ]
        win.SIG_SEND_OBJECTLIST.emit(test_objects)

        assert win.object_store.count == 5
        assert len(win.object_store.signals) == 3
        assert len(win.object_store.images) == 2

        with tempfile.TemporaryDirectory() as tmpdir:
            path = osp.join(tmpdir, "workspace_test.h5")

            # Save via the overridden method (goes through save_to_h5_file flow)
            win.save_h5_workspace(path)
            assert osp.isfile(path)
            assert not win.is_modified()

            # Create a second window and load the workspace
            win2 = DerivedAppWindow(console=False)
            win2.resize(1200, 700)
            win2.show()

            assert win2.object_store.count == 0
            win2.load_h5_workspace(path)

            assert win2.object_store.count == 5
            assert len(win2.object_store.signals) == 3
            assert len(win2.object_store.images) == 2

            # Verify data
            np.testing.assert_array_almost_equal(
                win.object_store.signals[0].xydata,
                win2.object_store.signals[0].xydata,
            )
            np.testing.assert_array_equal(
                win.object_store.images[0].data,
                win2.object_store.images[0].data,
            )

            # Verify titles survived the round-trip
            for i in range(3):
                assert win2.object_store.signals[i].title == f"Test signal #{i}", (
                    f"Signal title mismatch at index {i}"
                )
            for i in range(2):
                assert win2.object_store.images[i].title == f"Test image #{i}", (
                    f"Image title mismatch at index {i}"
                )

            win2.set_modified(False)
            win2.close()

        win.set_modified(False)
        win.close()

    execenv.print("Derived app workspace round-trip test passed.")


@pytest.mark.app
def test_derived_app_import_and_save() -> None:
    """Test importing an HDF5 file and saving the workspace."""
    fnames = helpers.get_test_fnames("*.h5")
    if not fnames:
        execenv.print("No test HDF5 files found, skipping test.")
        return

    fname = fnames[-1]
    with qth.sigimax_app_context(exec_loop=False):
        win = DerivedAppWindow(console=False)
        win.resize(1200, 700)
        win.show()

        # Import objects from a real HDF5 file
        execenv.print(f"Importing HDF5 file: {fname}")
        win.import_h5_file(fname)

        initial_count = win.object_store.count
        execenv.print(f"Imported {initial_count} object(s)")

        if initial_count > 0:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = osp.join(tmpdir, "import_save_test.h5")
                win.save_h5_workspace(path)
                assert osp.isfile(path)

                # Reload and verify count matches
                win2 = DerivedAppWindow(console=False)
                win2.show()
                win2.load_h5_workspace(path)
                assert win2.object_store.count == initial_count
                win2.set_modified(False)
                win2.close()

        win.set_modified(False)
        win.close()

    execenv.print("Import-and-save test passed.")


@pytest.mark.app
def test_import_specific_dataset_and_save() -> None:
    """Test importing a specific dataset by name and save/load round-trip.

    Exercises :meth:`DerivedAppWindow.import_dataset_from_file` via the
    ``open_h5_files`` comma-separated syntax (``"file.h5,dataset_name"``).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # -- Create an HDF5 file with raw named datasets --
        src_path = osp.join(tmpdir, "raw_datasets.h5")
        _create_h5_with_datasets(src_path)

        with qth.sigimax_app_context(exec_loop=False):
            win = DerivedAppWindow(console=False)
            win.resize(1200, 700)
            win.show()

            # -- 1. Import a single dataset by name --
            win.open_h5_files(
                h5files=[f"{src_path},sine"],
                import_all=False,
                reset_all=False,
            )
            assert win.object_store.count == 1, (
                f"Expected 1 object, got {win.object_store.count}"
            )
            assert len(win.object_store.signals) == 1
            assert win.object_store.signals[0].title == "sine"

            # -- 2. Import another dataset (no reset) --
            win.open_h5_files(
                h5files=[f"{src_path},checkerboard"],
                import_all=False,
                reset_all=False,
            )
            assert win.object_store.count == 2
            assert len(win.object_store.images) == 1
            assert win.object_store.images[0].title == "checkerboard"

            # The historical ``filename,dataset`` contract rejects any extra
            # comma rather than silently changing how the selector is parsed.
            with pytest.raises(ValueError):
                win.open_h5_files(
                    h5files=[f"{src_path},sine,extra"],
                    import_all=False,
                    reset_all=False,
                )

            # -- 3. Import all datasets at once (with reset) --
            win.open_h5_files(
                h5files=[src_path],
                import_all=True,
                reset_all=True,
            )
            # import_all=True triggers import_dataset_from_file with dsetname=None
            assert win.object_store.count == 3, (
                f"Expected 3 objects, got {win.object_store.count}"
            )
            assert len(win.object_store.signals) == 2  # sine + cosine
            assert len(win.object_store.images) == 1  # checkerboard

            # -- 4. Save workspace and reload --
            ws_path = osp.join(tmpdir, "workspace_specific.h5")
            win.save_h5_workspace(ws_path)
            assert osp.isfile(ws_path)

            win2 = DerivedAppWindow(console=False)
            win2.resize(1200, 700)
            win2.show()

            win2.load_h5_workspace(ws_path)
            assert win2.object_store.count == 3
            assert len(win2.object_store.signals) == 2
            assert len(win2.object_store.images) == 1

            # Verify data integrity for the sine signal
            np.testing.assert_array_almost_equal(
                win.object_store.signals[0].y,
                win2.object_store.signals[0].y,
            )
            # Verify image data integrity
            np.testing.assert_array_equal(
                win.object_store.images[0].data,
                win2.object_store.images[0].data,
            )

            win2.set_modified(False)
            win2.close()
            win.set_modified(False)
            win.close()

    execenv.print("Import-specific-dataset and save/load test passed.")


def show_derivated_app() -> None:
    """Show the derived application window."""
    with qth.sigimax_app_context(exec_loop=True):
        win = DerivedAppWindow(console=False)
        win.show()


if __name__ == "__main__":
    test_object_store_serialize_roundtrip()
    test_derived_app_h5_workspace()
    test_derived_app_import_and_save()
    test_import_specific_dataset_and_save()
    # show_derivated_app()
