HDF5 Workspace
==============

SigimaX provides the HDF5 user interface and generic dataset import. A derived
application owns its workspace model and its workspace file format. SigimaX
does not define a universal workspace schema.

Responsibilities
----------------

SigimaX provides:

- File, Open/Import, Browse, and Save actions;
- the HDF5 browser and :class:`sigimax.h5.H5Importer` for arbitrary datasets;
- :meth:`sigimax.mainwindow.SGMXMainWindow.set_modified`, the save prompt, and
  the close workflow;
- protected HDF5 hooks for derived applications.

A derived application provides:

- its data model;
- workspace serialization and deserialization;
- the mutation points that mark the workspace modified;
- optional application-specific dataset import.

A base :class:`~sigimax.mainwindow.SGMXMainWindow` has no data model. Its Save
action remains disabled and a direct call to ``save_h5_workspace`` raises
:class:`NotImplementedError`. This prevents a successful-looking save from
silently discarding a modified workspace.

Minimal Derived Application
---------------------------

The SigimaX test suite contains an executable reference application. It is both
an integration test and a complete minimal example: it stores signals and
images, imports generic HDF5 datasets, and writes a small workspace format.

Its data model deliberately remains application code. It uses two collections
and knows how to serialize them with ``guidata``:

.. literalinclude:: ../../sigimax/tests/hdf5/test_h5_derived_app.py
   :language: python
   :pyobject: SimpleObjectStore

The derived window validates paths through the protected hook, writes its model,
and only clears the modified flag after a successful write:

.. literalinclude:: ../../sigimax/tests/hdf5/test_h5_derived_app.py
   :language: python
   :pyobject: DerivedAppWindow.save_h5_workspace

The matching loader is equally application-specific:

.. literalinclude:: ../../sigimax/tests/hdf5/test_h5_derived_app.py
   :language: python
   :pyobject: DerivedAppWindow.load_h5_workspace

Workspace State and Save
------------------------

Call ``set_modified(True)`` whenever an application mutation changes the
workspace. The framework adds an asterisk to the window title, enables Save for
windows that implement ``save_h5_workspace``, and asks for confirmation when
the user closes a modified window.

A successful ``save_h5_workspace`` implementation must call
``set_modified(False)`` only after its writer closes without an exception. An
exception or a cancelled save leaves the workspace modified, so the close flow
remains safe.

Generic Dataset Import
----------------------

``open_h5_files`` and :class:`~sigimax.widgets.h5browser.H5BrowserDialog` are
for importing arbitrary HDF5 datasets. They are independent from an
application's workspace loader. The reference application connects
``SIG_SEND_OBJECTLIST`` to its model and implements
``import_dataset_from_file`` for programmatic selection of a dataset.

The generic import layer can create :class:`sigima.objects.SignalObj` and
:class:`sigima.objects.ImageObj`; a derived application decides how these
objects enter its own model.

NeXus Scientific Objects
------------------------

With Sigima 1.4 or later, an ``NXdata`` group is importable as a 1D signal or
2D image with its physical axes, labels and units. Modern group attributes
(``signal``, ``axes`` and ``<axis>_indices``) and legacy dataset attributes
(``signal=1`` and ``axes``) are supported. Selecting a group imports the
scientific object; selecting a child dataset still gives access to raw values.

Axis datasets must be 1D, hold real numbers and contain either one coordinate
per point or one extra value for bin edges. Edges are converted to centers.
Image coordinates may be non-uniform; a decreasing image axis is reversed,
with the image, and this conversion is recorded, while an image axis that is
not strictly monotonic prevents import. The ``axes`` attribute must give one
entry per signal dimension, and ``<axis>_indices`` attributes must designate
distinct existing dimensions. Invalid declared axes are reported and prevent
group import; undeclared axes use indices. Signal Y uncertainties are read from
``<signal>_errors`` or ``errors`` when they hold real numbers and their shape
matches; image uncertainties are not imported.

Imported objects record their file, group, signal, axes and conversions in
``experimental_source`` metadata; a dimension without axis is recorded as
``"."``, as in NeXus ``axes`` attributes. This describes the measurement
origin, not a reproducible acquisition or a processing history. The
application must preserve object metadata in its own workspace serialization.

Declarative Data Mappings
-------------------------

For files without suitable ``NXdata`` descriptions, register a mapping before
opening the file. A mapping matches groups by attribute values and required
paths, then describes the signals or images they contain. Save the following
JSON as ``counters.json``:

.. code-block:: json

    {
        "version": 1,
        "name": "Counters",
        "match": {
            "attributes": {"NX_class": "NXentry"},
            "paths": ["time"]
        },
        "objects": [
            {
                "name": "{name}",
                "signal": "counts_*",
                "axes": [{"path": "time", "label": "Elapsed time", "units": "s"}],
                "label": "Counts",
                "units": "counts"
            }
        ]
    }

