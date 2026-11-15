# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Minimal Derived Application
============================

This example demonstrates the **derivation pattern** — the core concept of SigimaX.
In just a few lines of code, you can build a full-featured scientific desktop
application with menus, toolbars, console, and status bar.

The three-step pattern is:

1. **Subclass** :class:`~sigimax.config.SigimaXOptions` for app-specific options
2. **Subclass** :class:`~sigimax.mainwindow.SGMXMainWindow` for custom UI
3. **Install** the options with :func:`~sigimax.config.set_conf`, then **call**
   :func:`~sigimax.app.create` to launch

This example creates a minimal "MyApp" with a dockable curve plot widget.
"""

# %%
# Importing necessary modules
# ---------------------------

from plotpy.constants import PlotType

from sigimax.app import create
from sigimax.config import (
    EnumOptionField,
    SigimaXOptions,
    TypedOptionField,
    _,
    get_conf,
    reset_conf,
    set_conf,
)
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils.qthelpers import sigimax_app_context
from sigimax.widgets.plotdock import DockablePlotWidget

# %%
# Step 1: Define custom configuration
# ------------------------------------
#
# Subclass :class:`~sigimax.config.SigimaXOptions` to add fields specific to
# your application. Options are typed, validated, and support JSON persistence.


class MyAppOptions(SigimaXOptions):
    """Custom configuration for the demo application."""

    def __init__(self):
        super().__init__()
        self.app_name.set("MyApp")
        self.app_version.set("0.1.0")

        # Add a custom string option
        self.greeting = TypedOptionField(
            self,
            "greeting",
            default="Hello from MyApp!",
            expected_type=str,
            description="Startup greeting message",
        )

        # Add a constrained enum option
        self.theme = EnumOptionField(
            self,
            "theme",
            default="light",
            choices=["light", "dark", "auto"],
            description="Application color theme",
        )


# %%
# Step 2: Customize the main window
# ----------------------------------
#
# Subclass :class:`~sigimax.mainwindow.SGMXMainWindow` and override its setup
# hooks to add your own menus, toolbars, and dock widgets. Docks are added in
# ``_setup_docks``, with ``_add_dockwidget``: the saved window layout is then
# applied to them, and they follow color theme changes.


class MyAppMainWindow(SGMXMainWindow):
    """Main window with a dockable curve viewer."""

    def _setup_docks(self):
        # Add a dockable curve plot widget
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.curve_dock, _("Curve Viewer"), name="curve_viewer")


# %%
# Step 3: Launch the application
# --------------------------------
#
# Install the options with :func:`~sigimax.config.set_conf` before creating the
# window: SigimaX and your own code read them with
# :func:`~sigimax.config.get_conf`. Then use :func:`~sigimax.app.create` to
# instantiate the window (without entering the Qt event loop, so sphinx-gallery
# can capture the screenshot).

set_conf(MyAppOptions())
try:
    with sigimax_app_context(exec_loop=False):
        win = create(
            window_class=MyAppMainWindow,
            splash=False,
            console=False,
            size=(900, 600),
        )
        win.show()

        # Print configuration to verify it works
        print(f"App name: {get_conf().app_name.get()}")
        print(f"Greeting: {get_conf().greeting.get()}")
        print(f"Window title: {win.windowTitle()}")

        win.set_modified(False)
        win.close()
finally:
    # Restore the base configuration so later examples/tests are unaffected
    reset_conf()

# %%
# Summary
# -------
#
# This example showed the minimal derivation pattern:
#
# - **Configuration**: ``MyAppOptions`` adds typed, validated options, and
#   ``set_conf()`` makes it the active configuration
# - **Main window**: ``MyAppMainWindow`` adds a curve plot dock
# - **Launcher**: ``create()`` or ``run()`` starts the application
#
# For a production app, use ``run(window_class=MyAppMainWindow)`` instead
# of ``create()`` — it enters the Qt event loop and shows a splash screen.
