# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 Workspace Save/Load
=========================

SigimaX provides the plumbing for an HDF5-backed workspace (menu actions,
file dialogs, browser) but does **not** know what a derived application's
data model looks like. This example shows how to plug your own model in by
overriding three extension points on :class:`~sigimax.mainwindow.SGMXMainWindow`:

- :meth:`~sigimax.mainwindow.SGMXMainWindow.save_h5_workspace` — serialize your
  objects when the user chooses *File > Save*
- ``load_h5_workspace`` (a convention, not a base-class method) — the
  counterpart used to reload a workspace saved by your own application
- :meth:`~sigimax.mainwindow.SGMXMainWindow.import_dataset_from_file` — import
  data coming from a *generic* (non-SigimaX) HDF5 file, as offered by
  *File > Browse HDF5 file*

See :doc:`../../user_guide/hdf5_workspace` for the full reference and
``sigimax/tests/hdf5/test_h5_derived_app.py`` for the complete test this
example is derived from.
"""

# %%
# Importing necessary modules
# ---------------------------

import os.path as osp
import tempfile

import numpy as np
from guidata.io import HDF5Reader, HDF5Writer
from sigima import ImageObj, SignalObj

from sigimax.config import CONF as Conf
from sigimax.env import execenv
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth

# %%
# Step 1: A minimal data model
# ------------------------------
#
# Any object store works, as long as it can serialize/deserialize itself
# using :class:`guidata.io.HDF5Writer`/:class:`guidata.io.HDF5Reader`. Here we
# use a plain list of :class:`~sigima.objects.SignalObj`/
# :class:`~sigima.objects.ImageObj`, grouped under two HDF5 groups.


class SimpleObjectStore:
    """Minimal object store: two ordered lists (signals + images)."""

    def __init__(self) -> None:
        self.signals: list[SignalObj] = []
        self.images: list[ImageObj] = []

    def add_objects(self, objects: list[SignalObj | ImageObj]) -> None:
        for obj in objects:
            if isinstance(obj, SignalObj):
                self.signals.append(obj)
            elif isinstance(obj, ImageObj):
                self.images.append(obj)

    @property
    def count(self) -> int:
        return len(self.signals) + len(self.images)

    def serialize(self, writer: HDF5Writer) -> None:
        with writer.group("signals"):
            for idx, sig in enumerate(self.signals):
                with writer.group(f"{idx:03d}"):
                    sig.serialize(writer)
        with writer.group("images"):
            for idx, ima in enumerate(self.images):
                with writer.group(f"{idx:03d}"):
                    ima.serialize(writer)

    def deserialize(self, reader: HDF5Reader) -> None:
        self.signals.clear()
        self.images.clear()
        if "signals" in reader.h5:
            with reader.group("signals"):
                for idx in range(len(reader.h5["signals"])):
                    with reader.group(f"{idx:03d}"):
                        obj = SignalObj()
                        obj.deserialize(reader)
                        self.signals.append(obj)
        if "images" in reader.h5:
            with reader.group("images"):
                for idx in range(len(reader.h5["images"])):
                    with reader.group(f"{idx:03d}"):
                        obj = ImageObj()
                        obj.deserialize(reader)
                        self.images.append(obj)


# %%
# Step 2: Override the workspace save/load hooks
# -------------------------------------------------
#
# ``save_h5_workspace`` is the only method the base class calls (from *File >
# Save*, wired to :meth:`~sigimax.mainwindow.SGMXMainWindow.save_to_h5_file`).
# ``load_h5_workspace`` is a symmetrical helper of our own — SigimaX does not
# impose a name or signature for "load one of *our own* workspace files"
# since it depends entirely on the data model.


class MyAppWindow(SGMXMainWindow):
    """Derived application window with a custom HDF5 workspace."""

    def __init__(self, console: bool | None = None) -> None:
        Conf.app_name.set("MyH5App")
        super().__init__(console=console)

    def _before_setup(self, console: bool) -> None:
        super()._before_setup(console)
        self.object_store = SimpleObjectStore()

    def save_h5_workspace(self, filename: str) -> None:
        filename = self._check_h5file(filename, "save")
        with HDF5Writer(filename) as writer:
            self.object_store.serialize(writer)
        self.set_modified(False)
        execenv.print(f"Workspace saved to '{filename}'")

    def load_h5_workspace(self, filename: str) -> None:
        filename = self._check_h5file(filename, "load")
        with HDF5Reader(filename) as reader:
            self.object_store.deserialize(reader)
        self.set_modified(False)
        execenv.print(f"Workspace loaded from '{filename}'")


# %%
# Step 3: Round-trip
# --------------------
#
# ``save_to_h5_file(path)``/``save_h5_workspace(path)`` and
# ``load_h5_workspace(path)`` accept an explicit path, so they never open a
# file dialog — this is what makes them usable both interactively (*File*
# menu) and headlessly (macros, tests, this example).

with qth.sigimax_app_context(exec_loop=False):
    win = MyAppWindow(console=False)

    signal = SignalObj()
    signal.set_xydata(np.linspace(0, 10, 100), np.sin(np.linspace(0, 10, 100)))
    signal.title = "Demo signal"
    win.object_store.add_objects([signal])

    with tempfile.TemporaryDirectory() as tmpdir:
        path = osp.join(tmpdir, "workspace.h5")

        win.save_h5_workspace(path)
        print(f"Saved {win.object_store.count} object(s) to {path}")

        reloaded = MyAppWindow(console=False)
        reloaded.load_h5_workspace(path)
        print(f"Reloaded {reloaded.object_store.count} object(s)")

    win.close()

# %%
# Summary
# -------
#
# - :meth:`~sigimax.mainwindow.SGMXMainWindow.save_h5_workspace` is the single
#   contract point SigimaX relies on for *File > Save* — the base
#   implementation is a documented no-op, override it in your window class
# - Add a symmetrical ``load_*`` method for reopening your own files; there is
#   no base-class hook to override because the data model is entirely
#   downstream
# - Override :meth:`~sigimax.mainwindow.SGMXMainWindow.import_dataset_from_file`
#   to support importing *generic* (non-SigimaX) HDF5 files through
#   *File > Browse HDF5 file*
# - To add a new node type recognized by the generic HDF5 browser itself
#   (rather than importing raw datasets), subclass
#   :class:`~sigimax.h5.common.BaseNode` and register it with
#   ``sigimax.h5.common.NODE_FACTORY.register(MyNode)``
