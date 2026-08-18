# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Tests for the GetObjectDialog widget (:mod:`sigimax.widgets.objectdialog`)
----------------------------------------------------------------------------

Covers:
- SimpleObjectTree population from a remote proxy (stub server)
- GetObjectDialog current object selection and OK button state
"""

from __future__ import annotations

import numpy as np
import pytest
from guidata.qthelpers import qt_app_context
from sigima.client import SimpleRemoteProxy
from sigima.client.stub import DataLabStubServer

from sigimax.widgets.objectdialog import GetObjectDialog

pytestmark = pytest.mark.gui


def _connected_proxy_with_signals(server: DataLabStubServer) -> SimpleRemoteProxy:
    """Connect a proxy to the stub server and populate its default group.

    ``add_signal`` stores the signal on the stub server but does not attach
    it to any group: the default group's object list is wired directly here
    via the stub server instance to get a deterministic, non-empty group.
    """
    proxy = SimpleRemoteProxy(autoconnect=False)
    proxy.connect(port=str(server.port), timeout=2.0, retries=1)
    proxy.add_signal("Signal 1", np.arange(10.0), np.arange(10.0))
    proxy.add_signal("Signal 2", np.arange(10.0), np.arange(10.0) ** 2)
    group_uuid = next(iter(server.signal_groups))
    server.signal_groups[group_uuid].objects.extend(server.signals.keys())
    return proxy


def test_get_object_dialog_lists_signals():
    """The dialog tree is populated with the signals added to the panel."""
    server = DataLabStubServer(verbose=False)
    server.start()
    try:
        proxy = _connected_proxy_with_signals(server)
        with qt_app_context():
            dlg = GetObjectDialog(None, proxy, panel="signal")
            group_item = dlg.tree.topLevelItem(0)
            titles = [
                group_item.child(index).text(0)
                for index in range(group_item.childCount())
            ]
            # No item selected by default -> OK button disabled
            assert dlg.get_current_object_uuid() is None
            assert not dlg.ok_btn.isEnabled()
            # Selecting the first object enables the OK button
            dlg.tree.setCurrentItem(group_item.child(0))
            assert dlg.get_current_object_uuid() is not None
            assert dlg.ok_btn.isEnabled()
        assert any("Signal 1" in title for title in titles)
        assert any("Signal 2" in title for title in titles)
    finally:
        server.stop()


def test_get_object_dialog_no_selection_disables_ok():
    """With no current item, the OK button is disabled."""
    server = DataLabStubServer(verbose=False)
    server.start()
    try:
        proxy = SimpleRemoteProxy(autoconnect=False)
        proxy.connect(port=str(server.port), timeout=2.0, retries=1)
        with qt_app_context():
            dlg = GetObjectDialog(None, proxy, panel="signal")
            dlg.tree.clearSelection()
            dlg.tree.setCurrentItem(None)
            # pylint: disable=protected-access
            dlg._GetObjectDialog__current_object_changed()
        assert dlg.get_current_object_uuid() is None
        assert not dlg.ok_btn.isEnabled()
    finally:
        server.stop()


if __name__ == "__main__":
    test_get_object_dialog_lists_signals()
    test_get_object_dialog_no_selection_disables_ok()
