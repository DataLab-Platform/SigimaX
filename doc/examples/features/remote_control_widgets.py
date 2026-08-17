# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Remote Control Widgets
=======================

This example demonstrates how to use
:class:`~sigimax.widgets.connection.ConnectionDialog` and
:class:`~sigimax.widgets.objectdialog.GetObjectDialog` to build a minimal
remote client for a DataLab-derived application server.

These widgets are generic: they only depend on
:class:`sigima.client.SimpleRemoteProxy` (or any proxy exposing the same
``connect``/``get_current_panel``/``get_group_titles_with_object_info`` API),
never on a specific application's branding or object model.

To keep this example runnable without a real DataLab-derived application,
:class:`sigima.client.stub.DataLabStubServer` is used to simulate one
in-process.
"""

# %%
# Importing necessary modules
# ---------------------------

import numpy as np
from guidata.qthelpers import qt_app_context
from sigima.client import SimpleRemoteProxy
from sigima.client.stub import DataLabStubServer

from sigimax.widgets.connection import ConnectionDialog
from sigimax.widgets.objectdialog import GetObjectDialog

# %%
# Starting a (stub) server and connecting to it
# ------------------------------------------------
#
# In a real client application, ``server`` would not exist: a real
# DataLab-derived application would already be running, and ``proxy.connect``
# would be passed to :class:`~sigimax.widgets.connection.ConnectionDialog` for
# the user to see the connection progress.

server = DataLabStubServer(verbose=False)
port = server.start()

proxy = SimpleRemoteProxy(autoconnect=False)

with qt_app_context(exec_loop=False):
    dlg = ConnectionDialog(lambda: proxy.connect(port=str(port), timeout=2.0))
    connected = dlg.exec()
    print(f"Connected: {connected} (error: {dlg.get_error_message() or 'none'})")

# %%
# Populating the server with a couple of signals
# -------------------------------------------------
#
# ``add_signal`` stores the signal on the server but does not attach it to
# any group by itself: the stub server's default group is wired here
# directly, through the server instance, to get a non-empty tree below. A
# real DataLab-derived server groups newly added objects automatically.

proxy.add_signal("Signal 1", np.arange(10.0), np.arange(10.0))
proxy.add_signal("Signal 2", np.arange(10.0), np.arange(10.0) ** 2)
group_uuid = next(iter(server.signal_groups))
server.signal_groups[group_uuid].objects.extend(server.signals.keys())

# %%
# Picking an object from the server
# ------------------------------------
#
# :class:`~sigimax.widgets.objectdialog.GetObjectDialog` lists the groups and
# objects available on the server. Restricting ``panel`` to ``"signal"``
# hides the panel selector combo box.

with qt_app_context(exec_loop=False):
    dlg = GetObjectDialog(None, proxy, panel="signal")
    group_item = dlg.tree.topLevelItem(0)
    dlg.tree.setCurrentItem(group_item.child(0))
    print(f"Selected object UUID: {dlg.get_current_object_uuid()}")

server.stop()

# %%
# Summary
# -------
#
# - :class:`~sigimax.widgets.connection.ConnectionDialog` wraps a blocking
#   ``connect`` callback in a background thread, so the Qt event loop keeps
#   running while the connection is attempted.
# - :class:`~sigimax.widgets.objectdialog.GetObjectDialog` displays the
#   groups/objects reported by
#   :meth:`sigima.client.base.SimpleBaseProxy.get_group_titles_with_object_info`.
# - :class:`~sigima.client.stub.DataLabStubServer` lets both widgets be
#   exercised headlessly, without a real DataLab-derived application.