Paths are relative to each matching group. Only the last component of
``signal`` may contain a pattern (``*``, ``?`` or ``[...]``); ``{name}`` is
then required in the object name and is replaced by each dataset name.
Uncertainty datasets ending in ``_errors`` and declared axes are excluded
from pattern expansion.

``axes`` contains one entry per signal dimension, in array order (rows then
columns for an image). Each entry is a path, an object with ``path`` and optional
``label`` and ``units``, or ``null`` to use indices. Omitting ``axes`` uses
indices for every dimension. The optional ``errors`` path overrides the
default ``<signal>_errors`` dataset. Labels and units otherwise come from
``long_name`` and ``units`` attributes, with the dataset name as label fallback.
An explicitly requested uncertainty dataset that does not hold real numbers or
has the wrong shape prevents importing that mapped object.

This runnable example uses the JSON file above and creates a small input file:

.. code-block:: python

    from pathlib import Path
    from tempfile import TemporaryDirectory

    import h5py
    import numpy as np

    from sigimax.h5 import H5Importer
    from sigimax.h5.mapping import load_mapping, register_mapping, unregister_mapping

    mapping = load_mapping("counters.json")
    with TemporaryDirectory() as directory:
        filename = Path(directory) / "scan.h5"
        with h5py.File(filename, "w") as h5file:
            entry = h5file.create_group("entry")
            entry.attrs["NX_class"] = "NXentry"
            entry["time"] = [0.0, 0.5, 1.0]
            entry["counts_1"] = [10.0, 20.0, 30.0]
            entry["counts_1_errors"] = [1.0, 2.0, 3.0]
        register_mapping(mapping)
        try:
            importer = H5Importer(str(filename))
            try:
                node = importer.get("/entry::Counters/counts_1")
                signal = node.get_native_object()
                np.testing.assert_array_equal(signal.x, [0.0, 0.5, 1.0])
                np.testing.assert_array_equal(signal.dy, [1.0, 2.0, 3.0])
                assert signal.xunit == "s"
                assert signal.metadata["experimental_source"]["details"] == {
                    "mapping": "Counters"
                }
            finally:
                importer.close()
        finally:
            unregister_mapping(mapping.name)

The registry is process-wide; JSON files are not discovered automatically.
A plugin should register its mappings when loaded and unregister them when
unloaded. Re-registering an identical mapping is harmless; a different mapping
with the same name raises ``ValueError``. Existing open files are not rebuilt
when the registry changes. Mapped objects appear as extra browser nodes, leaving
raw datasets accessible, and record the mapping name in their experimental source.

Large Files and Multidimensional Views
--------------------------------------

Dataset classification uses shape and type metadata; mixed compound datasets
are checked on their first records. Text previews are bounded to 100 elements,
and attributes above 10 000 elements are skipped. Graphical previews are read
in a worker thread; previews of items selected meanwhile are not read, and
stale results are not displayed. Closing a file or the browser dialog waits
for the preview read to finish.

Ordinary 1D arrays and 2D images, NeXus and mapped objects exceeding ``2**24``
elements are previewed with a sampling step along each axis. The full data is
still read on import. Compound datasets and signals stored in 2D tables still
use complete objects for graphical previews, so this is not a universal memory
bound.

Numeric datasets with three or more dimensions are listed but not imported as
complete objects. There is no graphical slice selector. Use
:class:`sigimax.h5.selection.NDSelection` and
:func:`sigimax.h5.selection.read_selection` to read only a selected 1D or 2D
view as a NumPy array:

.. code-block:: python

    from pathlib import Path
    from tempfile import TemporaryDirectory

    import h5py
    import numpy as np

    from sigimax.h5.selection import NDSelection, read_selection

    cube = np.arange(5 * 3 * 4).reshape(5, 3, 4)
    with TemporaryDirectory() as directory:
        filename = Path(directory) / "cube.h5"
        with h5py.File(filename, "w") as h5file:
            h5file["frames"] = cube
        with h5py.File(filename, "r") as h5file:
            dataset = h5file["frames"]
            frame = read_selection(dataset, NDSelection((1, 2), (2,)))
            spectrum = read_selection(dataset, NDSelection((0,), (1, 3)))
            transposed = read_selection(dataset, NDSelection((2, 1), (2,)))
            np.testing.assert_array_equal(frame, cube[2])
            np.testing.assert_array_equal(spectrum, cube[:, 1, 3])
            np.testing.assert_array_equal(transposed, cube[2].T)

``displayed`` gives the axes in output order; ``indices`` fixes the other axes
in their original order. An optional positive ``step`` samples displayed axes.
Invalid axes or indices raise ``ValueError``. This low-level API returns arrays,
not calibrated Sigima objects, and does not attach experimental-source metadata.

DataLab
-------

DataLab keeps its native workspace format, panel serialization, metadata, ROI,
and analysis-result handling. Its ``save_h5_workspace`` override remains the
owner of that format. The SigimaX HDF5 GUI and generic import infrastructure do
not change DataLab's native HDF5 layout.
