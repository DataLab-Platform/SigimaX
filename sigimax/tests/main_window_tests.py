# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Application test for main window
--------------------------------

Testing the features of the main window of the application that are not
covered by other tests.
"""

# guitest: show

from sigimax.tests import sigimax_test_app_context


def test_main_app():
    """Main window test"""
    with sigimax_test_app_context(console=False) as win:
        print("Main window test")
        win.activateWindow()


if __name__ == "__main__":
    test_main_app()
