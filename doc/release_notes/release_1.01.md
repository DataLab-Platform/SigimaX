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
* Closing the main window (unless it is only hidden, see `hide_on_close`) now releases it as the instance returned by `get_instance`, which creates a new window afterwards: the closed window, with its widgets and data, is no longer kept in memory until another main window is created.

### Qt helpers ###

* `block_signals` now restores the previous signal-blocking state of the widget and of its children instead of unblocking them unconditionally: nested blocking contexts and widgets already blocked by the caller keep their state.
* `sigimax_app_context` no longer schedules the unattended/screenshot close timer when the Qt event loop is not executed (`exec_loop=False`): the pending timer previously closed unrelated top-level widgets created later, such as the window of a subsequent test.

### Curve fitting dialogs ###

* Interactive fitting dialogs now show the formula of the fitted model below the fit parameters, and parameter labels show the symbols used in the formula (e.g. "Scale factor (x₀)"), so that the parameters stored in the fitted signal metadata can be related to the model. `guifit` accepts a new `formula` argument for this purpose. This closes [Issue #9](https://github.com/DataLab-Platform/SigimaX/issues/9).
* Polynomial and linear fit coefficients are now labelled `a`, `b`, `c`... as in the model formula and in the fitted signal metadata, instead of `c2`, `c1`, `c0`.
* The Planckian fit dialog starts from a curve matching the data peak (its initial amplitude was about 147 times too low on blackbody data in physical units), and its "width factor" is now labelled "temperature factor": for wavelengths in meters, the temperature is `h c σ / (5 k_B x₀)`.
* The exponential fit dialog now evaluates the same model as Sigima, and its rate slider covers short time constants whatever the X unit (e.g. 1 ms with X in seconds).

### Requirements ###

* Sigima 1.3.0 or later is required for the portable annotation model, PlotPy conversion helpers and curve fitting model formulas.