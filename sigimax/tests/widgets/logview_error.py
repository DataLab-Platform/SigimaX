# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Log viewer test: raise an exception and create a seg fault in derivated SigimaX App
"""

# guitest: skip

from guidata.qthelpers import qt_app_context

from sigimax.env import execenv
from sigimax.gui.main import SGMXMainWindow


def error():
    """Raise an exception and create a seg fault in derivated SigimaX App"""
    with execenv.context(unattended=True):
        with qt_app_context(exec_loop=True):
            win = SGMXMainWindow()
            win.test_segfault_error()


if __name__ == "__main__":
    error()
