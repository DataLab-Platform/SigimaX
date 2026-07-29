.. _features:

Features
========

This page provides an organized catalog of SigimaX's key features.

Application Framework
---------------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Feature
      - Description
    * - :class:`~sigimax.mainwindow.SGMXMainWindow`
      - Generic main window with customizable menus, toolbars, console, and dock
        widgets. Derived apps subclass this to build their own UI.
    * - :func:`~sigimax.app.create`
      - Instantiate a main window with optional splash screen, console, and size.
        Returns the window instance for embedding.
    * - :func:`~sigimax.app.run`
      - Create the window and enter the Qt event loop. The standard entry point
        for standalone applications.
    * - :class:`~sigimax.widgets.splashscreen.SplashScreenConfig`
      - Configurable splash screen with image, app name, version, tagline, and
        optional progress display.

Configuration System
--------------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Feature
      - Description
    * - :class:`~sigimax.config.SigimaXOptions`
      - Full configuration singleton (``CONF``) with 20+ typed options covering
        app metadata, plot defaults, HDF5 settings, and more.
    * - ``EnumOptionField``
      - Option constrained to a set of string choices, with validation.
    * - ``TupleOptionField``
      - Fixed-length tuple option with type checking.
    * - ``FontOptionField``
      - Font option with validation against available system fonts.
    * - JSON persistence
      - ``save()`` / ``load()`` methods for configuration persistence.
    * - Context managers
      - Temporary overrides with ``option.context(value)`` pattern.

.. admonition:: Configuration options reference

    The full list of configuration options available in the ``CONF`` singleton:

    .. options-table::

HDF5 Workspace
--------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Feature
      - Description
    * - Open/Save workspace
      - File actions and workspace-state handling. Derived applications provide
        their own workspace serialization.
    * - :class:`~sigimax.widgets.h5browser.H5BrowserDialog`
      - Interactive HDF5 file browser with tree view, supporting scalar, array,
        text, and compound datasets.
    * - Import datasets
      - ``import_dataset_from_file()`` hook for derived apps to handle
        application-specific HDF5 dataset import.
    * - :class:`~sigimax.h5.H5Importer`
      - Low-level HDF5 import utilities with node factory and data extraction.

See :doc:`hdf5_workspace` for the persistence contract and its complete
derived-application example.

Scientific Widgets
------------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Widget
      - Description
    * - :class:`~sigimax.widgets.plotdock.DockablePlotWidget`
      - Embeds PlotPy plots in dock widgets, with configurable watermark and
        dock location. Supports ``PlotType.CURVE`` and ``PlotType.IMAGE``.
    * - Curve fitting dialogs
      - Gaussian, polynomial, and custom curve fitting via
        :mod:`sigimax.widgets.fitdialog`.
    * - Signal peak detection
      - Interactive peak detection dialog via
        :mod:`sigimax.widgets.signalpeak`.
    * - Signal baseline selection
      - Baseline selection for background subtraction via
        :mod:`sigimax.widgets.signalbaseline`.
    * - Signal cursor
      - Cursor-based value readout via
        :mod:`sigimax.widgets.signalcursor`.
    * - Signal delta-X
      - Delta-X measurement between two points via
        :mod:`sigimax.widgets.signaldeltax`.
    * - Image background
      - Image background region selection via
        :mod:`sigimax.widgets.imagebackground`.
    * - :class:`~sigimax.widgets.wizard.Wizard`
      - Multi-page wizard dialog with navigation, validation, and data
        collection (Next/Back/Finish/Cancel).
    * - :class:`~sigimax.widgets.logviewer.LogViewerWindow`
      - Log viewer dialog for displaying application log files.
    * - :class:`~sigimax.widgets.warningerror.WarningErrorMessageBox`
      - Warning/error display dialog with traceback support.

Status Bar Widgets
------------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Widget
      - Description
    * - :class:`~sigimax.widgets.status.MemoryStatus`
      - Displays current memory usage with configurable alarm threshold.
    * - :class:`~sigimax.widgets.status.ConsoleStatus`
      - Console toggle button in the status bar.
    * - :class:`~sigimax.widgets.status.BaseStatus`
      - Base status bar widget for custom status indicators.

PlotPy Adapters
---------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Feature
      - Description
    * - Signal/Image adapters
      - Convert between Sigima objects (:class:`~sigima.objects.SignalObj`,
        :class:`~sigima.objects.ImageObj`) and PlotPy plot items for display.
    * - ROI adapters
      - Convert between Sigima ROI objects and PlotPy annotation items
        (segment, rectangular, circular, polygonal).
    * - :func:`~sigimax.adapters_plotpy.create_adapter_from_object`
      - Factory function that dispatches to the correct adapter based on
        object type.
    * - JSON roundtrips
      - ``items_to_json()`` / ``json_to_items()`` for serializing plot items.

Runtime Environment
-------------------

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Feature
      - Description
    * - :class:`~sigimax.env.SGMXExecEnv`
      - Runtime environment singleton (``execenv``) controlling unattended mode,
        verbosity levels, demo mode, screenshot capture, and delay settings.
    * - :class:`~sigimax.env.VerbosityLevels`
      - Enum with ``quiet``, ``normal``, and ``debug`` verbosity levels.
    * - Command-line arguments
      - ``--unattended``, ``--verbose``, ``--screenshot``, ``--delay``,
        ``--version``, ``--reset`` parsed automatically on startup.
    * - Context manager
      - ``execenv.context()`` for temporarily overriding environment settings.

Internationalization
--------------------

SigimaX supports internationalization with gettext:

- All UI strings are wrapped with ``_()`` from :mod:`sigimax.config`
- Translations are stored in ``locale/`` (currently English and French)
- Use ``guidata.utils.translations`` CLI to scan and compile translations
