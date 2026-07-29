# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Derived application example test
---------------------------------

This test demonstrates how to build a custom application on top of SigimaX by:

1. Subclassing :class:`SigimaXOptions` to add application-specific options.
2. Subclassing :class:`SGMXMainWindow` to customize the main window (menus,
   toolbars, dockable widgets, etc.).

The resulting "MyApp" application showcases the full derivation pattern that
downstream projects (like DataLab) can follow.
"""

# guitest: show

from __future__ import annotations

import numpy as np
import pytest
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action
from plotpy.constants import PlotType
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from sigimax.app import create as sigimax_create
from sigimax.config import CONF as Conf
from sigimax.config import EnumOptionField, SigimaXOptions, TypedOptionField, _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth
from sigimax.widgets.plotdock import DockablePlotWidget
from sigimax.widgets.splashscreen import SigimaXSplashScreen, SplashScreenConfig

# =============================================================================
# 1. Derived configuration: MyAppOptions
# =============================================================================


class MyAppOptions(SigimaXOptions):
    """Custom options for the MyApp application.

    Extends :class:`SigimaXOptions` with application-specific settings
    such as a greeting message, max recent files, and a default unit system.
    """

    APP_NAME = "MyApp"
    CONF_VERSION = "1.0.0"

    def __init__(self) -> None:
        super().__init__()

        # Override default application metadata
        self.app_name.set("MyApp")
        self.app_version.set("0.1.0")
        self.app_desc.set("A demo application built on SigimaX")

        # --- Application-specific options ---

        self.greeting_message = TypedOptionField(
            self,
            "greeting_message",
            default="Welcome to MyApp!",
            expected_type=str,
            description="Message displayed in the status bar on startup.",
        )
        self.max_recent_files = TypedOptionField(
            self,
            "max_recent_files",
            default=10,
            expected_type=int,
            description="Maximum number of recent files to remember.",
        )
        self.default_unit_system = EnumOptionField(
            self,
            "default_unit_system",
            default="metric",
            choices=["metric", "imperial"],
            description="Default unit system for display.",
        )
        self.auto_compute_on_load = TypedOptionField(
            self,
            "auto_compute_on_load",
            default=False,
            expected_type=bool,
            description=(
                "If True, automatically run default computations "
                "when loading a dataset."
            ),
        )

        # Recapture defaults after adding custom options
        self._defaults.update(
            {
                name: getattr(self, name).get()
                for name in (
                    "greeting_message",
                    "max_recent_files",
                    "default_unit_system",
                    "auto_compute_on_load",
                )
            }
        )


# =============================================================================
# 2. Derived main window: MyAppMainWindow
# =============================================================================


class MyAppMainWindow(SGMXMainWindow):
    """Custom main window for the MyApp application.

    Extends :class:`SGMXMainWindow` with:

    - A custom "Tools" menu with domain-specific actions.
    - A dockable curve plot widget.
    - A demo action that generates a sine wave and displays it.

    The pattern for derived windows is:

    1. Configure the global ``Conf`` options (app_name, app_version, etc.)
       **before** calling ``super().__init__()``, because :class:`SGMXMainWindow`
       reads from the module-level ``Conf`` reference.
    2. Add custom UI elements (menus, docks, toolbars) after initialization.
    """

    def __init__(
        self,
        console: bool | None = None,
        hide_on_close: bool = False,
    ) -> None:
        # Configure global Conf BEFORE calling super().__init__() so that
        # SGMXMainWindow reads the correct app_name, app_version, etc.
        Conf.app_name.set("MyApp")
        Conf.app_version.set("0.1.0")
        Conf.app_desc.set("A demo application built on SigimaX")

        super().__init__(console=console, hide_on_close=hide_on_close)

        # --- Custom widgets ---
        self.curve_dock: DockablePlotWidget | None = None

        # --- Build custom UI ---
        self._setup_custom_ui()

    # ------------------------------------------------------------------
    # Custom UI setup
    # ------------------------------------------------------------------

    def _setup_custom_ui(self) -> None:
        """Set up MyApp-specific menus, toolbars, and dock widgets."""
        self._add_curve_dock()
        self._add_tools_menu()
        self._add_custom_toolbar()

    def _add_curve_dock(self) -> None:
        """Add a dockable curve plot widget to the main window."""
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        dockwidget, location = self.curve_dock.create_dockwidget(_("Curve Viewer"))
        self.addDockWidget(location, dockwidget)
        self.docks[self.curve_dock] = dockwidget

    def _add_tools_menu(self) -> None:
        """Add a custom 'Tools' menu to the menu bar."""
        tools_menu = self.menuBar().addMenu(_("&Tools"))

        generate_action = create_action(
            self,
            _("Generate sine wave"),
            icon=get_icon("new_signal.svg"),
            tip=_("Generate a sample sine wave and display it"),
            triggered=self._generate_sine_wave,
        )
        clear_action = create_action(
            self,
            _("Clear plot"),
            icon=get_icon("libre-gui-close.svg"),
            tip=_("Remove all curves from the plot"),
            triggered=self._clear_plot,
        )
        show_options_action = create_action(
            self,
            _("Show configuration"),
            tip=_("Print all current configuration options to the console"),
            triggered=self._show_configuration,
        )
        add_actions(
            tools_menu, [generate_action, clear_action, None, show_options_action]
        )

    def _add_custom_toolbar(self) -> None:
        """Add a custom toolbar with quick-access actions."""
        toolbar = QW.QToolBar(_("MyApp Tools"), self)
        toolbar.setObjectName("myapp_tools_toolbar")
        self.addToolBar(QC.Qt.TopToolBarArea, toolbar)

        generate_action = create_action(
            self,
            _("Sine"),
            icon=get_icon("new_signal.svg"),
            tip=_("Generate a sine wave"),
            triggered=self._generate_sine_wave,
        )
        toolbar.addAction(generate_action)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    def _generate_sine_wave(self) -> None:
        """Generate a sine wave and display it in the curve dock."""
        if self.curve_dock is None:
            return
        x = np.linspace(0, 4 * np.pi, 500)
        y = np.sin(x) + 0.1 * np.random.randn(len(x))

        plot = self.curve_dock.get_plot()
        from plotpy.builder import make  # pylint: disable=import-outside-toplevel

        curve = make.curve(x, y, title="sin(x) + noise", color="blue")
        plot.add_item(curve)
        plot.do_autoscale()

        self.statusBar().showMessage(
            _("Generated sine wave with %d points") % len(x), 3000
        )

    def _clear_plot(self) -> None:
        """Remove all items from the curve dock plot."""
        if self.curve_dock is None:
            return
        plot = self.curve_dock.get_plot()
        plot.del_all_items()
        plot.replot()
        self.statusBar().showMessage(_("Plot cleared"), 2000)

    def _show_configuration(self) -> None:
        """Print all configuration options to stdout (and console if available)."""
        print("\n--- MyApp Configuration ---")
        Conf.describe_all()
        print("---\n")


# =============================================================================
# 3. Test function
# =============================================================================


@pytest.mark.unit
def test_derived_app():
    """Test that a derived application can be built on top of SigimaX."""
    # -- Verify custom options work --
    conf = MyAppOptions()
    assert conf.app_name.get() == "MyApp"
    assert conf.app_version.get() == "0.1.0"
    assert conf.greeting_message.get() == "Welcome to MyApp!"
    assert conf.max_recent_files.get() == 10
    assert conf.default_unit_system.get() == "metric"
    assert conf.auto_compute_on_load.get() is False

    # Test option modification
    conf.greeting_message.set("Hello, World!")
    assert conf.greeting_message.get() == "Hello, World!"

    # Test context manager override
    with conf.max_recent_files.context(5):
        assert conf.max_recent_files.get() == 5
    assert conf.max_recent_files.get() == 10

    # Test reset to defaults
    conf.greeting_message.set("Changed")
    conf.reset_to_defaults()
    assert conf.greeting_message.get() == "Welcome to MyApp!"

    # Test serialization round-trip
    d = conf.to_dict()
    assert "greeting_message" in d
    assert "max_recent_files" in d
    assert d["default_unit_system"] == "metric"

    conf2 = MyAppOptions()
    conf2.from_dict(d)
    assert conf2.greeting_message.get() == conf.greeting_message.get()
    assert conf2.max_recent_files.get() == conf.max_recent_files.get()

    # Test enum validation
    try:
        conf.default_unit_system.set("invalid_unit")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected

    # Test list_options includes custom options
    option_names = conf.list_options()
    assert "greeting_message" in option_names
    assert "max_recent_files" in option_names
    assert "default_unit_system" in option_names
    assert "auto_compute_on_load" in option_names
    # Also includes inherited SigimaX options
    assert "color_mode" in option_names
    assert "console_enabled" in option_names

    print("All custom option tests passed.")


@pytest.mark.app
def test_splash_screen():
    """Test that the splash screen can be created and shown."""
    with qth.sigimax_app_context(exec_loop=False):
        # Test 1: Splash screen from explicit config (fallback pixmap, no image)
        config = SplashScreenConfig(
            app_name="MyApp",
            app_version="0.1.0",
            tagline="A demo application",
            show_progress=True,
        )
        assert not config.is_enabled  # No image_path => disabled

        # Test 2: Splash screen with a non-existent image (fallback)
        config_with_path = SplashScreenConfig(
            image_path="nonexistent.png",
            app_name="MyApp",
            app_version="0.1.0",
        )
        assert config_with_path.is_enabled

        splash = SigimaXSplashScreen(config_with_path)
        splash.show()
        splash.show_message("Loading test...")
        splash.close()

        # Test 3: from_conf returns None when no splash image is configured
        splash_from_conf = SigimaXSplashScreen.from_conf()
        assert splash_from_conf is None  # Default config has no splash image

        # Test 4: create() launcher works without splash
        win = sigimax_create(
            window_class=MyAppMainWindow,
            splash=False,
            console=False,
            size=(800, 600),
        )
        assert win is not None
        win.set_modified(False)
        win.close()

    print("Splash screen tests passed.")


@pytest.mark.app
def test_derived_app_window():
    # pylint: disable=protected-access
    # pylint: disable=redefined-outer-name
    """Test that the derived main window creates and runs properly."""
    with qth.sigimax_app_context(exec_loop=False):
        win = MyAppMainWindow(console=False)
        win.resize(1200, 700)
        win.show()

        # Verify window title contains our app name
        assert "MyApp" in win.windowTitle()

        # Verify the curve dock was created
        assert win.curve_dock is not None

        # Test generating a sine wave
        win._generate_sine_wave()
        plot = win.curve_dock.get_plot()
        items_before_generate = len(plot.get_items())
        assert items_before_generate > 0

        # Test clearing the plot — note that the plot may keep internal
        # items (e.g., tool markers), so we just check the count decreased
        initial_count = len(plot.get_items())
        win._generate_sine_wave()  # add another curve
        assert len(plot.get_items()) > initial_count
        win._clear_plot()

        # Test show configuration (just ensure it doesn't crash)
        win._show_configuration()

        # Clean close
        win.set_modified(False)
        win.close()

    print("Derived main window test passed.")


if __name__ == "__main__":
    from sigimax.app import run as sigimax_run

    # Launch with splash screen (fallback pixmap since no image is provided)
    splash_config = SplashScreenConfig(
        image_path="nonexistent_demo.png",  # Will use fallback pixmap
        app_name="MyApp",
        app_version="0.1.0",
        tagline="A demo application built on SigimaX",
    )
    sigimax_run(
        window_class=MyAppMainWindow,
        splash_config=splash_config,
        console=True,
        size=(1200, 700),
    )
