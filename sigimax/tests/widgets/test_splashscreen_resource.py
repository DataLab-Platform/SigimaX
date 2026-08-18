# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Splash-screen resource resolution tests."""

from __future__ import annotations

from unittest.mock import patch

from qtpy import QtGui as QG

from sigimax.widgets.splashscreen import SigimaXSplashScreen, SplashScreenConfig


def test_splash_resolves_image_basename(tmp_path) -> None:
    """A basename may be resolved through guidata's registered image paths."""
    image_path = tmp_path / "derived-splash.png"
    pixmap = QG.QPixmap(64, 32)
    pixmap.fill(QG.QColor("red"))
    assert pixmap.save(str(image_path))

    config = SplashScreenConfig(
        image_path="derived-splash.png",
        show_progress=False,
    )
    with patch(
        "sigimax.widgets.splashscreen.get_image_file_path",
        return_value=str(image_path),
    ):
        splash = SigimaXSplashScreen(config)

    assert splash.pixmap().size() == pixmap.size()
    splash.close()


def test_missing_splash_resource_uses_fallback() -> None:
    """An unresolved configured image must not prevent application startup."""
    config = SplashScreenConfig(
        image_path="missing-derived-splash.png",
        app_name="DerivedApp",
    )
    with patch(
        "sigimax.widgets.splashscreen.get_image_file_path",
        side_effect=RuntimeError("not found"),
    ):
        splash = SigimaXSplashScreen(config)

    assert not splash.pixmap().isNull()
    assert splash.pixmap().size().width() == 480
    assert splash.pixmap().size().height() == 280
    splash.close()


def test_progress_message_may_be_disabled() -> None:
    """Derived apps may preserve an image-only splash without messages."""
    config = SplashScreenConfig(image_path=None, show_progress=False)
    splash = SigimaXSplashScreen(config)
    with patch.object(splash, "showMessage") as show_message:
        splash.show_message("Initializing...")

    show_message.assert_not_called()
    splash.close()
