.. _api:

API
===

The public Application Programming Interface (API) of SigimaX provides
the building blocks for creating scientific desktop applications.

.. list-table::
    :header-rows: 1
    :align: left

    * - Module
      - Purpose

    * - :mod:`sigimax.app`
      - Application launcher — ``create()`` and ``run()`` entry points for
        starting a SigimaX-based application with splash screen support.

    * - :mod:`sigimax.config`
      - Configuration system — ``SigimaXOptions`` singleton (``CONF``),
        typed option fields (``EnumOptionField``, ``TupleOptionField``,
        ``FontOptionField``), and translation function ``_()``.

    * - :mod:`sigimax.env`
      - Runtime environment — ``SGMXExecEnv`` singleton (``execenv``) for
        controlling unattended mode, verbosity, demo mode, and screenshots.

    * - :mod:`sigimax.mainwindow`
      - Generic main window — ``SGMXMainWindow`` with customizable menus,
        toolbars, console, HDF5 workspace, and status bar.

    * - :mod:`sigimax.widgets`
      - Reusable Qt widgets — scientific dialogs (fitting, peak detection,
        baseline, cursor, delta-X), HDF5 browser, log viewer, wizard,
        splash screen, status bar, and dockable plot widgets.

    * - :mod:`sigimax.h5`
      - HDF5 I/O — import, read, write, and browse HDF5 files with node
        factory and data extraction utilities.

    * - :mod:`sigimax.adapters_plotpy`
      - PlotPy adapters — converters between Sigima objects
        (``SignalObj``, ``ImageObj``, ROIs) and PlotPy plot/annotation items.

    * - :mod:`sigimax.utils`
      - Utilities — Qt helpers (log management, signal blocking, progress bars),
        configuration directory resolution, and callback workers.


.. toctree::
   :maxdepth: 2
   :caption: Public modules:

   app
   config
   env
   mainwindow
   widgets
   h5
   adapters_plotpy
   utils
