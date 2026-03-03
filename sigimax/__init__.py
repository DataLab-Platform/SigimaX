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

from sigimax.app import create, run
from sigimax.gui.main import SGMXMainWindow

__version__ = "0.0.1.dev0"
__docurl__ = "https://sigimax.readthedocs.io/"
__homeurl__ = "https://github.com/DataLab-Platform/SigimaX"
__supporturl__ = "https://github.com/DataLab-Platform/SigimaX/issues/new/choose"

# --- Important note: DATAPATH and LOCALEPATH are used by guidata.configtools
# ---                 to retrieve data and translation files paths
#
# Dear (Debian, RPM, ...) package makers, please feel free to customize the
# following path to module's data (images) and translations:
DATAPATH = LOCALEPATH = ""
