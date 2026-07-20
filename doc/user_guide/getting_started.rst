.. _getting_started:

Getting Started
===============

This page provides a quick introduction to building applications with SigimaX.

SigimaX follows a **three-step derivation pattern**: subclass the configuration,
subclass the main window, and launch with ``run()``. This pattern is proven in
production — `DataLab <https://datalab-platform.com/>`_ is built entirely on it.

The Derivation Pattern
----------------------

**Step 1 — Subclass** :class:`~sigimax.config.SigimaXOptions` to add
application-specific configuration fields:

.. code-block:: python

    from sigimax.config import TypedOptionField
    from sigimax.config import EnumOptionField, SigimaXOptions

    class MyAppOptions(SigimaXOptions):
        ENV_VAR = "MYAPP_OPTIONS_JSON"

        def __init__(self):
            super().__init__()
            self.app_name.set("MyApp", sync_env=False)
            self.greeting = TypedOptionField(
                self, "greeting", default="Hello!",
                expected_type=str, description="Startup message",
            )
            self.unit_system = EnumOptionField(
                self, "unit_system", default="metric",
                choices=["metric", "imperial"],
                description="Default units",
            )

**Step 2 — Subclass** :class:`~sigimax.mainwindow.SGMXMainWindow` to customize
the user interface:

.. code-block:: python

    from sigimax.config import CONF as Conf, _
    from sigimax.mainwindow import SGMXMainWindow
    from sigimax.widgets.plotdock import DockablePlotWidget
    from plotpy.constants import PlotType

    class MyAppMainWindow(SGMXMainWindow):
        def __init__(self, console=None, hide_on_close=False):
            Conf.app_name.set("MyApp")
            super().__init__(console=console, hide_on_close=hide_on_close)
            # Add a dockable curve plot
            self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
            dock, loc = self.curve_dock.create_dockwidget(_("Curve Viewer"))
            self.addDockWidget(loc, dock)

**Step 3 — Launch** the application:

.. code-block:: python

    from sigimax.app import run

    run(window_class=MyAppMainWindow)

That's it. Three classes, three steps — and you have a full-featured scientific
desktop application with menus, toolbars, console, HDF5 workspace, and status bar.

Key Concepts
^^^^^^^^^^^^

- **Configuration system**: Options are typed fields (``TypedOptionField``,
  ``EnumOptionField``, ``TupleOptionField``) that support ``get()``/``set()``/
  ``context()`` API, JSON persistence, and environment variable sync.

- **Overridable hooks**: The main window provides hooks that derived apps can
  override: ``reset_all()``, ``_is_save_enabled()``, ``_update_file_menu()``,
  ``_update_view_menu()``, ``_about()``.

- **Built-in features**: HDF5 workspace (open/save/browse), embedded Python
  console, status bar with memory monitoring, splash screen support.

What's Included
---------------

SigimaX provides 15+ ready-to-use scientific widgets:

.. list-table::
    :header-rows: 1
    :align: left
    :widths: 30 70

    * - Widget
      - Purpose
    * - :class:`~sigimax.widgets.plotdock.DockablePlotWidget`
      - Embeddable PlotPy plot in dock widgets
    * - :class:`~sigimax.widgets.h5browser.H5BrowserDialog`
      - Interactive HDF5 file browser
    * - :class:`~sigimax.widgets.fitdialog`
      - Curve fitting dialogs (Gaussian, polynomial, etc.)
    * - :class:`~sigimax.widgets.signalpeak`
      - Signal peak detection dialog
    * - :class:`~sigimax.widgets.signalbaseline`
      - Signal baseline selection dialog
    * - :class:`~sigimax.widgets.signalcursor`
      - Signal cursor selection dialog
    * - :class:`~sigimax.widgets.signaldeltax`
      - Signal delta-X measurement dialog
    * - :class:`~sigimax.widgets.imagebackground`
      - Image background selection dialog
    * - :class:`~sigimax.widgets.logviewer.LogViewerWindow`
      - Log viewer dialog
    * - :class:`~sigimax.widgets.wizard.Wizard`
      - Multi-page wizard dialog
    * - :class:`~sigimax.widgets.splashscreen.SigimaXSplashScreen`
      - Configurable splash screen
    * - :class:`~sigimax.widgets.status.MemoryStatus`
      - Status bar memory usage widget
    * - :class:`~sigimax.widgets.warningerror.WarningErrorMessageBox`
      - Warning/error display dialog

Next Steps
----------

- Browse the :doc:`../auto_examples/index` to see SigimaX in action
- Read the :doc:`overview` for architecture details
- Dive into the :doc:`/api/index` for complete reference documentation
