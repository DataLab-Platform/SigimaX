# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests (:mod:`sigimax.tests`)
------------------------

The SigimaX test suite is based on the `pytest <https://pytest.org>`_ framework.

The test suite modules are organized in subpackages according to their purpose.
The following subpackages are available:
"""

from __future__ import annotations

import os
import os.path as osp
import sys
from contextlib import contextmanager
from typing import Generator

from guidata.guitest import run_testlauncher
from sigima.tests import helpers

import sigimax
from sigimax.config import MOD_NAME
from sigimax.gui.main import SGMXMainWindow
from sigimax.utils import qthelpers as qth

# Add test data files and folders for the SigimaX module:
helpers.add_test_module_path(MOD_NAME, osp.join("data", "tests"))


@contextmanager
def sigimax_test_app_context(
    size: tuple[int, int] = None,
    maximized: bool = False,
    save: bool = False,
    console: bool | None = None,
    exec_loop: bool = True,
) -> Generator[SGMXMainWindow, None, None]:
    """Context manager handling SigimaX mainwindow creation and Qt event loop
    with optional HDF5 file save and other options for testing purposes

    Args:
        size: mainwindow size (default: (950, 600))
        maximized: whether to maximize mainwindow (default: False)
        save: whether to save HDF5 file (default: False)
        console: whether to show console (default: None)
        exec_loop: whether to execute Qt event loop (default: True)
    """
    if size is None:
        size = 1200, 700
    with qth.sigimax_app_context(exec_loop=exec_loop):
        win: SGMXMainWindow | None = None
        try:
            win = SGMXMainWindow(console=console)
            if maximized:
                win.showMaximized()
            else:
                width, height = size
                win.resize(width, height)
                win.showNormal()
            win.show()
            win.setObjectName(helpers.get_default_test_name())  # screenshot name
            yield win
        finally:
            if save:
                path = helpers.get_output_data_path("h5")
                try:
                    os.remove(path)
                    win.save_to_h5_file(path)
                except (FileNotFoundError, PermissionError):
                    pass
            has_exception_occurred = sys.exc_info()[0] is not None
            if not exec_loop or has_exception_occurred and win is not None:
                # Closing main window properly
                win.set_modified(False)
                win.close()


def run() -> None:
    """Run SigimaX test launcher"""
    run_testlauncher(sigimax)


if __name__ == "__main__":
    run()
