# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX Configuration Options System (:mod:`sigimax.config`)
------------------------------------------------------------

Sigima-style in-memory option system for SigimaX-based GUI applications.

This module provides a clean, extensible configuration system following the same
pattern as :mod:`sigima.config` (``OptionField`` with ``get``/``set``/``context``),
but tailored for GUI applications built on SigimaX.

Design principles:

- **Simple API**: Options are accessed via ``CONF.color_mode.get()`` and
  ``CONF.color_mode.set("dark")``.
- **Context managers**: Temporarily override options with
  ``with CONF.fft_shift_enabled.context(False): ...``.
- **Extensible via subclassing**: Derived applications (like DataLab) subclass
  :class:`SigimaXOptions` to add their own options.
- **Environment variable sync**: Options are synchronized via a JSON-encoded
  environment variable for cross-process communication.
- **Optional JSON file persistence**: For GUI apps that need to persist user
  preferences across sessions.

Typical usage:

.. code-block:: python

    from sigimax.config import CONF as Conf

    # Get an option value
    colormap = Conf.ima_def_colormap.get()

    # Set an option value
    Conf.ima_def_colormap.set("gray")

    # Temporarily override an option
    with Conf.fft_shift_enabled.context(False):
        # FFT shift is disabled in this block
        ...

    # Save/load from JSON file (for GUI persistence)
    Conf.save()  # saves to default config path
    Conf.load()  # loads from default config path

Extending for a derived application:

.. code-block:: python

    from sigimax.options import SigimaXOptions

    class MyAppOptions(SigimaXOptions):
        ENV_VAR = "MYAPP_OPTIONS_JSON"

        def __init__(self):
            super().__init__()
            self.my_custom_option = TypedOptionField(
                self, "my_custom_option", default=42,
                expected_type=int,
                description="My custom option for MyApp",
            )

    options = MyAppOptions()
