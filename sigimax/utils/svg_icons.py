# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""SVG icon constants and helper for remote-control widgets."""

from __future__ import annotations

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtSvg as QS

__all__ = ["GROUP", "IMAGE", "SIGNAL", "svgtext_to_icon"]

SIGNAL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<polyline points="4,32 20,32 26,12 34,52 40,32 60,32"
 fill="none" stroke="#1f77b4" stroke-width="4" stroke-linejoin="round"
 stroke-linecap="round"/>
</svg>"""

IMAGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect x="6" y="10" width="52" height="44" rx="3" fill="none"
 stroke="#1f77b4" stroke-width="4"/>
<circle cx="22" cy="26" r="6" fill="#1f77b4"/>
<polyline points="6,46 22,32 34,42 44,28 58,40" fill="none"
 stroke="#1f77b4" stroke-width="4" stroke-linejoin="round"
 stroke-linecap="round"/>
</svg>"""

GROUP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<path d="M4 50 V22 a3 3 0 0 1 3 -3 h16 l6 8 h28 a3 3 0 0 1 3 3 v20 a3 3 0 0 1
 -3 3 H7 a3 3 0 0 1 -3 -3 z" fill="#f2b13c" stroke="#8a6a1f" stroke-width="2"/>
</svg>"""


def svgtext_to_icon(text: str) -> QG.QIcon:
    """Convert SVG text to a QIcon.

    Args:
        text: SVG text

    Returns:
        Icon rendered from the SVG text
    """
    svg_bytes = QC.QByteArray(text.encode("utf-8"))
    renderer = QS.QSvgRenderer(svg_bytes)  # pylint: disable=no-member
    pixmap = QG.QPixmap(64, 64)
    pixmap.fill(QC.Qt.transparent)
    painter = QG.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QG.QIcon(pixmap)
