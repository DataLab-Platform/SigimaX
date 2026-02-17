# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX configuration module
----------------------------

This module handles `SigimaX` configuration (options, images and icons).
"""

from __future__ import annotations

import os
import os.path as osp
import sys
from typing import Literal

from guidata import configtools
from plotpy.config import CONF as PLOTPY_CONF
from plotpy.config import MAIN_BG_COLOR, MAIN_FG_COLOR
from plotpy.constants import LUTAlpha
from sigima.config import options as sigima_options
from sigima.proc.title_formatting import (
    PlaceholderTitleFormatter,
    set_default_title_formatter,
)

from sigimax.utils import conf

# Configure Sigima to use placeholder title formatting
set_default_title_formatter(PlaceholderTitleFormatter())

CONF_VERSION = "1.0.0"

APP_NAME = "SigimaX"
MOD_NAME = "sigimax"


_ = configtools.get_translation(MOD_NAME)

APP_DESC = _("""SigimaX is a GUI library working with Sigima and PlotPyStack.
             It provides a App configuration system, a generic MainWindow class and a
             set of widgets to build applications on top of Sigima and PlotPyStack.""")
APP_PATH = osp.dirname(__file__)

DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true")
if DEBUG:
    print("*** DEBUG mode *** [Reset configuration file, do not redirect std I/O]")

TEST_SEGFAULT_ERROR = len(os.environ.get("TEST_SEGFAULT_ERROR", "")) > 0
if TEST_SEGFAULT_ERROR:
    print('*** TEST_SEGFAULT_ERROR mode *** [Enabling test action in "?" menu]')
DATETIME_FORMAT = "%d/%m/%Y - %H:%M:%S"

# TODO : handle data data, icon and logo generically
# configtools.add_image_module_path(MOD_NAME, osp.join("data", "logo"))
configtools.add_image_module_path(MOD_NAME, osp.join("data", "icons"))

# DATAPATH = configtools.get_module_data_path(MOD_NAME, "data")
# SHOTPATH = osp.join(
#    configtools.get_module_data_path(MOD_NAME), os.pardir, "doc", "images", "shots"
# )


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


class MainSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the main configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    color_mode = conf.EnumOption(["auto", "dark", "light"], default="auto")
    process_isolation_enabled = conf.Option()
    traceback_log_path = conf.ConfigPathOption()
    traceback_log_available = conf.Option()
    faulthandler_enabled = conf.Option()
    faulthandler_log_path = conf.ConfigPathOption()
    faulthandler_log_available = conf.Option()
    window_maximized = conf.Option()
    window_position = conf.Option()
    window_size = conf.Option()
    window_state = conf.Option()
    base_dir = conf.WorkingDirOption()
    available_memory_threshold = conf.Option()
    current_tab = conf.Option()
    ignore_warnings = conf.Option()


class ConsoleSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the console configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    console_enabled = conf.Option()
    show_console_on_error = conf.Option()
    max_line_count = conf.Option()
    external_editor_path = conf.Option()
    external_editor_args = conf.Option()


class IOSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the I/O configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    # HDF5 file format options
    # ------------------------
    # When opening an HDF5 file, ask user for confirmation if the current workspace
    # has to be cleared before loading the file:
    h5_clear_workspace = conf.Option()  # True: clear workspace, False: do not clear
    h5_clear_workspace_ask = conf.Option()  # True: ask user, False: do not ask
    # Signal or image title when importing from HDF5 file:
    # - True: use HDF5 full dataset path in signal or image title
    # - False: use HDF5 dataset name in signal or image title
    h5_fullpath_in_title = conf.Option()
    # Signal or image title when importing from HDF5 file:
    # - True: add HDF5 file name in signal or image title
    # - False: do not add HDF5 file name in signal or image title
    h5_fname_in_title = conf.Option()

    # ImageIO supported file formats:
    imageio_formats = conf.Option()

    # Dialog settings persistence (JSON-serialized datasets):
    save_to_directory_settings = conf.DataSetOption()
    add_metadata_settings = conf.DataSetOption()


class ViewSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the view configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    # Toolbar position:
    # - "top": top
    # - "bottom": bottom
    # - "left": left
    # - "right": right
    plot_toolbar_position = conf.Option()

    # String formatting for shape legends
    sig_format = conf.Option()
    ima_format = conf.Option()

    show_label = conf.Option()
    # auto_refresh = conf.Option()
    sig_linewidth = conf.Option()
    sig_linewidth_perfs_threshold = conf.Option()
    sig_autodownsampling = conf.Option()
    sig_autodownsampling_maxpoints = conf.Option()

    # Autoscale margin settings for plots (percentage values)
    sig_autoscale_margin_percent = conf.Option()
    ima_autoscale_margin_percent = conf.Option()

    # Default visualization settings at item creation
    # (e.g. see adapter's `make_item` methods in datalab/adapters_plotpy/*.py)
    ima_eliminate_outliers = conf.Option()

    # Default visualization settings, persisted in object metadata
    # (e.g. see `BaseDataPanel.update_metadata_view_settings`)
    sig_def_shade = conf.Option()
    sig_def_curvestyle = conf.Option()
    sig_def_baseline = conf.Option()
    # ⚠️ Do not add "sig_def_use_dsamp" and "sig_def_dsamp_factor" options here
    # because it would not be compatible with the auto-downsampling feature.

    # Default visualization settings, persisted in object metadata
    # (e.g. see `BaseDataPanel.update_metadata_view_settings`)
    ima_def_colormap = conf.Option()
    ima_def_invert_colormap = conf.Option()
    ima_def_interpolation = conf.Option()
    ima_def_alpha = conf.Option()
    ima_def_alpha_function = conf.Option()
    ima_def_keep_lut_range = conf.Option()

    @classmethod
    def get_def_dict(cls, category: Literal["ima", "sig"]) -> dict:
        """Get default visualization settings as a dictionary

        Args:
            category: category ("ima" or "sig", respectively for image and signal)

        Returns:
            Default visualization settings as a dictionary
        """
        assert category in ("ima", "sig")
        prefix = f"{category}_def_"
        def_dict = {}
        for attrname in dir(cls):
            if attrname.startswith(prefix):
                name = attrname[len(prefix) :]
                opt = getattr(cls, attrname)
                defval = opt.get(None)
                if defval is not None:
                    def_dict[name] = defval
        return def_dict

    @classmethod
    def set_def_dict(cls, category: Literal["ima", "sig"], def_dict: dict) -> None:
        """Set default visualization settings from a dictionary

        Args:
            category: category ("ima" or "sig", respectively for image and signal)
            def_dict: default visualization settings as a dictionary
        """
        assert category in ("ima", "sig")
        prefix = f"{category}_def_"
        for attrname in dir(cls):
            if attrname.startswith(prefix):
                name = attrname[len(prefix) :]
                opt = getattr(cls, attrname)
                if name in def_dict:
                    opt.set(def_dict[name])


# Usage (example): Conf.console.console_enabled.get(True)
class Conf(conf.Configuration, metaclass=conf.ConfMeta):
    """Class defining SigimaX configuration structure.
    Each class attribute is a section (metaclass is automatically affecting
    section names in .INI file based on class attribute names)."""

    main = MainSection()
    console = ConsoleSection()
    view = ViewSection()
    io = IOSection()


def get_old_log_fname(fname):
    """Return old log fname from current log fname"""
    return osp.splitext(fname)[0] + ".1.log"


def initialize():
    """Initialize application configuration"""
    # TODO : from import datalab -> need to be made generic
    config_app_name = ""
    Conf.initialize(config_app_name, CONF_VERSION, load=not DEBUG)

    # Set default values:
    # -------------------
    # (do not use "set" method here to avoid overwriting user settings in .INI file)
    # Setting here the default values only for the most critical options. The other
    # options default values are set when used in the application code.
    #
    # Main section
    Conf.main.color_mode.get("auto")
    Conf.main.process_isolation_enabled.get(True)
    Conf.main.traceback_log_path.get(f".{APP_NAME}_traceback.log")
    Conf.main.faulthandler_log_path.get(f".{APP_NAME}_faulthandler.log")
    Conf.main.available_memory_threshold.get(500)
    Conf.main.ignore_warnings.get(False)
    # Console section
    Conf.console.console_enabled.get(True)
    Conf.console.show_console_on_error.get(False)
    Conf.console.external_editor_path.get("code")
    Conf.console.external_editor_args.get("-g {path}:{line_number}")
    # IO section
    Conf.io.h5_clear_workspace.get(True)  # Default to avoid objects UUID reset
    Conf.io.h5_clear_workspace_ask.get(True)
    Conf.io.h5_fullpath_in_title.get(False)
    Conf.io.h5_fname_in_title.get(True)
    iofmts = Conf.io.imageio_formats.get(())
    if len(iofmts) > 0:
        sigima_options.imageio_formats.set(iofmts)  # Sync with sigima config

    # View section
    tb_pos = Conf.view.plot_toolbar_position.get("left")
    assert tb_pos in ("top", "bottom", "left", "right")
    Conf.view.sig_linewidth.get(1.0)
    Conf.view.sig_linewidth_perfs_threshold.get(1000)
    Conf.view.sig_autodownsampling.get(True)
    Conf.view.sig_autodownsampling_maxpoints.get(100000)
    Conf.view.sig_autoscale_margin_percent.get(2.0)
    Conf.view.ima_autoscale_margin_percent.get(1.0)
    Conf.view.ima_eliminate_outliers.get(0.1)
    Conf.view.sig_def_shade.get(0.0)
    Conf.view.sig_def_curvestyle.get("Lines")
    Conf.view.sig_def_baseline.get(0.0)
    Conf.view.ima_def_colormap.get("viridis")
    Conf.view.ima_def_invert_colormap.get(False)
    Conf.view.ima_def_interpolation.get(5)
    Conf.view.ima_def_alpha.get(1.0)
    Conf.view.ima_def_alpha_function.get(LUTAlpha.NONE.value)
    Conf.view.ima_def_keep_lut_range.get(False)

    # Initialize PlotPy configuration with versioned app name
    PLOTPY_CONF.set_application(
        osp.join(config_app_name, "plotpy"), CONF_VERSION, load=False
    )


def reset():
    """Reset application configuration"""
    Conf.reset()
    initialize()


initialize()

# TODO : handle these colors in a more generic way (e.g. in PlotPy configuration,
# or in a dedicated config section for shapes and annotations)
# -> config/config_plotpy.py ?
ROI_LINE_COLOR = "#5555ff"
ROI_SEL_LINE_COLOR = "#9393ff"
MARKER_LINE_COLOR = "#A11818"
MARKER_TEXT_COLOR = "#440909"

PLOTPY_DEFAULTS = {
    "plot": {
        #
        # XXX: If needed in the future, add here the default settings for PlotPy:
        # that will override the PlotPy settings.
        # That is the right way to customize the PlotPy settings for shapes and
        # annotations.
        # For example, for shapes:
        # "shape/drag/line/color": "#00ffff",
        #
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
        # Default annotation text style for segments:
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
        # Default style for drag shapes: (global annotations style)
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
        "label/font/family/nt": ["Cascadia Code", "Consolas", "Courier New"],
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
    "roi": {  # Shape style for ROI
        # Signals:
        # - Editable ROI (ROI editor):
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
        # - Readonly ROI (plot):
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
        # Images:
        # - Editable ROI (ROI editor):
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
        # - Readonly ROI (plot):
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

# PlotPy configuration will be initialized in initialize() function
PLOTPY_CONF.update_defaults(PLOTPY_DEFAULTS)