"""

from __future__ import annotations

import json
import os
import os.path as osp
import sys
from pathlib import Path
from typing import Any

from guidata import configtools
from plotpy.config import CONF as PLOTPY_CONF
from plotpy.config import MAIN_BG_COLOR, MAIN_FG_COLOR
from sigima.config import (
    ImageIOOptionField,
    OptionField,
    OptionsContainer,
    TypedOptionField,
)
from sigima.config import options as sigima_options
from sigima.proc.title_formatting import (
    PlaceholderTitleFormatter,
    set_default_title_formatter,
)

from sigimax.utils import conf as _conf_module  # For config dir resolution

# Module-level constants
MOD_TITLE = "SigimaX"
MOD_NAME = "sigimax"

# Configure Sigima to use placeholder title formatting
set_default_title_formatter(PlaceholderTitleFormatter())

# Configure guidata translation and icons paths for SigimaX
_ = configtools.get_translation(MOD_NAME)
configtools.add_image_module_path(MOD_NAME, osp.join("data", "icons"))
DATAPATH = configtools.get_module_data_path(MOD_NAME, "data")

# Other Module-level constants
MOD_DESC = _("""SigimaX is a GUI library working with Sigima and PlotPyStack.
             It provides a App configuration system, a generic MainWindow class and a
             set of widgets to build applications on top of Sigima and PlotPyStack.""")

DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true")
if DEBUG:
    print("*** DEBUG mode *** [Reset configuration file, do not redirect std I/O]")

TEST_SEGFAULT_ERROR = len(os.environ.get("TEST_SEGFAULT_ERROR", "")) > 0
if TEST_SEGFAULT_ERROR:
    print('*** TEST_SEGFAULT_ERROR mode *** [Enabling test action in "?" menu]')
# DATETIME_FORMAT = "%d/%m/%Y - %H:%M:%S"


def get_old_log_fname(fname):
    """Return old log fname from current log fname"""
    return osp.splitext(fname)[0] + ".1.log"


def is_frozen(module_name: str) -> bool:
    """Test if module has been frozen (py2exe/cx_Freeze/pyinstaller)

    Args:
        module_name (str): module name

    Returns:
        bool: True if module has been frozen (py2exe/cx_Freeze/pyinstaller)
    """
    datapath = configtools.get_module_path(module_name)
    parentdir = osp.normpath(osp.join(datapath, osp.pardir))
    return not osp.isfile(__file__) or osp.isfile(parentdir)  # library.zip


IS_FROZEN = is_frozen(MOD_NAME)


def get_mod_source_dir() -> str | None:
    """Return module source directory

    Returns:
        str | None: module source directory, or None if not found
    """
    if IS_FROZEN:
        devdir = osp.abspath(osp.join(sys.prefix, os.pardir, os.pardir))
    else:
        devdir = osp.abspath(osp.join(osp.dirname(__file__), os.pardir))
    if osp.isfile(osp.join(devdir, MOD_NAME, "__init__.py")):
        return devdir
    # Unhandled case (this should not happen, but just in case):
    return None


# ---------------------------------------------------------------------------
# Custom OptionField subclasses for GUI application options
# ---------------------------------------------------------------------------


class EnumOptionField(OptionField):
    """Option field constrained to a fixed set of valid string values.

    Args:
        container: Options container instance to which this option belongs.
        name: Name of the option.
        default: Default value (must be one of ``choices``).
        choices: List of valid string values.
        description: Description of the option.
    """

    def __init__(
        self,
        container: AppOptionsContainer,
        name: str,
        default: str,
        choices: list[str],
        description: str = "",
        category: str = "",
    ) -> None:
        self.choices = choices
        super().__init__(container, name, default, description, category)

    def check(self, value: Any) -> None:
        """Check if value is one of the allowed choices.

        Args:
            value: The value to check.

        Raises:
            ValueError: If the value is not one of the allowed choices.
        """
        if value not in self.choices:
            raise ValueError(
                f"Option '{self.name}': expected one of {self.choices}, got {value!r}"
            )


class TupleOptionField(OptionField):
    """Option field for tuple values (e.g., window position, size).

    Handles JSON serialization where tuples become lists, automatically
    converting back to tuples on load.

    Args:
        container: Options container instance to which this option belongs.
        name: Name of the option.
        default: Default value (tuple or None).
        description: Description of the option.
    """

    def check(self, value: Any) -> None:
        """Check if value is a tuple, list (from JSON), or None.

        Args:
            value: The value to check.

        Raises:
            ValueError: If the value is not a valid type.
        """
        if value is not None and not isinstance(value, (tuple, list)):
            raise ValueError(
                f"Option '{self.name}': expected tuple, list, or None, "
                f"got {type(value).__name__}"
            )

    def set(self, value: Any, *, sync_env: bool = True) -> None:
        """Set the value, converting lists to tuples.

        Args:
            value: The new value to assign.
            sync_env: Whether to synchronize the environment variable
             (keyword-only).
        """
        if isinstance(value, list):
            value = tuple(value)
        super().set(value, sync_env=sync_env)


class FontOptionField(OptionField):
    """Option field for font specifications.

    Stores fonts as a tuple of (family: str, size: int, bold: bool).

    Args:
        container: Options container instance to which this option belongs.
        name: Name of the option.
        default: Default value as (family, size, bold) tuple.
        description: Description of the option.
    """

    def check(self, value: Any) -> None:
        """Check if value is a valid font tuple.

        Args:
            value: The value to check.

        Raises:
            ValueError: If the value is not a valid font specification.
        """
        if value is not None and (
            not isinstance(value, (tuple, list))
            or len(value) != 3
            or not isinstance(value[0], str)
        ):
            raise ValueError(
                f"Option '{self.name}': expected (family, size, bold) tuple, "
                f"got {value!r}"
            )

    def set(self, value: Any, *, sync_env: bool = True) -> None:
        """Set the value, converting lists to tuples.

        Args:
            value: The new value to assign.
            sync_env: Whether to synchronize the environment variable
             (keyword-only).
        """
        if isinstance(value, list):
            value = tuple(value)
        super().set(value, sync_env=sync_env)


# ---------------------------------------------------------------------------
# Base container with JSON file persistence
# ---------------------------------------------------------------------------


class AppOptionsContainer(OptionsContainer):
    """Base options container for SigimaX-based GUI applications.

    Extends Sigima's :class:`OptionsContainer` with optional JSON file
    persistence for GUI applications that need to save user preferences
    across sessions.

    Derived applications should subclass this (or :class:`SigimaXOptions`)
    to add their own options as OptionField attributes in ``__init__``.

    Class attributes:
        ENV_VAR: Environment variable name for JSON sync (override in subclass).
        APP_NAME: Application name used for default config directory.
    """

    ENV_VAR = "SIGIMAX_OPTIONS_JSON"
    APP_NAME = "SigimaX"

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        # Intentionally NOT calling super().__init__() because
        # OptionsContainer.__init__ creates Sigima-specific options.
        # We start fresh with our own option fields.
        pass

    # -- Environment variable sync (same pattern as Sigima) --

    @classmethod
    def set_env(cls, value: str) -> None:
        """Set the environment variable with the given JSON string.

        Args:
            value: A JSON string representation of the options to set.
        """
        os.environ[cls.ENV_VAR] = value

    @classmethod
    def get_env(cls) -> str:
        """Get the current value of the environment variable.

        Returns:
            The JSON string representation of the options from the
             environment variable.
        """
        return os.environ.get(cls.ENV_VAR, "{}")

    def ensure_loaded_from_env(self) -> None:
        """Load option values from the environment variable if set."""
        value = self.get_env()
        if value == "{}":
            return
        try:
            values = json.loads(value)
            self.from_dict(values)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[sigimax] Warning: failed to load options from env: {exc}")

    def to_env_json(self) -> str:
        """Return current options as a JSON string for the environment variable.

        Returns:
            A JSON string representation of the current options.
        """
        return json.dumps(self.to_dict())

    def sync_env(self) -> None:
        """Update the environment variable with current option values."""
        self.set_env(self.to_env_json())

    # -- Dictionary serialization --

    def to_dict(self) -> dict[str, Any]:
        """Return all option values as a dictionary.

        Returns:
            A dictionary with option names as keys and their current values.
        """
        return {
            name: getattr(self, name).get(sync_env=False)
            for name in vars(self)
            if isinstance(getattr(self, name), OptionField)
        }

    def from_dict(self, values: dict[str, Any]) -> None:
        """Set option values from a dictionary.

        Unknown keys are silently ignored, making this safe for loading
        options from a newer or older version of the application.

        Args:
            values: A dictionary with option names as keys and their new values.
        """
        for name, value in values.items():
            if hasattr(self, name):
                opt = getattr(self, name)
                if isinstance(opt, OptionField):
                    try:
                        opt.set(value, sync_env=False)
                    except (ValueError, TypeError) as exc:
                        print(
                            f"[sigimax] Warning: invalid value for "
                            f"option '{name}': {exc}"
                        )
        self.sync_env()

    # -- JSON file persistence --

    def _get_default_config_path(self) -> Path:
        """Return the default path for the JSON configuration file.

        Uses the same config directory as the INI-based system for
        backward compatibility.

        Returns:
            Path to the default JSON configuration file.
        """
        # Use guidata's config directory resolution
        try:
            config_dir = Path(_conf_module.Configuration.get_path(""))
        except Exception:  # pylint: disable=broad-except
            # Fallback to user home directory
            config_dir = Path.home() / f".{self.APP_NAME}"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "options.json"

    def save(self, path: str | Path | None = None) -> None:
        """Save current options to a JSON file.

        Args:
            path: Path to save to. If None, uses the default config path.
        """
        filepath = Path(path) if path else self._get_default_config_path()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, path: str | Path | None = None) -> None:
        """Load options from a JSON file.

        Missing keys are left at their current (default) values.
        Unknown keys are silently ignored.

        Args:
            path: Path to load from. If None, uses the default config path.
        """
        filepath = Path(path) if path else self._get_default_config_path()
        if not filepath.exists():
            return
        try:
            with open(filepath, encoding="utf-8") as f:
                values = json.load(f)
            self.from_dict(values)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[sigimax] Warning: failed to load options from {filepath}: {exc}")

    # -- Introspection --

    def describe_all(self) -> None:
        """Print the name, value, and description of all options."""
        for name in vars(self):
            opt = getattr(self, name)
            if isinstance(opt, OptionField):
                print(f"{name} = {opt.get(sync_env=False)}  # {opt.description}")

    def list_options(self) -> list[str]:
        """Return the sorted list of all option names.

        Returns:
            Sorted list of option attribute names.
        """
        return sorted(
            name for name in vars(self) if isinstance(getattr(self, name), OptionField)
        )


# ---------------------------------------------------------------------------
# PlotPy theme color constants
# ---------------------------------------------------------------------------

#: ROI line color (default blue)
ROI_LINE_COLOR = "#5555ff"
#: ROI selected line color
ROI_SEL_LINE_COLOR = "#9393ff"
#: Marker line color (default dark red)
MARKER_LINE_COLOR = "#A11818"
#: Marker text color
MARKER_TEXT_COLOR = "#440909"


class SigimaXOptions(AppOptionsContainer):
    """Generic options for SigimaX-based GUI applications.

    Contains all options that are useful for any derived application building
    on SigimaX (window management, console, I/O, visualization defaults,
    processing behavior).

    At the end of initialization, PlotPy's INI-based configuration is
    initialized with default styles for plots, results, and ROI shapes.
    Subclasses can override :meth:`get_plotpy_defaults` to customize these.

    Derived applications should subclass this to add app-specific options:

    .. code-block:: python

        class MyAppOptions(SigimaXOptions):
            ENV_VAR = "MYAPP_OPTIONS_JSON"
            APP_NAME = "MyApp"
            CONF_VERSION = "1.0.0"

            def __init__(self):
                super().__init__()
                self.my_option = TypedOptionField(
                    self, "my_option", default=True,
                    expected_type=bool,
                    description="My app-specific option",
                )

        options = MyAppOptions()
    """

    #: Configuration version string (override in subclass if needed)
    CONF_VERSION = "1.0.0"

    def __init__(self) -> None:
        super().__init__()

        # ===================================================================
        # Derivated application info — Name, version, description, URLs
        # ===================================================================

        self.app_name = TypedOptionField(
            self,
            "app_name",
            default="SigimaX",
            expected_type=str,
            description="Application name.",
        )
        self.app_version = TypedOptionField(
            self,
            "app_version",
            default="0.1.0",
            expected_type=str,
            description="Application version.",
        )
        self.app_logo_path = TypedOptionField(
            self,
            "app_logo_path",
            default="",
            expected_type=str,
            description="Path to the application logo.",
        )
        self.app_desc = TypedOptionField(
            self,
            "app_desc",
            default="",
            expected_type=str,
            description="Application description.",
        )
        self.app_local_doc_path = TypedOptionField(
            self,
            "app_local_doc_path",
            default="",
            expected_type=str,
            description="Path pattern to a local PDF documentation file. "
            "Use '{lang}' as a placeholder for the locale prefix "
            "(e.g. 'data/doc/MyApp_{lang}.pdf'). "
            "If empty, no local PDF menu item is shown.",
        )
        self.app_docurl = TypedOptionField(
            self,
            "app_docurl",
            default="",
            expected_type=str,
            description="URL to the application documentation.",
        )
        self.app_homeurl = TypedOptionField(
            self,
            "app_homeurl",
            default="",
            expected_type=str,
            description="URL to the application homepage.",
        )
        self.app_supporturl = TypedOptionField(
            self,
            "app_supporturl",
            default="",
            expected_type=str,
            description="URL to the application support/contact page.",
        )
        self.app_developer = TypedOptionField(
            self,
            "app_developer",
            default="",
            expected_type=str,
            description="Developer or organization name shown in the About dialog.",
        )
        self.app_copyright = TypedOptionField(
            self,
            "app_copyright",
            default="",
            expected_type=str,
            description="Copyright notice shown in the About dialog "
            "(e.g. '2023 My Organization').",
        )
        self.splash_image_path = TypedOptionField(
            self,
            "splash_image_path",
            default="",
            expected_type=str,
            description="Path to the splash screen image (PNG, SVG, etc.). "
            "If empty, no splash screen is shown.",
        )
        self.splash_show_progress = TypedOptionField(
            self,
            "splash_show_progress",
            default=True,
            expected_type=bool,
            description="If True, display progress messages on the splash screen "
            "during application startup.",
        )

        # ===================================================================
        # Main options — Application-level settings
        # ===================================================================

        self.color_mode = EnumOptionField(
            self,
            "color_mode",
            category="main",
            default="auto",
            choices=["auto", "dark", "light"],
            description="Application color mode (auto, dark, or light).",
        )
        self.datetime_format = TypedOptionField(
            self,
            "datetime_format",
            default="%d/%m/%Y - %H:%M:%S",
            expected_type=str,
            description="Application datetime format.",
        )

        # ===================================================================
        # Log and Console state
        # ===================================================================

        self.traceback_log_path = TypedOptionField(
            self,
            "traceback_log_path",
            category="main",
            default=f".{self.app_name.get()}_traceback.log",
            expected_type=str,
            description="Path to the traceback log file (relative to config dir).",
        )
        self.traceback_log_available = TypedOptionField(
            self,
            "traceback_log_available",
            category="main",
            default=False,
            expected_type=bool,
            description="Whether a traceback log file is currently available.",
        )
        self.faulthandler_enabled = TypedOptionField(
            self,
            "faulthandler_enabled",
            category="main",
            default=True,
            expected_type=bool,
            description="If True, enable Python faulthandler for crash reporting.",
        )
        self.faulthandler_log_path = TypedOptionField(
            self,
            "faulthandler_log_path",
            category="main",
            default=f".{self.app_name.get()}_faulthandler.log",
            expected_type=str,
            description="Path to the faulthandler log file (relative to config dir).",
        )
        self.faulthandler_log_available = TypedOptionField(
            self,
            "faulthandler_log_available",
            category="main",
            default=False,
            expected_type=bool,
            description="Whether a faulthandler log file is currently available.",
        )

        # ===================================================================
        # Other Application options
        # ===================================================================

        self.available_memory_threshold = TypedOptionField(
            self,
            "available_memory_threshold",
            category="main",
            default=500,
            expected_type=int,
            description=(
                "Available memory threshold in MB. A warning is shown "
                "when available memory drops below this value."
            ),
        )
        self.ignore_warnings = TypedOptionField(
            self,
            "ignore_warnings",
            category="proc",
            default=False,
            expected_type=bool,
            description=("If True, suppress Python warnings during computations."),
        )

        # ===================================================================
        # Window state — Persisted UI geometry
        # ===================================================================

        self.window_maximized = TypedOptionField(
            self,
            "window_maximized",
            category="main",
            default=False,
            expected_type=bool,
            description="Whether the main window was maximized on last close.",
        )
        self.window_position = TupleOptionField(
            self,
            "window_position",
            category="main",
            default=None,
            description="Main window position as (x, y) tuple, or None.",
        )
        self.window_size = TupleOptionField(
            self,
            "window_size",
            category="main",
            default=None,
            description="Main window size as (width, height) tuple, or None.",
        )
        self.window_state = TypedOptionField(
            self,
            "window_state",
            category="main",
            default="",
            expected_type=str,
            description=(
                "Main window state (hex-encoded QByteArray) for restoring "
                "dock widget positions and toolbar layout."
            ),
        )
        self.base_dir = TypedOptionField(
            self,
            "base_dir",
            category="main",
            default="",
            expected_type=str,
            description="Base working directory for file dialogs.",
        )

        # ===================================================================
        # Console options — Embedded console settings
        # ===================================================================

        self.console_enabled = TypedOptionField(
            self,
            "console_enabled",
            category="console",
            default=True,
            expected_type=bool,
            description="If True, show the embedded Python console.",
        )
        self.show_console_on_error = TypedOptionField(
            self,
            "show_console_on_error",
            category="console",
            default=False,
            expected_type=bool,
            description=(
                "If True, automatically show the console when an error occurs."
            ),
        )
        self.console_max_line_count = TypedOptionField(
            self,
            "console_max_line_count",
            category="console",
            default=5000,
            expected_type=int,
            description="Maximum number of lines to keep in the console output.",
        )
        self.external_editor_path = TypedOptionField(
            self,
            "external_editor_path",
            category="console",
            default="code",
            expected_type=str,
            description=(
                "Path to the external editor executable (e.g., 'code' for VS Code)."
            ),
        )
        self.external_editor_args = TypedOptionField(
            self,
            "external_editor_args",
            category="console",
            default="-g {path}:{line_number}",
            expected_type=str,
            description=(
                "Command-line arguments template for the external editor. "
                "Supports {path} and {line_number} placeholders."
            ),
        )

        # ===================================================================
        # I/O options — File import/export settings
        # ===================================================================

        self.h5_clear_workspace = TypedOptionField(
            self,
            "h5_clear_workspace",
            category="io",
            default=True,
            expected_type=bool,
            description=(
                "If True, clear the workspace before loading an HDF5 file "
                "(avoids UUID conflicts)."
            ),
        )
        self.h5_clear_workspace_ask = TypedOptionField(
            self,
            "h5_clear_workspace_ask",
            category="io",
            default=True,
            expected_type=bool,
            description=(
                "If True, ask user for confirmation before clearing workspace "
                "when loading an HDF5 file."
            ),
        )
        self.h5_fullpath_in_title = TypedOptionField(
            self,
            "h5_fullpath_in_title",
            category="io",
            default=False,
            expected_type=bool,
            description=(
                "If True, use full HDF5 dataset path in signal/image title. "
                "If False, use only the dataset name."
            ),
        )
        self.h5_fname_in_title = TypedOptionField(
            self,
            "h5_fname_in_title",
            category="io",
            default=True,
            expected_type=bool,
            description=("If True, include the HDF5 file name in signal/image title."),
        )
        self.imageio_formats = ImageIOOptionField(
            self,
            "imageio_formats",
            category="io",
            default=(),
            description="Supported ImageIO file formats.",
        )

        # ===================================================================
        # View options — Plot and visualization defaults
        # ===================================================================

        self.plot_toolbar_position = EnumOptionField(
            self,
            "plot_toolbar_position",
            category="view",
            default="left",
            choices=["top", "bottom", "left", "right"],
            description="Position of the plot toolbar.",
        )
        self.plot_dock_location = EnumOptionField(
            self,
            "plot_dock_location",
            category="view",
            default="right",
            choices=["top", "bottom", "left", "right"],
            description="Default dock area for plot widgets "
            "(top, bottom, left, or right).",
        )
        self.watermark_image_path = TypedOptionField(
            self,
            "watermark_image_path",
            category="view",
            default="",
            expected_type=str,
            description="Path to the watermark image displayed on empty plots. "
            "If empty, no watermark is shown.",
        )

        self.sig_format = TypedOptionField(
            self,
            "sig_format",
            category="view",
            default="",
            expected_type=str,
            description="Format string for signal shape legends.",
        )
        self.ima_format = TypedOptionField(
            self,
            "ima_format",
            category="view",
            default="",
            expected_type=str,
            description="Format string for image shape legends.",
        )
        self.show_label = TypedOptionField(
            self,
            "show_label",
            category="view",
            default=False,
            expected_type=bool,
            description="If True, show labels on plot items.",
        )
        self.sig_linewidth = TypedOptionField(
            self,
            "sig_linewidth",
            category="view",
            default=1.0,
            expected_type=float,
            description="Default line width for signal curves.",
        )
        self.sig_linewidth_perfs_threshold = TypedOptionField(
            self,
            "sig_linewidth_perfs_threshold",
            category="view",
            default=1000,
            expected_type=int,
            description=(
                "Number of curves above which line width is forced to 1 "
                "for performance reasons."
            ),
        )
        self.sig_autodownsampling = TypedOptionField(
            self,
            "sig_autodownsampling",
            category="view",
            default=True,
            expected_type=bool,
            description=(
                "If True, automatically downsample signals with many points "
                "for faster rendering."
            ),
        )
        self.sig_autodownsampling_maxpoints = TypedOptionField(
            self,
            "sig_autodownsampling_maxpoints",
            category="view",
            default=100000,
            expected_type=int,
            description="Maximum number of points before auto-downsampling kicks in.",
        )
        self.sig_autoscale_margin_percent = TypedOptionField(
            self,
            "sig_autoscale_margin_percent",
            category="view",
            default=2.0,
            expected_type=float,
            description="Margin percentage for signal plot autoscale.",
        )
        self.ima_autoscale_margin_percent = TypedOptionField(
            self,
            "ima_autoscale_margin_percent",
            category="view",
            default=1.0,
            expected_type=float,
            description="Margin percentage for image plot autoscale.",
        )
        self.ima_eliminate_outliers = TypedOptionField(
            self,
            "ima_eliminate_outliers",
            category="view",
            default=0.1,
            expected_type=float,
            description=(
                "Percentage of outliers to eliminate from image LUT range "
                "at item creation (0.0 to disable)."
            ),
        )

        # --- Signal visualization defaults (persisted in object metadata) ---

        self.sig_def_shade = TypedOptionField(
            self,
            "sig_def_shade",
            category="view",
            default=0.0,
            expected_type=float,
            description="Default shade value for signal curves (0.0 = no shade).",
        )
        self.sig_def_curvestyle = TypedOptionField(
            self,
            "sig_def_curvestyle",
            category="view",
            default="Lines",
            expected_type=str,
            description=(
                "Default curve style for signals "
                "(e.g., 'Lines', 'Sticks', 'Steps', 'Dots')."
            ),
        )
        self.sig_def_baseline = TypedOptionField(
            self,
            "sig_def_baseline",
            category="view",
            default=0.0,
            expected_type=float,
            description="Default baseline value for signal curves.",
        )

        # --- Image visualization defaults (persisted in object metadata) ---

        self.ima_def_colormap = TypedOptionField(
            self,
            "ima_def_colormap",
            category="view",
            default="viridis",
            expected_type=str,
            description="Default colormap for images (e.g., 'viridis', 'gray').",
        )
        self.ima_def_invert_colormap = TypedOptionField(
            self,
            "ima_def_invert_colormap",
            category="view",
            default=False,
            expected_type=bool,
            description="If True, invert the default colormap.",
        )
        self.ima_def_interpolation = TypedOptionField(
            self,
            "ima_def_interpolation",
            category="view",
            default=5,
            expected_type=int,
            description="Default interpolation mode for images (integer index).",
        )
        self.ima_def_alpha = TypedOptionField(
            self,
            "ima_def_alpha",
            category="view",
            default=1.0,
            expected_type=float,
            description="Default alpha (opacity) for images (0.0 to 1.0).",
        )
        self.ima_def_alpha_function = TypedOptionField(
            self,
            "ima_def_alpha_function",
            category="view",
            default=0,
            expected_type=int,
            description=(
                "Default alpha function for images (LUTAlpha enum value). "
                "0 = NONE (uniform alpha)."
            ),
        )
        self.ima_def_keep_lut_range = TypedOptionField(
            self,
            "ima_def_keep_lut_range",
            category="view",
            default=False,
            expected_type=bool,
            description=(
                "If True, keep the LUT range when switching between images "
                "instead of auto-scaling."
            ),
        )

        # ===================================================================
        # Processing options — Computation behavior
        # ===================================================================

        self.operation_mode = EnumOptionField(
            self,
            "operation_mode",
            category="proc",
            default="single",
            choices=["single", "pairwise"],
            description=(
                "Operation mode for multi-selection computations. "
                "'single': one operand shared, 'pairwise': paired operations."
            ),
        )
        self.extract_roi_singleobj = TypedOptionField(
            self,
            "extract_roi_singleobj",
            category="proc",
            default=False,
            expected_type=bool,
            description=(
                "If True, extract all ROIs into a single object. "
                "If False, create one object per ROI."
            ),
        )
        self.keep_results = TypedOptionField(
            self,
            "keep_results",
            category="proc",
            default=False,
            expected_type=bool,
            description=(
                "If True, keep analysis results after processing. "
                "Warning: results may become invalid after transformations."
            ),
        )
        self.show_result_dialog = TypedOptionField(
            self,
            "show_result_dialog",
            category="proc",
            default=True,
            expected_type=bool,
            description=(
                "If True, systematically show a result dialog after "
                "analysis computations."
            ),
        )
        self.use_signal_bounds = TypedOptionField(
            self,
            "use_signal_bounds",
            category="proc",
            default=False,
            expected_type=bool,
            description=(
                "If True, use xmin and xmax bounds from the current signal "
                "when creating a new signal."
            ),
        )
        self.use_image_dims = TypedOptionField(
            self,
            "use_image_dims",
            category="proc",
            default=True,
            expected_type=bool,
            description=(
                "If True, use dimensions from the current image when "
                "creating a new image."
            ),
        )
        self.fft_shift_enabled = TypedOptionField(
            self,
            "fft_shift_enabled",
            category="proc",
            default=True,
            expected_type=bool,
            description=(
                "If True, apply FFT shift to center the zero-frequency "
                "component. Synced with sigima.config.options."
            ),
        )
        self.auto_normalize_kernel = TypedOptionField(
            self,
            "auto_normalize_kernel",
            category="proc",
            default=False,
            expected_type=bool,
            description=(
                "If True, automatically normalize convolution kernels to "
                "sum to 1.0 before convolution. "
                "Synced with sigima.config.options."
            ),
        )
        self.xarray_compat_behavior = EnumOptionField(
            self,
            "xarray_compat_behavior",
            category="proc",
            default="ask",
            choices=["ask", "interpolate"],
            description=(
                "Behavior when X-arrays are incompatible in multi-signal "
                "operations. 'ask': prompt user, 'interpolate': auto-interpolate."
            ),
        )

        # ===================================================================
        # Initialize PlotPy INI-based configuration
        # ===================================================================
        self.initialize_plotpy()
        # ===================================================================
        # Sync with sigima.config.options for shared settings (e.g., FFT shift, kernel
        # normalization)
        # ===================================================================
        self.sync_with_sigima()

        # ===================================================================
        # Capture default values for reset_to_defaults()
        # (Sigima's OptionField does not expose a .default attribute)
        # # TODO: [P3] Refactor OptionField to store the default value explicitly,
        # so we can simplify this logic in the future.
        # ===================================================================
        self._defaults = {
            name: getattr(self, name).get(sync_env=False)
            for name in vars(self)
            if isinstance(getattr(self, name), OptionField)
        }

    def reset_to_defaults(self) -> None:
        """Reset all options to their default values."""
        for name, default in self._defaults.items():
            getattr(self, name).set(default, sync_env=False)
        self.sync_env()

    # -- Option categories (INI sections and settings-UI grouping) --

    def get_option_categories(self) -> list[tuple[str, str]]:
        """Return ordered option categories as ``(id, label)`` pairs.

        The ``id`` doubles as the INI section name for derived applications and
        as the persistence/grouping key; the ``label`` is a human-readable,
        translatable title suitable for a settings dialog tab.

        Derived applications extend this by concatenating their own categories
        to the result of ``super().get_option_categories()``.

        Returns:
            Ordered list of ``(category_id, label)`` pairs.
        """
        return [
            ("main", _("General")),
            ("console", _("Console")),
            ("io", _("I/O")),
            ("proc", _("Processing")),
            ("view", _("Visualization")),
        ]

    def get_field_category(self, name: str) -> str:
        """Return the category id of an option field (empty if uncategorized).

        Args:
            name: The option field name.

        Returns:
            The category id, or an empty string if the field is uncategorized
             or unknown.
        """
        field = getattr(self, name, None)
        return getattr(field, "category", "") if field is not None else ""

    def fields_by_category(self) -> dict[str, list[str]]:
        """Return option field names grouped by category id.

        Categories are keyed in the order returned by
        :meth:`get_option_categories`; uncategorized fields are omitted.

        Returns:
            Mapping ``category_id -> [option_field_name, ...]``.
        """
        result: dict[str, list[str]] = {
            cid: [] for cid, _label in self.get_option_categories()
        }
        for name in vars(self):
            field = getattr(self, name)
            if isinstance(field, OptionField):
                category = getattr(field, "category", "")
                if category:
                    result.setdefault(category, []).append(name)
        return result

    # -- PlotPy INI-based configuration integration --

    def get_plotpy_defaults(self) -> dict[str, dict[str, Any]]:
        """Return default PlotPy configuration values.

        Override this method in subclasses to customize the PlotPy styles
        for plots, result annotations, ROI shapes, and labels.

        The returned dict has top-level keys corresponding to PlotPy
        configuration sections (``"plot"``, ``"results"``, ``"roi"``).

        Returns:
            Nested dictionary of PlotPy default settings.
        """
        return {
            "plot": {
                # Overriding default plot settings from PlotPy
                "title/font/size": 11,
                "title/font/bold": False,
                "selected_curve_symbol/marker": "Ellipse",
                "selected_curve_symbol/edgecolor": "#a0a0a4",
                "selected_curve_symbol/facecolor": MAIN_FG_COLOR,
                "selected_curve_symbol/alpha": 0.3,
                "selected_curve_symbol/size": 5,
                "marker/curve/text/textcolor": "black",
                # Cross marker style (shown when pressing Alt key on plot)
                "marker/cross/symbol/marker": "Cross",
                "marker/cross/symbol/edgecolor": MAIN_FG_COLOR,
                "marker/cross/symbol/facecolor": "#ff0000",
                "marker/cross/symbol/alpha": 1.0,
                "marker/cross/symbol/size": 8,
                "marker/cross/text/font/family": "default",
                "marker/cross/text/font/size": 8,
                "marker/cross/text/font/bold": False,
                "marker/cross/text/font/italic": False,
                "marker/cross/text/textcolor": "#000000",
                "marker/cross/text/background_color": "#ffffff",
                "marker/cross/text/background_alpha": 0.7,
                "marker/cross/line/style": "DashLine",
                "marker/cross/line/color": MARKER_LINE_COLOR,
                "marker/cross/line/width": 1.0,
                "marker/cross/markerstyle": "Cross",
                "marker/cross/spacing": 7,
                # Cursor line and symbol style
                "marker/cursor/line/style": "SolidLine",
                "marker/cursor/line/color": MARKER_LINE_COLOR,
                "marker/cursor/line/width": 1.0,
                "marker/cursor/symbol/marker": "NoSymbol",
                "marker/cursor/symbol/size": 11,
                "marker/cursor/symbol/edgecolor": MAIN_BG_COLOR,
                "marker/cursor/symbol/facecolor": "#ff9393",
                "marker/cursor/symbol/alpha": 1.0,
                "marker/cursor/sel_line/style": "SolidLine",
                "marker/cursor/sel_line/color": MARKER_LINE_COLOR,
                "marker/cursor/sel_line/width": 2.0,
                "marker/cursor/sel_symbol/marker": "NoSymbol",
                "marker/cursor/sel_symbol/size": 11,
                "marker/cursor/sel_symbol/edgecolor": MAIN_BG_COLOR,
                "marker/cursor/sel_symbol/facecolor": MARKER_LINE_COLOR,
                "marker/cursor/sel_symbol/alpha": 0.8,
                "marker/cursor/text/font/size": 9,
                "marker/cursor/text/font/family": "default",
                "marker/cursor/text/font/bold": False,
                "marker/cursor/text/font/italic": False,
                "marker/cursor/text/textcolor": MARKER_TEXT_COLOR,
                "marker/cursor/text/background_color": "#ffffff",
                "marker/cursor/text/background_alpha": 0.7,
                "marker/cursor/sel_text/font/size": 9,
                "marker/cursor/sel_text/font/family": "default",
                "marker/cursor/sel_text/font/bold": False,
                "marker/cursor/sel_text/font/italic": False,
                "marker/cursor/sel_text/textcolor": MARKER_TEXT_COLOR,
                "marker/cursor/sel_text/background_color": "#ffffff",
                "marker/cursor/sel_text/background_alpha": 0.7,
                # Default annotation text style for segments
                "shape/segment/line/style": "SolidLine",
                "shape/segment/line/color": "#00ff55",
                "shape/segment/line/width": 1.0,
                "shape/segment/sel_line/style": "SolidLine",
                "shape/segment/sel_line/color": "#00ff55",
                "shape/segment/sel_line/width": 2.0,
                "shape/segment/fill/style": "NoBrush",
                "shape/segment/sel_fill/style": "NoBrush",
                "shape/segment/symbol/marker": "XCross",
                "shape/segment/symbol/size": 9,
                "shape/segment/symbol/edgecolor": "#00ff55",
                "shape/segment/symbol/facecolor": "#00ff55",
                "shape/segment/symbol/alpha": 1.0,
                "shape/segment/sel_symbol/marker": "XCross",
                "shape/segment/sel_symbol/size": 12,
                "shape/segment/sel_symbol/edgecolor": "#00ff55",
                "shape/segment/sel_symbol/facecolor": "#00ff55",
                "shape/segment/sel_symbol/alpha": 0.7,
                # Default style for drag shapes (global annotations style)
                "shape/drag/line/style": "SolidLine",
                "shape/drag/line/color": "#00ff55",
                "shape/drag/line/width": 1.0,
                "shape/drag/fill/style": "SolidPattern",
                "shape/drag/fill/color": MAIN_BG_COLOR,
                "shape/drag/fill/alpha": 0.1,
                "shape/drag/symbol/marker": "Rect",
                "shape/drag/symbol/size": 3,
                "shape/drag/symbol/edgecolor": "#00ff55",
                "shape/drag/symbol/facecolor": "#00ff55",
                "shape/drag/symbol/alpha": 1.0,
                "shape/drag/sel_line/style": "SolidLine",
                "shape/drag/sel_line/color": "#00ff55",
                "shape/drag/sel_line/width": 2.0,
                "shape/drag/sel_fill/style": "SolidPattern",
                "shape/drag/sel_fill/color": MAIN_BG_COLOR,
                "shape/drag/sel_fill/alpha": 0.1,
                "shape/drag/sel_symbol/marker": "Rect",
                "shape/drag/sel_symbol/size": 7,
                "shape/drag/sel_symbol/edgecolor": "#00ff55",
                "shape/drag/sel_symbol/facecolor": "#00ff00",
                "shape/drag/sel_symbol/alpha": 0.7,
            },
            "results": {
                # Annotated shape style for result shapes:
                #   Signals:
                "s/annotation/line/style": "SolidLine",
                "s/annotation/line/color": "#00aa00",
                "s/annotation/line/width": 2,
                "s/annotation/fill/style": "NoBrush",
                "s/annotation/fill/color": MAIN_BG_COLOR,
                "s/annotation/fill/alpha": 0.1,
                "s/annotation/symbol/marker": "XCross",
                "s/annotation/symbol/size": 7,
                "s/annotation/symbol/edgecolor": "#00aa00",
                "s/annotation/symbol/facecolor": "#00aa00",
                "s/annotation/symbol/alpha": 1.0,
                "s/annotation/sel_line/style": "DashLine",
                "s/annotation/sel_line/color": "#00ff00",
                "s/annotation/sel_line/width": 1,
                "s/annotation/sel_fill/style": "SolidPattern",
                "s/annotation/sel_fill/color": MAIN_BG_COLOR,
                "s/annotation/sel_fill/alpha": 0.1,
                "s/annotation/sel_symbol/marker": "Rect",
                "s/annotation/sel_symbol/size": 9,
                "s/annotation/sel_symbol/edgecolor": "#00aa00",
                "s/annotation/sel_symbol/facecolor": "#00ff00",
                "s/annotation/sel_symbol/alpha": 0.7,
                #   Images:
                "i/annotation/line/style": "SolidLine",
                "i/annotation/line/color": "#ffff00",
                "i/annotation/line/width": 2,
                "i/annotation/fill/style": "SolidPattern",
                "i/annotation/fill/color": MAIN_BG_COLOR,
                "i/annotation/fill/alpha": 0.1,
                "i/annotation/symbol/marker": "Rect",
                "i/annotation/symbol/size": 3,
                "i/annotation/symbol/edgecolor": "#ffff00",
                "i/annotation/symbol/facecolor": "#ffff00",
                "i/annotation/symbol/alpha": 1.0,
                "i/annotation/sel_line/style": "SolidLine",
                "i/annotation/sel_line/color": "#00ff00",
                "i/annotation/sel_line/width": 2,
                "i/annotation/sel_fill/style": "SolidPattern",
                "i/annotation/sel_fill/color": MAIN_BG_COLOR,
                "i/annotation/sel_fill/alpha": 0.1,
                "i/annotation/sel_symbol/marker": "Rect",
                "i/annotation/sel_symbol/size": 9,
                "i/annotation/sel_symbol/edgecolor": "#00aa00",
                "i/annotation/sel_symbol/facecolor": "#00ff00",
                "i/annotation/sel_symbol/alpha": 0.7,
                # Marker styles for results:
                #   Signals:
                "s/marker/cursor/line/style": "DashLine",
                "s/marker/cursor/line/color": MARKER_LINE_COLOR,
                "s/marker/cursor/line/width": 1.0,
                "s/marker/cursor/symbol/marker": "Ellipse",
                "s/marker/cursor/symbol/size": 11,
                "s/marker/cursor/symbol/edgecolor": MAIN_BG_COLOR,
                "s/marker/cursor/symbol/facecolor": MARKER_LINE_COLOR,
                "s/marker/cursor/symbol/alpha": 0.7,
                "s/marker/cursor/sel_line/style": "DashLine",
                "s/marker/cursor/sel_line/color": MARKER_LINE_COLOR,
                "s/marker/cursor/sel_line/width": 2.0,
                "s/marker/cursor/sel_symbol/marker": "Ellipse",
                "s/marker/cursor/sel_symbol/size": 11,
                "s/marker/cursor/sel_symbol/edgecolor": MARKER_LINE_COLOR,
                "s/marker/cursor/sel_symbol/facecolor": MARKER_LINE_COLOR,
                "s/marker/cursor/sel_symbol/alpha": 0.7,
                "s/marker/cursor/text/font/size": 9,
                "s/marker/cursor/text/font/family": "default",
                "s/marker/cursor/text/font/bold": False,
                "s/marker/cursor/text/font/italic": False,
                "s/marker/cursor/text/textcolor": MARKER_TEXT_COLOR,
                "s/marker/cursor/text/background_color": "#ffffff",
                "s/marker/cursor/text/background_alpha": 0.7,
                "s/marker/cursor/sel_text/font/size": 9,
                "s/marker/cursor/sel_text/font/family": "default",
                "s/marker/cursor/sel_text/font/bold": False,
                "s/marker/cursor/sel_text/font/italic": False,
                "s/marker/cursor/sel_text/textcolor": MARKER_TEXT_COLOR,
                "s/marker/cursor/sel_text/background_color": "#ffffff",
                "s/marker/cursor/sel_text/background_alpha": 0.7,
                "s/marker/cursor/markerstyle": "Cross",
                #   Images:
                "i/marker/cursor/line/style": "DashLine",
                "i/marker/cursor/line/color": MARKER_LINE_COLOR,
                "i/marker/cursor/line/width": 1.0,
                "i/marker/cursor/symbol/marker": "Diamond",
                "i/marker/cursor/symbol/size": 11,
                "i/marker/cursor/symbol/edgecolor": MARKER_LINE_COLOR,
                "i/marker/cursor/symbol/facecolor": MARKER_LINE_COLOR,
                "i/marker/cursor/symbol/alpha": 0.7,
                "i/marker/cursor/sel_line/style": "DashLine",
                "i/marker/cursor/sel_line/color": MARKER_LINE_COLOR,
                "i/marker/cursor/sel_line/width": 2.0,
                "i/marker/cursor/sel_symbol/marker": "Diamond",
                "i/marker/cursor/sel_symbol/size": 11,
                "i/marker/cursor/sel_symbol/edgecolor": MARKER_LINE_COLOR,
                "i/marker/cursor/sel_symbol/facecolor": MARKER_LINE_COLOR,
                "i/marker/cursor/sel_symbol/alpha": 0.7,
                "i/marker/cursor/text/font/size": 9,
                "i/marker/cursor/text/font/family": "default",
                "i/marker/cursor/text/font/bold": False,
                "i/marker/cursor/text/font/italic": False,
                "i/marker/cursor/text/textcolor": MARKER_TEXT_COLOR,
                "i/marker/cursor/text/background_color": "#ffffff",
                "i/marker/cursor/text/background_alpha": 0.7,
                "i/marker/cursor/sel_text/font/size": 9,
                "i/marker/cursor/sel_text/font/family": "default",
                "i/marker/cursor/sel_text/font/bold": False,
                "i/marker/cursor/sel_text/font/italic": False,
                "i/marker/cursor/sel_text/textcolor": MARKER_TEXT_COLOR,
                "i/marker/cursor/sel_text/background_color": "#ffffff",
                "i/marker/cursor/sel_text/background_alpha": 0.7,
                "i/marker/cursor/markerstyle": "Cross",
                # Style for labels:
                "label/symbol/marker": "NoSymbol",
                "label/symbol/size": 0,
                "label/symbol/edgecolor": MAIN_BG_COLOR,
                "label/symbol/facecolor": MAIN_BG_COLOR,
                "label/border/style": "SolidLine",
                "label/border/color": "#cbcbcb",
                "label/border/width": 1,
                "label/font/size": 8,
                "label/font/family/nt": [
                    "Cascadia Code",
                    "Consolas",
                    "Courier New",
                ],
                "label/font/family/posix": "Bitstream Vera Sans Mono",
                "label/font/family/mac": "Monaco",
                "label/font/bold": False,
                "label/font/italic": False,
                "label/color": MAIN_FG_COLOR,
                "label/bgcolor": MAIN_BG_COLOR,
                "label/bgalpha": 0.8,
                "label/anchor": "TL",
                "label/xc": 10,
                "label/yc": 10,
                "label/abspos": True,
                "label/absg": "TL",
                "label/xg": 0.0,
                "label/yg": 0.0,
            },
            "roi": {
                # Signals — Editable ROI (ROI editor):
                "s/editable/fill": "#ffff00",
                "s/editable/shade": 0.10,
                "s/editable/line/style": "SolidLine",
                "s/editable/line/color": "#ffff00",
                "s/editable/line/width": 1,
                "s/editable/fill/style": "SolidPattern",
                "s/editable/fill/color": MAIN_BG_COLOR,
                "s/editable/fill/alpha": 0.1,
                "s/editable/symbol/marker": "Rect",
                "s/editable/symbol/size": 3,
                "s/editable/symbol/edgecolor": "#ffff00",
                "s/editable/symbol/facecolor": "#ffff00",
                "s/editable/symbol/alpha": 1.0,
                "s/editable/sel_line/style": "SolidLine",
                "s/editable/sel_line/color": "#00ff00",
                "s/editable/sel_line/width": 1,
                "s/editable/sel_fill/style": "SolidPattern",
                "s/editable/sel_fill/color": MAIN_BG_COLOR,
                "s/editable/sel_fill/alpha": 0.1,
                "s/editable/sel_symbol/marker": "Rect",
                "s/editable/sel_symbol/size": 9,
                "s/editable/sel_symbol/edgecolor": "#00aa00",
                "s/editable/sel_symbol/facecolor": "#00ff00",
                "s/editable/sel_symbol/alpha": 0.7,
                # Signals — Readonly ROI (plot):
                "s/readonly/line/style": "SolidLine",
                "s/readonly/line/color": ROI_LINE_COLOR,
                "s/readonly/line/width": 1,
                "s/readonly/sel_line/style": "SolidLine",
                "s/readonly/sel_line/color": ROI_SEL_LINE_COLOR,
                "s/readonly/sel_line/width": 2,
                "s/readonly/fill": ROI_LINE_COLOR,
                "s/readonly/shade": 0.10,
                "s/readonly/symbol/marker": "Ellipse",
                "s/readonly/symbol/size": 7,
                "s/readonly/symbol/edgecolor": MAIN_BG_COLOR,
                "s/readonly/symbol/facecolor": ROI_LINE_COLOR,
                "s/readonly/symbol/alpha": 1.0,
                "s/readonly/sel_symbol/marker": "Ellipse",
                "s/readonly/sel_symbol/size": 9,
                "s/readonly/sel_symbol/edgecolor": MAIN_BG_COLOR,
                "s/readonly/sel_symbol/facecolor": ROI_SEL_LINE_COLOR,
                "s/readonly/sel_symbol/alpha": 0.9,
                "s/readonly/multi/color": "#806060",
                # Images — Editable ROI (ROI editor):
                "i/editable/line/style": "SolidLine",
                "i/editable/line/color": "#ffff00",
                "i/editable/line/width": 1,
                "i/editable/fill/style": "SolidPattern",
                "i/editable/fill/color": MAIN_BG_COLOR,
                "i/editable/fill/alpha": 0.1,
                "i/editable/symbol/marker": "Rect",
                "i/editable/symbol/size": 3,
                "i/editable/symbol/edgecolor": "#ffff00",
                "i/editable/symbol/facecolor": "#ffff00",
                "i/editable/symbol/alpha": 1.0,
                "i/editable/sel_line/style": "SolidLine",
                "i/editable/sel_line/color": "#00ff00",
                "i/editable/sel_line/width": 1,
                "i/editable/sel_fill/style": "SolidPattern",
                "i/editable/sel_fill/color": MAIN_BG_COLOR,
                "i/editable/sel_fill/alpha": 0.1,
                "i/editable/sel_symbol/marker": "Rect",
                "i/editable/sel_symbol/size": 9,
                "i/editable/sel_symbol/edgecolor": "#00aa00",
                "i/editable/sel_symbol/facecolor": "#00ff00",
                "i/editable/sel_symbol/alpha": 0.7,
                # Images — Readonly ROI (plot):
                "i/readonly/line/style": "DotLine",
                "i/readonly/line/color": ROI_LINE_COLOR,
                "i/readonly/line/width": 1,
                "i/readonly/fill/style": "SolidPattern",
                "i/readonly/fill/color": MAIN_BG_COLOR,
                "i/readonly/fill/alpha": 0.1,
                "i/readonly/symbol/marker": "NoSymbol",
                "i/readonly/symbol/size": 5,
                "i/readonly/symbol/edgecolor": ROI_LINE_COLOR,
                "i/readonly/symbol/facecolor": ROI_LINE_COLOR,
                "i/readonly/symbol/alpha": 0.6,
                "i/readonly/sel_line/style": "DotLine",
                "i/readonly/sel_line/color": "#0000ff",
                "i/readonly/sel_line/width": 1,
                "i/readonly/sel_fill/style": "SolidPattern",
                "i/readonly/sel_fill/color": MAIN_BG_COLOR,
                "i/readonly/sel_fill/alpha": 0.1,
                "i/readonly/sel_symbol/marker": "Rect",
                "i/readonly/sel_symbol/size": 8,
                "i/readonly/sel_symbol/edgecolor": "#0000aa",
                "i/readonly/sel_symbol/facecolor": "#0000ff",
                "i/readonly/sel_symbol/alpha": 0.7,
            },
        }

    def initialize_plotpy(self, config_app_name: str = "", load: bool = False) -> None:
        """Initialize PlotPy's INI-based configuration.

        Applies the default styles from :meth:`get_plotpy_defaults` and
        optionally sets the application name for the PlotPy INI file.

        This method is called automatically at the end of ``__init__``.
        Subclasses can call it again with a different ``config_app_name``
        after overriding :meth:`get_plotpy_defaults`.

        Args:
            config_app_name: Application name for the PlotPy INI file
             (e.g., ``"MyApp_v1"``). If empty, PlotPy uses its own default.
            load: If True, load existing user settings from the INI file.
        """
        defaults = self.get_plotpy_defaults()
        PLOTPY_CONF.update_defaults(defaults)
        PLOTPY_CONF.set_application(
            osp.join(config_app_name, "plotpy") if config_app_name else "plotpy",
            self.CONF_VERSION,
            load=load,
        )

    def sync_with_sigima(self) -> None:
        """Synchronize relevant options with Sigima's options container.

        Call this after loading or modifying options that have Sigima counterparts
        (``fft_shift_enabled``, ``auto_normalize_kernel``, ``imageio_formats``).
        """
        sigima_options.fft_shift_enabled.set(self.fft_shift_enabled.get())
        sigima_options.auto_normalize_kernel.set(self.auto_normalize_kernel.get())
        sigima_options.imageio_formats.set(self.imageio_formats.get())

    def get_sigima_defaults(self, category: str) -> dict:
        """Get default Sigima visualization settings as a dictionary.

        Collects all options named ``{category}_def_*`` and returns them
        as a dictionary with the ``{category}_def_`` prefix stripped.

        Args:
            category: 'sig' for signal defaults, 'ima' for image defaults.

        Returns:
            Dictionary of default visualization settings.

        Example:
            >>> options.get_sigima_defaults("ima")
            {'colormap': 'viridis', 'alpha': 1.0, ...}
        """
        assert category in ("ima", "sig"), f"Expected 'ima' or 'sig', got {category!r}"
        prefix = f"{category}_def_"
        result = {}
        for name in vars(self):
            if name.startswith(prefix):
                opt = getattr(self, name)
                if isinstance(opt, OptionField):
                    value = opt.get(sync_env=False)
                    if value is not None:
                        result[name[len(prefix) :]] = value
        return result

    def set_sigima_defaults(self, category: str, defaults: dict) -> None:
        """Set default Sigima visualization settings from a dictionary.

        Args:
            category: 'sig' for signal defaults, 'ima' for image defaults.
            defaults: Dictionary of setting names (without prefix) to values.

        Example:
            >>> options.set_sigima_defaults("ima", {"colormap": "gray"})
        """
        assert category in ("ima", "sig"), f"Expected 'ima' or 'sig', got {category!r}"
        prefix = f"{category}_def_"
        for key, value in defaults.items():
            attr_name = f"{prefix}{key}"
            if hasattr(self, attr_name):
                opt = getattr(self, attr_name)
                if isinstance(opt, OptionField):
                    opt.set(value)


#: Global instance of SigimaX options.
#: Derived applications should create their own instance of their subclass.
CONF = SigimaXOptions()

#: Names of every option defined by the SigimaX base configuration. A derived
#: application may add options and override values, but it may **not** remove a
#: base option (doing so would break SigimaX modules that read it at runtime).
_BASE_OPTION_NAMES: frozenset[str] = frozenset(
    name for name in vars(CONF) if isinstance(getattr(CONF, name), OptionField)
)

#: The currently active options container. Defaults to the SigimaX base
#: configuration; a derived application installs its own container via
#: :func:`set_conf`. All SigimaX modules read the active container through
#: :func:`get_conf` (never by binding ``CONF`` directly), so that a derived
#: application's configuration is honoured transparently regardless of import
#: order.
_active_conf: AppOptionsContainer = CONF


def get_conf() -> AppOptionsContainer:
    """Return the currently active options container.

    SigimaX modules (and derived-application code) should call this at runtime
    to read configuration options, e.g. ``get_conf().color_mode.get()``.

    Returns:
        The active options container (the SigimaX base by default, or the
         container installed by a derived application via :func:`set_conf`).
    """
    return _active_conf


def set_conf(container: AppOptionsContainer) -> None:
    """Install a derived application's options container as the active one.

    The container must define **every** SigimaX base option (base options
    cannot be removed) so that SigimaX modules never fail a runtime lookup. It
    may freely add new options and override default values.

    Args:
        container: The options container to activate (typically a subclass of
         :class:`SigimaXOptions`).

    Raises:
        ValueError: If the container is missing one or more base SigimaX options.
    """
    container_names = {
        name
        for name in vars(container)
        if isinstance(getattr(container, name), OptionField)
    }
    missing = _BASE_OPTION_NAMES - container_names
    if missing:
        raise ValueError(
            "Cannot install options container: the following base SigimaX "
            f"options are missing (base options cannot be removed): {sorted(missing)}"
        )
    global _active_conf  # pylint: disable=global-statement
    _active_conf = container


def reset_conf() -> None:
    """Restore the SigimaX base configuration as the active container.

    Mainly useful for tests that install a derived container and need to revert.
    """
    global _active_conf  # pylint: disable=global-statement
    _active_conf = CONF
