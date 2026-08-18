Main-Window Lifecycle
=====================

SigimaX creates a derived main window in a predictable sequence. Use the
protected hooks instead of relying on incidental constructor ordering.

Initialization Order
--------------------

When a :class:`~sigimax.mainwindow.SGMXMainWindow` is created, SigimaX:

1. initializes its own non-virtual state;
2. calls ``_before_setup(console)``;
3. applies the color mode through ``_update_color_mode(startup=True)``;
4. creates the generic status bar, actions, central widget, menus, and restored
   window state;
5. calls ``_after_setup(console)``; and
6. restores the window geometry.

Use ``_before_setup`` for derived state that another protected hook may need
during startup. Use ``_after_setup`` for work that requires generic widgets
such as actions, menus, or the status bar.

The HDF5 reference application follows this rule by creating its data model in
``_before_setup``:

.. literalinclude:: ../../sigimax/tests/hdf5/test_h5_derived_app.py
   :language: python
   :pyobject: DerivedAppWindow._before_setup

Singleton Access
----------------

Call ``MyMainWindow.get_instance()`` on the concrete derived class. It returns
the current instance of that class or creates one of the same class. This keeps
the base framework from accidentally constructing ``SGMXMainWindow`` when an
application requested its own window subclass.

Shutdown Order
--------------

For a modified workspace, the close flow asks the user to save first. A
successful application save clears the modified state; cancellation or failure
leaves it set and stops the close. Once closing proceeds, SigimaX calls
``_close_managed_widgets()``, ``_cleanup_before_reset()``,
``reset_all()``, ``_save_pos_size_and_state()``, and
``_cleanup_after_state_save()`` in that order.

Derived applications should use these hooks for their own managed resources and
call ``super()`` when preserving the generic behavior is required.