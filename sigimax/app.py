# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Application launcher
====================

The :mod:`sigimax.app` module provides helper functions to create and run
SigimaX-derived applications with optional splash screen support.

Derived applications typically call :func:`create` (or :func:`run`) with
their own :class:`~sigimax.mainwindow.SGMXMainWindow` subclass and an
optional :class:`~sigimax.widgets.splashscreen.SplashScreenConfig`.

Basic usage::

    from sigimax.app import run
    from sigimax.widgets.splashscreen import SplashScreenConfig
    from myapp.main import MyAppMainWindow

    run(
        window_class=MyAppMainWindow,
        splash_config=SplashScreenConfig(
            image_path="myapp/data/splash.png",
            app_name="MyApp",
            app_version="1.0.0",
        ),
    )

.. autofunction:: create
.. autofunction:: run
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy import QtWidgets as QW

from sigimax.config import get_conf
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils.qthelpers import sigimax_app_context
from sigimax.widgets.splashscreen import SigimaXSplashScreen, SplashScreenConfig

if TYPE_CHECKING:
    pass


def create(
    window_class: type[SGMXMainWindow] = SGMXMainWindow,
    splash: bool = True,
    splash_config: SplashScreenConfig | None = None,
    console: bool | None = None,
    h5files: list[str] | None = None,
    size: tuple[int, int] | None = None,
) -> SGMXMainWindow:
    """Create and show a SigimaX application window.

    This is the recommended entry point for derived applications. It handles
    the splash screen lifecycle around the (potentially heavy) window
    initialization.

    Args:
        window_class: The main window class to instantiate. Defaults to
         :class:`~sigimax.mainwindow.SGMXMainWindow`.
        splash: If ``True``, show a splash screen during initialization.
        splash_config: Explicit splash screen configuration. If ``None`` and
         *splash* is ``True``, the configuration is built from
         :data:`sigimax.config.CONF`.
        console: If ``True``, enable the embedded console. ``None`` reads
         from :data:`sigimax.config.CONF`.
        h5files: Optional list of HDF5 file paths to open after startup.
        size: Optional ``(width, height)`` tuple for the window size.

    Returns:
        The initialized and visible main window instance.
    """
    splashscreen: SigimaXSplashScreen | None = None

    if splash:
        config = splash_config or SplashScreenConfig.from_conf()
        if config.is_enabled:
            splashscreen = SigimaXSplashScreen(config)
            splashscreen.show()
            splashscreen.show_message("Initializing...")
            QW.QApplication.processEvents()

    # --- Heavy initialization ---
    window = window_class(console=console)

    if splashscreen is not None:
        splashscreen.show_message("Loading workspace...")
        QW.QApplication.processEvents()

    if size is not None:
        width, height = size
        window.resize(width, height)

    if splashscreen is not None:
        splashscreen.finish(window)

    if get_conf().window_maximized.get():
        window.showMaximized()
    else:
        window.showNormal()

    if h5files is not None:
        window.open_h5_files(h5files, import_all=True)

    return window


def run(
    window_class: type[SGMXMainWindow] = SGMXMainWindow,
    splash: bool = True,
    splash_config: SplashScreenConfig | None = None,
    console: bool | None = None,
    h5files: list[str] | None = None,
    size: tuple[int, int] | None = None,
) -> None:
    """Create and run a SigimaX application with an event loop.

    Convenience wrapper around :func:`create` that manages the
    :func:`~sigimax.utils.qthelpers.sigimax_app_context` lifecycle.

    Args:
        window_class: The main window class to instantiate.
        splash: If ``True``, show a splash screen during initialization.
        splash_config: Explicit splash screen configuration.
        console: If ``True``, enable the embedded console.
        h5files: Optional list of HDF5 file paths to open.
        size: Optional ``(width, height)`` tuple for the window size.
    """
    with sigimax_app_context(exec_loop=True):
        window = create(
            window_class=window_class,
            splash=splash,
            splash_config=splash_config,
            console=console,
            h5files=h5files,
            size=size,
        )
        QW.QApplication.processEvents()
        window.execute_post_show_actions()
