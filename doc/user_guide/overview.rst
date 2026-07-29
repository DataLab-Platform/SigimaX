.. _overview:

Overview
========

What is SigimaX?
-----------------

**SigimaX** is an open-source Python framework for building Qt-based scientific
desktop applications. It provides a reusable application skeleton — main window,
configuration system, embedded widgets, and HDF5 infrastructure — so that
developers can focus on domain-specific features instead of boilerplate.

SigimaX is extracted from `DataLab <https://datalab-platform.com/>`_, a mature
open-source platform for scientific signal and image processing, and powers its
GUI layer.

Why SigimaX?
-------------

Building a scientific desktop application from scratch typically requires:

- A main window with menus, toolbars, dock widgets, and status bar
- A configuration system with typed options, persistence, and defaults
- HDF5 file management (industry standard for scientific data)
- An embedded Python console for scripting and debugging
- Specialized dialogs for signal/image analysis (fitting, peak detection, etc.)
- Production-grade features: splash screen, memory monitoring, log viewer

SigimaX provides all of these as a **subclassable framework**, so derived
applications only need to add their domain-specific logic.

Position in the Stack
---------------------

SigimaX sits between the low-level libraries (PlotPy, guidata, PythonQwt) and
end-user applications:

.. code-block:: text

    End-user apps (DataLab, custom scientific apps)
             ↓  subclass / configure
          SigimaX            ← THIS PROJECT (framework layer)
             ↓  depends on
       Sigima (computation) + PlotPy + guidata + PythonQwt
             ↓
         NumPy / SciPy / Qt

.. list-table::
    :header-rows: 1
    :align: left

    * - Layer
      - Project
      - Role
    * - End-user apps
      - DataLab
      - Signal/image processing GUI application
    * - GUI framework
      - **SigimaX**
      - Reusable application skeleton
    * - Computation
      - Sigima
      - Headless scientific computing (signals & images)
    * - Plotting
      - PlotPy + PythonQwt
      - Interactive plot widgets
    * - GUI toolkit
      - guidata
      - Dataset/parameter framework with automatic GUI generation
    * - Foundation
      - NumPy + SciPy + Qt
      - Core scientific and GUI libraries

Architecture
------------

.. code-block:: text

    sigimax/
    ├── app.py              # Application launcher (create / run)
    ├── config.py           # Configuration system (SigimaXOptions, CONF singleton)
    ├── env.py              # Runtime environment (verbosity, unattended mode)
    ├── mainwindow.py       # SGMXMainWindow (generic main window)
    ├── widgets/            # Reusable Qt widgets
    │   ├── plotdock.py     # DockablePlotWidget
    │   ├── splashscreen.py # Configurable splash screen
    │   ├── h5browser.py    # HDF5 file browser
    │   ├── logviewer.py    # Log viewer dialog
    │   ├── status.py       # Status bar widgets (memory, console)
    │   ├── fitdialog.py    # Curve fitting dialogs
    │   ├── signalpeak.py   # Signal peak detection
    │   ├── signalbaseline.py # Signal baseline selection
    │   ├── signalcursor.py # Signal cursor selection
    │   ├── signaldeltax.py # Signal delta-X measurement
    │   ├── wizard.py       # Multi-page wizard dialog
    │   └── ...             # File dialogs, warning/error boxes
    ├── h5/                 # HDF5 I/O (read/write/import)
    ├── adapters_plotpy/    # Converters between PlotPy/guidata and Sigima objects
    ├── utils/              # Qt helpers, config dir resolution
    ├── data/               # Icons, resources
    └── locale/             # Translations (EN, FR)

Core Modules
^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :align: left

    * - Module
      - Purpose
    * - :mod:`sigimax.app`
      - Application launcher — ``create()`` and ``run()`` functions
    * - :mod:`sigimax.config`
      - Configuration system — ``SigimaXOptions``, ``CONF`` singleton, option fields
    * - :mod:`sigimax.env`
      - Runtime environment — ``SGMXExecEnv``, verbosity levels, unattended mode
    * - :mod:`sigimax.mainwindow`
      - ``SGMXMainWindow`` — generic main window with menus, console, HDF5 workspace

Design Philosophy
-----------------

SigimaX separates the **generic application skeleton** from **domain-specific logic**.
Derived applications follow a three-step pattern:

1. **Subclass** :class:`~sigimax.config.SigimaXOptions` to add application-specific
   configuration fields
2. **Subclass** :class:`~sigimax.mainwindow.SGMXMainWindow` to customize menus,
   toolbars, and dock widgets
3. **Call** :func:`~sigimax.app.run` to launch the application with splash screen
   support

This architecture is proven in production:
`DataLab <https://datalab-platform.com/>`_ is built entirely on this pattern.

Configuration System
^^^^^^^^^^^^^^^^^^^^

The configuration system uses typed option fields that support:

- **Type safety**: ``TypedOptionField`` (int, str, bool, float),
  ``EnumOptionField`` (constrained choices), ``TupleOptionField`` (fixed-length tuples),
  ``FontOptionField`` (font validation)
- **Persistence**: JSON save/load with ``save()`` and ``load()`` methods
- **Context managers**: Temporary overrides with ``option.context(value)``
- **Defaults**: Built-in reset-to-defaults mechanism

.. code-block:: python

    from sigimax.config import CONF as Conf

    # Get/set options
    colormap = Conf.ima_def_colormap.get()
    Conf.ima_def_colormap.set("gray")

    # Context manager for temporary overrides
    with Conf.fft_shift_enabled.context(False):
        # FFT shift disabled in this block
        ...

What SigimaX Provides vs What Stays in Derived Apps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 50 50

    * - **In SigimaX**
      - **Stays in derived apps (e.g. DataLab)**
    * - Configuration system
      - Signal/Image panels, processors
    * - Generic main window
      - Action handler, plugin system
    * - Dockable plot widgets
      - Remote control (XML-RPC, Web API)
    * - HDF5 I/O + browser
      - Macro editor, new-object dialogs
    * - Scientific dialogs (fit, baseline, peak, cursor…)
      - Application-specific UI and processing
    * - Log viewer, status bar, splash screen, wizard
      - Object model, plot handler
    * - PlotPy adapters
      - Processor registration pattern
    * - Environment/exec utilities
      - Tour/tutorial features
