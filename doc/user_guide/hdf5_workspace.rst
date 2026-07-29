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

DataLab
-------

DataLab keeps its native workspace format, panel serialization, metadata, ROI,
and analysis-result handling. Its ``save_h5_workspace`` override remains the
owner of that format. The SigimaX HDF5 GUI and generic import infrastructure do
not change DataLab's native HDF5 layout.
