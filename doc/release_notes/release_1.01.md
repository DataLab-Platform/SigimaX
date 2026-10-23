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

### HDF5 import ###

* Browsing an HDF5 file no longer reads its numeric datasets entirely just to classify them: generic nodes are classified and described from the dataset shape and data type, and value previews read only the first elements (`TEXT_PREVIEW_MAX_ITEMS`). Compound datasets mixing numeric and string fields are checked on their first records only. Full data is read when creating an imported object or an undecimated graphical preview.
* The HDF5 browser reads previews in a worker thread, so that it stays responsive while a large dataset is read: only the last selected node is shown, the previews of nodes selected meanwhile are not read, and closing a file or the browser dialog waits for the preview being read (imported objects are then read without concurrent access to the file). Ordinary 1D arrays and 2D images, NeXus and mapped objects with more than `PlotPreview.MAX_ITEMS` (2²⁴) elements are previewed with a step along each axis. Compound datasets and signals stored in 2D tables still use complete objects for graphical previews; this is not a universal memory bound.
* Numeric datasets with three dimensions or more (image stacks, spectral cubes...) are now listed in the HDF5 browser, with their shape and type. They are not imported as a whole, and there is no graphical slice selector: developers can read their 1D or 2D views with `sigimax.h5.selection.read_selection`, which reads only the selected elements (`NDSelection`: displayed axes, possibly transposed, and an index along each other axis).
* NeXus `NXdata` groups are shown as single nodes, imported as a signal (1D) or an image (2D) with their axes, units, labels and, for signals, uncertainties: `@signal`/`@axes` attributes with `@<axis>_indices`, legacy `signal`/`axes` dataset attributes, bin edges converted to bin centers, non-uniform image axes. Uniform axes are detected within the precision of their data type (e.g. `float32` axes), and decreasing image axes are reversed with the image. Invalid axes (axis count differing from the signal rank, axes designating a missing or already described dimension, axes not holding real numbers, image axes not strictly monotonic) are reported instead of being guessed. Imported objects record their origin in the `experimental_source` metadata entry (file, group, signal and axes, `"."` for a dimension without axis, conversions). `.nxs` and `.nx5` files are proposed in HDF5 file dialogs.
* Files that do not designate their data with suitable `NXdata` groups (no axes, several counters...) can be described by declarative data mappings (`sigimax.h5.mapping`): JSON-compatible descriptions of the signals and images of the groups having given attributes and paths, with their axes, uncertainties, labels and units, and a name pattern to repeat an object for each counter of a scan. Mapped objects are shown as extra nodes of the HDF5 browser and record the mapping in their `experimental_source`. Applications and plugins register mappings with `register_mapping` (and `unregister_mapping`); `NodeFactory.add_children_provider` lets them add such extra nodes. Blank units and labels are now ignored.
* Dataset attributes with more than `MAX_ATTRIBUTE_ITEMS` (10 000) values are no longer copied to object metadata.
* Images with unsigned 32-bit values above 2 147 483 647 are no longer clipped to `int32`: they are converted with Sigima's converter, which keeps every value exactly with Sigima ≥ 1.4.0. `BaseNode.uint32_wng` is kept for compatibility and is always `False`.
* 1D datasets of single-precision complex numbers (`complex64`) are now imported as complex signals: only their real part was kept (with a `ComplexWarning`). Integer signals beyond 2⁵³ now emit Sigima's precision warning instead of being rounded silently, and 2D tables with complex X values or uncertainties are reported as unsupported instead of being truncated.
* `NodeFactory.unregister` removes a node class and its post triggers, so that an application plugin can remove the node classes it registered when it is unloaded.

See the [HDF5 guide](../user_guide/hdf5_workspace.rst) for a complete JSON mapping and registration example, NeXus import limits and multidimensional selection examples.

### Requirements ###

* Sigima 1.4.0 or later is required: the HDF5 import modules use its experimental-source API, and integer conversions use its precision-preserving converter.