Remote Control Widgets
======================

SigimaX provides ready-to-use Qt widgets to build a *remote client*
application: a separate process that connects to a running DataLab-derived
application server and exchanges signals/images with it, using
:class:`sigima.client.SimpleRemoteProxy` (or any proxy exposing the same
``connect``/``get_current_panel``/``get_group_titles_with_object_info`` API).

These widgets originate from the (now unmaintained) ``cdlclient`` /
`DataLab Simple Client <https://github.com/DataLab-Platform/DataLabSimpleClient>`_
package. They have been ported into SigimaX, generalized (no DataLab-specific
branding hardcoded), and adapted to the current :mod:`sigima.client` API.

Responsibilities
----------------

SigimaX provides:

- :class:`~sigimax.widgets.connection.ConnectionDialog`, a small modal dialog
  showing the progress of a (possibly slow or failing) connection attempt;
- :class:`~sigimax.widgets.objectdialog.GetObjectDialog` and
  :class:`~sigimax.widgets.objectdialog.SimpleObjectTree`, a dialog and tree
  widget to browse and pick a signal or image among the objects currently
  available on the connected server;
- generic icons for signals, images and groups
  (:mod:`sigimax.utils.svg_icons`).

A derived (client) application provides:

- the actual :class:`sigima.client.SimpleRemoteProxy` (or compatible proxy)
  instance and its connection parameters;
- what to do with the object selected in :class:`~sigimax.widgets.objectdialog.GetObjectDialog`
  (e.g. retrieve its data with :meth:`~sigima.client.base.SimpleBaseProxy.get_object`);
  the widgets never modify the connection or the remote objects themselves.

Connecting to a Server
-----------------------

:class:`~sigimax.widgets.connection.ConnectionDialog` wraps a *blocking*
connect callback (typically :meth:`sigima.client.remote.SimpleRemoteProxy.connect`)
in a background thread, so the Qt event loop keeps running while the
connection is attempted:

.. code-block:: python

    from guidata.qthelpers import qt_app_context
    from sigima.client import SimpleRemoteProxy
    from sigimax.widgets.connection import ConnectionDialog

    proxy = SimpleRemoteProxy(autoconnect=False)
    with qt_app_context():
        dlg = ConnectionDialog(proxy.connect)
        if dlg.exec():
            print(f"Connected on port {proxy.port}")
        else:
            print(f"Connection failed: {dlg.get_error_message()}")

The dialog is generic: it does not assume any application branding. A derived
application may pass its own window icon and/or a banner pixmap:

.. code-block:: python

    dlg = ConnectionDialog(proxy.connect, icon=my_icon, banner=my_banner_pixmap)

Picking a Remote Object
------------------------

Once connected, :class:`~sigimax.widgets.objectdialog.GetObjectDialog` lists
the groups and objects (signals and/or images) currently available on the
server, using :meth:`sigima.client.base.SimpleBaseProxy.get_group_titles_with_object_info`:

.. code-block:: python

    from sigimax.widgets.objectdialog import GetObjectDialog

    with qt_app_context():
        dlg = GetObjectDialog(parent, proxy, panel="signal")
        if dlg.exec():
            uuid = dlg.get_current_object_uuid()
            obj_data = proxy.get_object(uuid)

Passing ``panel=None`` (the default) lets the user switch between the signal
and image panels from a combo box inside the dialog. Passing ``panel="signal"``
or ``panel="image"`` restricts the dialog to a single panel and hides the
combo box.

Testing Without a Real Server
------------------------------

:mod:`sigima.client.stub` provides a lightweight in-process XML-RPC server
(:class:`~sigima.client.stub.DataLabStubServer`) that implements enough of the
protocol to exercise these widgets headlessly, without launching a real
DataLab-derived application. This is how SigimaX's own test suite validates
:class:`~sigimax.widgets.connection.ConnectionDialog` and
:class:`~sigimax.widgets.objectdialog.GetObjectDialog`:

.. literalinclude:: ../../sigimax/tests/widgets/test_object_dialog.py
   :language: python
   :pyobject: _connected_proxy_with_signals

.. note::

    ``SimpleRemoteProxy.add_signal`` stores the signal on the stub server
    unconditionally, but does not attach it to any group. The example above
    wires the stub server's default group directly (through the
    ``DataLabStubServer`` instance) to get a deterministic, non-empty tree for
    the test. A real DataLab-derived server groups newly added objects
    automatically.

See also the :ref:`sphx_glr_auto_examples_features_remote_control_widgets.py`
example for a runnable, standalone script.
