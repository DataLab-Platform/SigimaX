Main-Window Lifecycle
=====================

SigimaX creates a derived main window in a predictable sequence. Use the
protected hooks instead of relying on incidental constructor ordering.

Initialization Order
--------------------

When a :class:`~sigimax.mainwindow.SGMXMainWindow` is created, SigimaX:

1. initializes its own non-virtual state;
2. calls :meth:`~sigimax.mainwindow.SGMXMainWindow._before_setup`;
3. applies the color mode through
   :meth:`~sigimax.mainwindow.SGMXMainWindow._update_color_mode`
   (``startup=True``);
4. clears the modified state and restores the window position and size
   (:meth:`~sigimax.mainwindow.SGMXMainWindow._restore_pos_and_size`);
5. calls :meth:`~sigimax.mainwindow.SGMXMainWindow.setup`, which:

   a. creates the status bar, with the widgets returned by
      :meth:`~sigimax.mainwindow.SGMXMainWindow._get_extra_status_widgets`;
   b. creates the global actions
      (:meth:`~sigimax.mainwindow.SGMXMainWindow._create_global_actions`) and
      the main toolbar
      (:meth:`~sigimax.mainwindow.SGMXMainWindow._get_main_toolbar_actions`);
   c. calls :meth:`~sigimax.mainwindow.SGMXMainWindow._setup_panels`;
   d. creates the central widget and the menus
      (:meth:`~sigimax.mainwindow.SGMXMainWindow._get_menubar_layout`);
   e. creates the console, if enabled
      (:meth:`~sigimax.mainwindow.SGMXMainWindow._configure_console`);
   f. calls :meth:`~sigimax.mainwindow.SGMXMainWindow._setup_docks`, then
      :meth:`~sigimax.mainwindow.SGMXMainWindow._post_setup`; and
   g. restores the saved window state, i.e. the layout of docks and toolbars
      (:meth:`~sigimax.mainwindow.SGMXMainWindow._restore_state`), last;

6. calls :meth:`~sigimax.mainwindow.SGMXMainWindow._after_setup`.

Use ``_before_setup`` for derived state that another protected hook may need
during startup. Add dock widgets in ``_setup_docks`` with
:meth:`~sigimax.mainwindow.SGMXMainWindow._add_dockwidget`: docks added after
``_restore_state`` keep their default geometry. Use ``_post_setup`` or
``_after_setup`` for work that requires generic widgets such as actions,
menus, or the status bar. Override the hooks called by ``setup`` rather than
``setup`` itself.

The File and View menus are cleared and rebuilt each time they are shown:
extend them through
:meth:`~sigimax.mainwindow.SGMXMainWindow._get_file_menu_actions` and
:meth:`~sigimax.mainwindow.SGMXMainWindow._get_view_menu_actions` (or
:meth:`~sigimax.mainwindow.SGMXMainWindow._update_file_menu` and
:meth:`~sigimax.mainwindow.SGMXMainWindow._update_view_menu`), not by adding
actions to ``file_menu`` or ``view_menu``.

The :class:`~sigimax.mainwindow.SGMXMainWindow` reference documents all the
protected hooks.

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