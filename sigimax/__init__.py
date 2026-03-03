# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
SigimaX
=======

SigimaX is a generic app components library based on Python
scientific libraries (such as NumPy, SciPy or scikit-image) and Qt graphical
user interfaces (thanks to `PlotPyStack`_ libraries).

It helps building scientific computing applications by providing a set of GUI modules.

.. _PlotPyStack: https://github.com/PlotPyStack
"""

__all__ = [
    "SGMXMainWindow",
    "create",
    "run",
]

from sigimax._metadata import (  # noqa: F401
    __docurl__,
    __homeurl__,
    __supporturl__,
    __version__,
)
from sigimax.app import create, run
from sigimax.gui.main import SGMXMainWindow

# --- Important note: DATAPATH and LOCALEPATH are used by guidata.configtools
# ---                 to retrieve data and translation files paths
#
# Dear (Debian, RPM, ...) package makers, please feel free to customize the
# following path to module's data (images) and translations:
DATAPATH = LOCALEPATH = ""
