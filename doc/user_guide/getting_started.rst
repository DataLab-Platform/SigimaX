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
        def __init__(self):
            super().__init__()
            self.app_name.set("MyApp")
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
the user interface, by overriding its setup hooks:

.. code-block:: python

    from sigimax.config import _
    from sigimax.mainwindow import SGMXMainWindow
    from sigimax.widgets.plotdock import DockablePlotWidget
    from plotpy.constants import PlotType

    class MyAppMainWindow(SGMXMainWindow):
        def _setup_docks(self):
            # Add a dockable curve plot
            self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
            self._add_dockwidget(
                self.curve_dock, _("Curve Viewer"), name="curve_viewer"
            )

``_setup_docks()`` is called before the saved window layout is restored, and
``_add_dockwidget()`` registers the dock in ``self.docks``: the dock gets its
saved geometry back and follows color theme changes. The ``name`` argument is
the stable Qt object name under which its layout is saved.

**Step 3 — Install** the configuration and **launch** the application:

.. code-block:: python

    from sigimax.app import run
    from sigimax.config import set_conf

    set_conf(MyAppOptions())
    run(window_class=MyAppMainWindow)

That's it. Two classes, three steps — and you have a full-featured scientific
desktop application with menus, toolbars, console, HDF5 browsing and import,
and status bar.

Active Configuration
^^^^^^^^^^^^^^^^^^^^

SigimaX modules read options through :func:`~sigimax.config.get_conf`, which
returns the *active* options container. :func:`~sigimax.config.set_conf` makes
your container the active one. Call it once, before the main window is created
(DataLab does it when its configuration module is imported), then read your
options with ``get_conf()``:

.. code-block:: python

    from sigimax.config import get_conf

    greeting = get_conf().greeting.get()

``CONF`` is the SigimaX base container: once another container is installed,
set and read options through ``get_conf()``, not ``CONF``.
:func:`~sigimax.config.set_conf` raises :class:`ValueError` if the container
lacks one of the base options (a :class:`~sigimax.config.SigimaXOptions`
subclass has them all). :func:`~sigimax.config.reset_conf` restores the base
container (mainly for tests).

Key Concepts
^^^^^^^^^^^^

- **Configuration system**: Options are typed fields (``TypedOptionField``,
  ``EnumOptionField``, ``TupleOptionField``) that support ``get()``/``set()``/
  ``context()`` API and JSON persistence.

- **Overridable hooks**: The main window provides hooks that derived apps can
  override: ``reset_all()``, ``_is_save_enabled()``,
  ``_get_file_menu_actions()``, ``_update_file_menu()``,
  ``_update_view_menu()``, ``_about()``, ``_before_setup()``,
  ``_setup_docks()``, ``_post_setup()``, and ``_after_setup()``. See
  :doc:`lifecycle` for their ordering and initialization contract.

- **Built-in features**: HDF5 GUI and generic dataset import; derived
  applications implement their own workspace persistence. SigimaX also
  provides an embedded Python console, status bar with memory monitoring, and
  splash screen support. See :doc:`hdf5_workspace` for the derived-application
  contract.

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
    * - :mod:`~sigimax.widgets.fitdialog`
      - Curve fitting dialogs (Gaussian, polynomial, etc.)
    * - :mod:`~sigimax.widgets.signalpeak`
      - Signal peak detection dialog
    * - :mod:`~sigimax.widgets.signalbaseline`
      - Signal baseline selection dialog
    * - :mod:`~sigimax.widgets.signalcursor`
      - Signal cursor selection dialog
    * - :mod:`~sigimax.widgets.signaldeltax`
      - Signal delta-X measurement dialog
    * - :mod:`~sigimax.widgets.imagebackground`
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
