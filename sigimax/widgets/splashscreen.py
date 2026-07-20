# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Splash screen
=============

The :mod:`sigimax.widgets.splashscreen` module provides a configurable splash
screen for SigimaX-derived applications.

Derived applications can customize the splash screen by providing a
:class:`SplashScreenConfig` instance, or by subclassing
:class:`SigimaXSplashScreen` for advanced rendering.

Basic usage::

    from sigimax.widgets.splashscreen import SplashScreenConfig, SigimaXSplashScreen

    config = SplashScreenConfig(
        image_path="path/to/splash.png",
        app_name="MyApp",
        app_version="1.0.0",
        tagline="Scientific Data Processing",
    )
    splash = SigimaXSplashScreen(config)
    splash.show()
    splash.show_message("Loading modules...")
    # ... heavy initialization ...
    splash.finish(main_window)

Factory from global configuration::

    splash = SigimaXSplashScreen.from_conf()
    if splash is not None:
        splash.show()
        # ...
        splash.finish(main_window)

.. autoclass:: SplashScreenConfig
.. autoclass:: SigimaXSplashScreen
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from guidata.configtools import get_image_file_path
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

if TYPE_CHECKING:
    pass

__all__ = [
    "SigimaXSplashScreen",
    "SplashScreenConfig",
]


@dataclasses.dataclass
class SplashScreenConfig:
    """Configuration for a splash screen.

    All fields are optional except *image_path*. When *image_path* is empty
    or ``None``, no splash screen is shown.

    Args:
        image_path: Absolute or relative path to the splash image (PNG, SVG,
         or any format supported by :class:`QPixmap`). If empty or ``None``,
         the splash screen is disabled.
        app_name: Application name overlaid on the splash image.
        app_version: Application version overlaid on the splash image.
        tagline: Optional subtitle displayed below the version.
        show_progress: If ``True``, progress messages are displayed at the
         bottom of the splash screen via :meth:`SigimaXSplashScreen.show_message`.
        text_color: Color used for overlay text (default: white).
        text_alignment: Qt alignment flags for overlay text
         (default: bottom-left).
    """

    image_path: str | None = None
    app_name: str = ""
    app_version: str = ""
    tagline: str = ""
    show_progress: bool = True
    text_color: QG.QColor = dataclasses.field(
        default_factory=lambda: QG.QColor("white")
    )
    text_alignment: QC.Qt.AlignmentFlag = dataclasses.field(
        default_factory=lambda: QC.Qt.AlignBottom | QC.Qt.AlignLeft
    )

    @property
    def is_enabled(self) -> bool:
        """Return ``True`` if the splash screen should be shown."""
        return bool(self.image_path)

    @classmethod
    def from_conf(cls) -> SplashScreenConfig:
        """Build a :class:`SplashScreenConfig` from the global
        :data:`sigimax.config.CONF` options.

        Returns:
            Configuration instance populated from global options.
        """
        # Import here to avoid circular imports
        from sigimax.config import get_conf  # pylint: disable=import-outside-toplevel

        conf = get_conf()

        return cls(
            image_path=conf.splash_image_path.get() or None,
            app_name=conf.app_name.get(),
            app_version=conf.app_version.get(),
            tagline=conf.app_desc.get(),
            show_progress=conf.splash_show_progress.get(),
        )


class SigimaXSplashScreen(QW.QSplashScreen):
    """Configurable splash screen for SigimaX-derived applications.

    Creates a :class:`QSplashScreen` from a :class:`SplashScreenConfig`.
    If the configuration specifies an application name/version, they are
    painted as overlay text on top of the splash image.

    Args:
        config: Splash screen configuration. If ``None``, a default
         configuration is built from :data:`sigimax.config.CONF`.
    """

    def __init__(self, config: SplashScreenConfig | None = None) -> None:
        self._config = config or SplashScreenConfig.from_conf()
        pixmap = self._load_pixmap()
        super().__init__(pixmap, QC.Qt.WindowStaysOnTopHint)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_message(self, message: str) -> None:
        """Display a progress message on the splash screen.

        The message is shown only if :attr:`SplashScreenConfig.show_progress`
        is ``True``.

        Args:
            message: The progress message to display.
        """
        if self._config.show_progress:
            self.showMessage(
                message,
                int(self._config.text_alignment),
                self._config.text_color,
            )
            # Process events so the message is actually painted
            QW.QApplication.processEvents()

    @classmethod
    def from_conf(cls) -> SigimaXSplashScreen | None:
        """Factory: build a splash screen from the global configuration.

        Returns:
            A :class:`SigimaXSplashScreen` instance, or ``None`` if the
            configuration does not specify a splash image.
        """
        config = SplashScreenConfig.from_conf()
        if not config.is_enabled:
            return None
        return cls(config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_pixmap(self) -> QG.QPixmap:
        """Load the splash image as a :class:`QPixmap`.

        Returns:
            The loaded pixmap. If the image cannot be loaded, a minimal
            fallback pixmap is generated.
        """
        path = self._config.image_path or ""
        pixmap = QG.QPixmap(path)
        if pixmap.isNull() and path:
            try:
                resolved_path = get_image_file_path(path, default=None)
            except RuntimeError:
                resolved_path = ""
            pixmap = QG.QPixmap(resolved_path)
        if pixmap.isNull():
            pixmap = self._create_fallback_pixmap()
        return pixmap

    def _create_fallback_pixmap(self) -> QG.QPixmap:
        """Create a minimal fallback pixmap when no image is available.

        Returns:
            A 480x280 pixmap with the application name drawn on a dark
            background.
        """
        width, height = 480, 280
        pixmap = QG.QPixmap(width, height)
        pixmap.fill(QG.QColor(40, 40, 40))

        painter = QG.QPainter(pixmap)
        painter.setPen(self._config.text_color)

        # Application name
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        name = self._config.app_name or "SigimaX"
        painter.drawText(
            QC.QRect(0, 0, width, height),
            int(QC.Qt.AlignCenter),
            name,
        )

        # Version
        if self._config.app_version:
            font.setPointSize(12)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(
                QC.QRect(0, height // 2 + 20, width, 40),
                int(QC.Qt.AlignHCenter | QC.Qt.AlignTop),
                f"v{self._config.app_version}",
            )

        painter.end()
        return pixmap
