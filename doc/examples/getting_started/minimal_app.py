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
3. **Call** :func:`~sigimax.app.create` to launch

This example creates a minimal "MyApp" with a dockable curve plot widget.
"""

# %%
# Importing necessary modules
# ---------------------------

from plotpy.constants import PlotType

from sigimax.app import create
from sigimax.config import CONF as Conf
from sigimax.config import EnumOptionField, SigimaXOptions, TypedOptionField, _
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
# Subclass :class:`~sigimax.mainwindow.SGMXMainWindow` to add your own menus,
# toolbars, and dock widgets.


class MyAppMainWindow(SGMXMainWindow):
    """Main window with a dockable curve viewer."""

    def __init__(self, console=None, hide_on_close=False):
        Conf.app_name.set("MyApp")
        Conf.app_version.set("0.1.0")
        super().__init__(console=console, hide_on_close=hide_on_close)

        # Add a dockable curve plot widget
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        dock, loc = self.curve_dock.create_dockwidget(_("Curve Viewer"))
        self.addDockWidget(loc, dock)


# %%
# Step 3: Launch the application
# --------------------------------
#
# Use :func:`~sigimax.app.create` to instantiate the window (without entering
# the Qt event loop, so sphinx-gallery can capture the screenshot).

with sigimax_app_context(exec_loop=False):
    win = create(
        window_class=MyAppMainWindow,
        splash=False,
        console=False,
        size=(900, 600),
    )
    win.show()

    # Print configuration to verify it works
    print(f"App name: {Conf.app_name.get()}")
    print(f"Window title: {win.windowTitle()}")

    win.set_modified(False)
    win.close()

# %%
# Summary
# -------
#
# This example showed the minimal derivation pattern:
#
# - **Configuration**: ``MyAppOptions`` adds typed, validated options
# - **Main window**: ``MyAppMainWindow`` adds a curve plot dock
# - **Launcher**: ``create()`` or ``run()`` starts the application
#
# For a production app, use ``run(window_class=MyAppMainWindow)`` instead
# of ``create()`` — it enters the Qt event loop and shows a splash screen.
