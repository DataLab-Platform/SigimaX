# Version 1.1.0 #

## SigimaX Version 1.1.0 ##

### PlotPy adapters ###

* PlotPy annotations created or edited through SigimaX are now stored with
  Sigima's renderer-independent annotation model, so they may be displayed by
  other supported visualization backends without carrying PlotPy-specific
  serialization data.
* Existing PlotPy annotations remain readable without modifying the source
  object. Supported annotations are migrated when an edit is accepted, while
  malformed, unknown, or partially supported payloads are preserved unchanged.
* Canonical annotation identifiers, metadata, extensions, and persistent lock
  state are preserved across PlotPy editing round trips. Application-specific
  opaque annotation entries continue to coexist with graphical annotations.

### Main window ###

* With Qt 5, the dock widget sizes saved on exit are now restored at startup: the window is sized and laid out before its state is restored, so tabified docks no longer shrink to the default window size and leave the extra width to the central widget.

### Qt helpers ###

* `block_signals` now restores the previous signal-blocking state of the widget and of its children instead of unblocking them unconditionally: nested blocking contexts and widgets already blocked by the caller keep their state.
* `sigimax_app_context` no longer schedules the unattended/screenshot close timer when the Qt event loop is not executed (`exec_loop=False`): the pending timer previously closed unrelated top-level widgets created later, such as the window of a subsequent test.

### Requirements ###

* Sigima 1.3.0 or later is required for the portable annotation model and
  PlotPy conversion helpers.