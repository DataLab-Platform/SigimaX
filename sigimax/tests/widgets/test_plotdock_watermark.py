# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Plot watermark resource resolution tests."""

from __future__ import annotations

from unittest.mock import patch

from guidata.configtools import get_pixmap
from guidata.qthelpers import qt_app_context
from plotpy.constants import PlotType
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from sigimax.config import get_conf
from sigimax.widgets.plotdock import DockablePlotWidget


def _save_image(path, width: int, height: int, color: str) -> None:
    """Save a plain image of the specified size and color."""
    pixmap = QG.QPixmap(width, height)
    pixmap.fill(QG.QColor(color))
    assert pixmap.save(str(path))


def test_watermark_resolves_image_name(tmp_path) -> None:
    """An image name is resolved through guidata's registered image paths, and the
    ``@2x`` variant of the image is used on high-DPI displays."""
    image_path = tmp_path / "derived-watermark.png"
    loaded: list[tuple[str, QG.QPixmap]] = []

    def load_pixmap(name: str, default: str | None) -> QG.QPixmap:
        """Load the pixmap as on a high-DPI display, and record it."""
        pixmap = get_pixmap(name, default, 2.0)
        loaded.append((name, pixmap))
        return pixmap

    with qt_app_context(exec_loop=False):
        _save_image(image_path, 64, 32, "red")
        _save_image(tmp_path / "derived-watermark@2x.png", 128, 64, "blue")
        parent = QW.QWidget()
        with (
            get_conf().watermark_image_path.context("derived-watermark.png"),
            patch(
                "sigimax.widgets.plotdock.get_image_file_path",
                return_value=str(image_path),
            ) as resolve,
            patch("sigimax.widgets.plotdock.get_pixmap", side_effect=load_pixmap),
        ):
            dock = DockablePlotWidget(parent, PlotType.CURVE)

        resolve.assert_called_once_with("derived-watermark.png", default=None)
        assert [name for name, _pixmap in loaded] == [str(image_path)]
        assert not dock.watermark.pixmap().isNull()
        # The label's pixmap is not checked: with Qt 6, ``QLabel.pixmap`` does not
        # return the device pixel ratio of the pixmap passed to ``setPixmap``.
        pixmap = loaded[0][1]
        assert pixmap.devicePixelRatio() == 2.0
        assert pixmap.size() == QC.QSize(128, 64)
        assert pixmap.toImage().pixelColor(0, 0) == QG.QColor("blue")


def test_missing_watermark_resource_does_not_fail() -> None:
    """An unresolved watermark image must not prevent plot widget creation."""
    with qt_app_context(exec_loop=False):
        parent = QW.QWidget()
        with (
            get_conf().watermark_image_path.context("missing-watermark.png"),
            patch(
                "sigimax.widgets.plotdock.get_image_file_path",
                side_effect=RuntimeError("not found"),
            ),
        ):
            dock = DockablePlotWidget(parent, PlotType.CURVE)

        pixmap = dock.watermark.pixmap()
        assert pixmap is None or pixmap.isNull()
