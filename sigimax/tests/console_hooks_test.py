# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Console hooks functional test
-------------------------------

Verify that:

1. The base :class:`SGMXMainWindow` creates a working console with a generic
   namespace (``win``, ``np``, etc.) and a generic welcome message.
2. A derived application can override :meth:`_get_console_namespace` and
   :meth:`_get_console_message` to inject custom variables and a custom
   welcome message.
"""

# guitest: show

from __future__ import annotations

import numpy as np

from sigimax.config import CONF as Conf
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth

# =============================================================================
# Derived window with custom console namespace
# =============================================================================


class CustomConsoleWindow(SGMXMainWindow):
    """Derived window that adds domain-specific variables to the console."""

    CUSTOM_DATA = np.array([1, 2, 3, 4, 5])

    def __init__(self) -> None:
        Conf.app_name.set("ConsoleHookTest")
        Conf.app_version.set("0.0.1")
        super().__init__(console=True)

    def _get_console_namespace(self) -> dict[str, object]:
        """Add custom variables alongside the defaults."""
        ns = super()._get_console_namespace()
        ns["app"] = self  # alias
        ns["data"] = self.CUSTOM_DATA
        ns["magic"] = 42
        return ns

    def _get_console_message(self) -> str:
        """Provide a domain-specific welcome message."""
        return (
            "Welcome to ConsoleHookTest console!\n"
            "Custom variables: app, data, magic\n"
            "Example:\n"
            "  data          # sample array\n"
            "  magic         # the answer\n"
            "  app == win    # True — both reference the main window"
        )


# =============================================================================
# Tests
# =============================================================================


def test_console_base():
    """Verify that the base SGMXMainWindow console has the expected namespace
    and welcome message."""
    with qth.sigimax_app_context(exec_loop=False):
        Conf.app_name.set("BaseConsoleTest")
        Conf.app_version.set("0.0.1")

        win = SGMXMainWindow(console=True)
        win.resize(800, 500)
        win.show()

        # Console must have been created
        assert win.console is not None, "Console was not created"

        # -- Check namespace contents ----------------------------------------
        ns = win.console.interpreter.locals
        assert "win" in ns, f"'win' missing from namespace: {list(ns)}"
        assert ns["win"] is win, "'win' should reference the main window"
        assert "np" in ns, f"'np' missing from namespace: {list(ns)}"
        assert ns["np"] is np, "'np' should be numpy"

        expected_keys = {"win", "np", "sps", "spi", "os", "sys", "osp", "time"}
        assert expected_keys.issubset(ns.keys()), (
            f"Missing keys: {expected_keys - ns.keys()}"
        )

        # DataLab-specific names must NOT be present
        assert "dl" not in ns, "'dl' should not be in base namespace"

        # -- Check welcome message -------------------------------------------
        msg = win._get_console_message()  # pylint: disable=protected-access
        assert "win" in msg, "Welcome message should mention 'win'"
        assert Conf.app_name.get() in msg, "Welcome message should contain the app name"

        # -- Clean close -----------------------------------------------------
        win.set_modified(False)
        win.close()

    print("Base console test passed.")


def test_console_derived():
    """Verify that a derived window can inject custom variables and message
    into the console."""
    with qth.sigimax_app_context(exec_loop=False):
        win = CustomConsoleWindow()
        win.resize(800, 500)
        win.show()

        assert win.console is not None, "Console was not created"

        # -- Check that custom variables are present in namespace -------------
        ns = win.console.interpreter.locals

        assert "app" in ns, f"'app' missing from namespace: {list(ns)}"
        assert ns["app"] is win, "'app' should reference the main window"
        assert "data" in ns, f"'data' missing from namespace: {list(ns)}"
        assert (ns["data"] == CustomConsoleWindow.CUSTOM_DATA).all(), (
            "'data' should be the custom array"
        )
        assert "magic" in ns, f"'magic' missing from namespace: {list(ns)}"
        assert ns["magic"] == 42, "'magic' should be 42"

        # -- Default variables should still be present (via super()) ----------
        assert "win" in ns, "'win' should still be present"
        assert ns["win"] is win, "'win' should reference the main window"
        assert "np" in ns, "'np' should still be present"

        # -- Check custom welcome message -------------------------------------
        msg = win._get_console_message()  # pylint: disable=protected-access
        assert "ConsoleHookTest" in msg, (
            "Custom welcome message should mention the app name"
        )
        assert "magic" in msg, "Custom welcome message should mention 'magic'"
        assert "data" in msg, "Custom welcome message should mention 'data'"

        # -- Clean close -----------------------------------------------------
        win.set_modified(False)
        win.close()

    print("Derived console test passed.")


if __name__ == "__main__":
    test_console_base()
    test_console_derived()
