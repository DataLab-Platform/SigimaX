# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Main-window lifecycle hook tests."""

from __future__ import annotations

from sigimax.config import CONF as Conf
from sigimax.mainwindow import SGMXMainWindow
from sigimax.utils import qthelpers as qth


class HookWindow(SGMXMainWindow):
    """Window recording the protected setup and persistence hooks."""

    def __init__(self) -> None:
        self.hook_calls: list[str] = []
        super().__init__(console=False)

    def _update_color_mode(self, startup: bool = False) -> None:
        self.hook_calls.append("color")
        super()._update_color_mode(startup=startup)

    def _before_setup(self, console: bool) -> None:
        self.hook_calls.append("before")
        super()._before_setup(console)

    def _configure_statusbar(self, console: bool) -> None:
        self.hook_calls.append("statusbar")
        super()._configure_statusbar(console)

    def _setup_global_actions(self) -> None:
        self.hook_calls.append("actions")
        super()._setup_global_actions()

    def _setup_central_widget(self) -> None:
        self.hook_calls.append("central")
        super()._setup_central_widget()

    def _add_menus(self) -> None:
        self.hook_calls.append("menus")
        super()._add_menus()

    def _restore_state(self) -> None:
        self.hook_calls.append("state")
        super()._restore_state()

    def _restore_pos_and_size(self) -> None:
        self.hook_calls.append("geometry")
        super()._restore_pos_and_size()

    def _after_setup(self, console: bool) -> None:
        self.hook_calls.append("after")
        super()._after_setup(console)

    def _save_pos_size_and_state(self) -> None:
        self.hook_calls.append("save")
        super()._save_pos_size_and_state()

    def _close_managed_widgets(self) -> None:
        self.hook_calls.append("close_widgets")
        super()._close_managed_widgets()

    def _cleanup_before_reset(self) -> None:
        self.hook_calls.append("before_reset")
        super()._cleanup_before_reset()

    def _cleanup_after_state_save(self) -> None:
        self.hook_calls.append("after_save")
        super()._cleanup_after_state_save()


def test_lifecycle_hooks() -> None:
    """Protected lifecycle hooks are overridable and keep a stable call order."""
    Conf.app_name.set("LifecycleHookTest")
    with qth.sigimax_app_context(exec_loop=False):
        window = HookWindow()
        assert window.hook_calls == [
            "color",
            "before",
            "statusbar",
            "actions",
            "central",
            "menus",
            "state",
            "after",
            "geometry",
        ]
        window._save_pos_size_and_state()  # pylint: disable=protected-access
        assert window.hook_calls[-1] == "save"
        assert window.close_properly()
        assert window.hook_calls[-4:] == [
            "close_widgets",
            "before_reset",
            "save",
            "after_save",
        ]
