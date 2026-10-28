# Version 1.1.0 #

## Unreleased ##

* Python 3.10 or later is now required. Python 3.9 users must keep an earlier compatible release.

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
* The tooltip of a rectangular ROI defined in pixel indices now shows the pixels selected by the ROI, i.e. those whose centers lie inside the rectangle: the corners of the rectangle were rounded to the nearest pixel indices, which could show a selection shifted by one pixel once the rectangle had been moved.

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
* The HDF5 browser reads previews in a worker thread, so that it stays responsive while a large dataset is read: only the last selected node is shown, the previews of nodes selected meanwhile are not read, selecting a node that cannot be previewed (a group, for example) clears the preview, and closing a file or the browser dialog waits for the preview being read (imported objects are then read without concurrent access to the file). Ordinary 1D arrays and 2D images, NeXus and mapped objects with more than `PlotPreview.MAX_ITEMS` (2²⁴) elements are previewed with a step along each axis; the axes of NeXus images are still read entirely, to check that they are strictly monotonic as on import (they hold far fewer values than the image). Compound datasets and signals stored in 2D tables still use complete objects for graphical previews; this is not a universal memory bound.
* Numeric datasets with three dimensions or more (image stacks, spectral cubes...) are now listed in the HDF5 browser, with their shape and type, and imported through a view: one signal or image per frame. When such a dataset (or NeXus signal) is selected, a view selector proposes the displayed axes (images of two axes, or signals along one axis), the axis along which frames are taken with their first, last and step, and the index of the other axes; the first frame is previewed, and the frames are imported once "Import these frames" is checked, the browser asking for confirmation beyond `MAX_FRAMES_WITHOUT_CONFIRMATION` (100) frames before creating them. The default view follows the NeXus `interpretation` of the signal (`spectrum`: signals along the last axis, `rgba-image`: one image per channel, otherwise images of the last two axes). Frames of NeXus signals keep the axes of their displayed dimensions, and their title and origin give the frame indices and the coordinates of the frame along the other axes. Developers set views with `NDView`, `default_view` and `set_view`, `expand_views` replaces a node by the nodes of its frames and `count_frames` counts them without creating them (`sigimax.h5.views`); `read_selection` reads only the selected elements (`NDSelection`: displayed axes, possibly transposed, and an index along each other axis).
* NeXus `NXdata` groups are shown as single nodes, imported as a signal (1D) or an image (2D) with their axes, units, labels and, for signals, uncertainties: `@signal`/`@axes` attributes with `@<axis>_indices`, legacy `signal`/`axes` dataset attributes, bin edges converted to bin centers, non-uniform image axes. Image axes deviating from even spacing by at most 2.5 units in the last place of their data type (`UNIFORM_AXIS_TOLERANCE`) are imported as uniform coordinates, so that evenly spaced `float32` axes are recognized, and their maximum deviation is recorded among the conversions; other image axes keep their stored coordinates. Decreasing image axes are reversed with the image. Invalid axes (axis count differing from the signal rank, axes designating a missing or already described dimension, axes not holding real numbers, image axes not strictly monotonic) are reported instead of being guessed. Imported objects record their origin in the `experimental_source` metadata entry (file, group, signal and axes, `"."` for a dimension without axis, conversions, and the title, start and end times of the entry). `.nxs` and `.nx5` files are proposed in HDF5 file dialogs.
* NeXus files written with the legacy conventions (e.g. scans of synchrotron SOLEIL) are imported with their axes: without `@axes`, the `axis` attribute of axis datasets gives the dimension they describe (from 1), the dataset with the lowest `primary` attribute being preferred, and an axis applies to the dimensions whose size fits. The other signals of an `NXdata` group (`@auxiliary_signals` attribute, or datasets having a legacy `signal` attribute, as counters and detectors of a scan) are shown as nodes of their own, with the axes that fit their dimensions: for example, a 1D counter is a signal versus the scanned motor, a detector writing a spectrum per point is an image with the motor along Y, and a detector writing an image per point is a stack of images, one per motor position.
* The HDF5 browser selects and expands the default `NXdata` group of a NeXus file (`@default` attributes of the file and of its entry) when the file is opened (`default_nxdata_path`).
* Compressed detector data (bitshuffle/LZ4 of Eiger detectors, Blosc, Zstandard...) is now read: SigimaX requires hdf5plugin, which provides these HDF5 filters. Datasets compressed with a filter that is still unavailable are reported in the browser (filter name and number) instead of failing when read.
* Files that do not designate their data with suitable `NXdata` groups (no axes, several counters...) can be described by declarative data mappings (`sigimax.h5.mapping`): JSON-compatible descriptions of the signals and images of the groups having given attributes and paths, with their axes, uncertainties, labels and units, and a name pattern to repeat an object for each counter of a scan. The `axes` of a mapped object describe its first dimensions, the following ones having no axis, so that one pattern applies to counters, spectra and images of a scan, with the scan axis first. Mapped objects are shown as extra nodes of the HDF5 browser and record the mapping in their `experimental_source`. Applications and plugins register mappings with `register_mapping` (and `unregister_mapping`); `NodeFactory.add_children_provider` lets them add such extra nodes. Blank units and labels are now ignored.
* Dataset attributes with more than `MAX_ATTRIBUTE_ITEMS` (10 000) values are no longer copied to object metadata.
* Images with unsigned 32-bit values above 2 147 483 647 are no longer clipped to `int32`: they are converted with Sigima's converter, which keeps every value exactly with Sigima ≥ 1.4.0. `BaseNode.uint32_wng` is kept for compatibility and is always `False`.
* 1D datasets of single-precision complex numbers (`complex64`) are now imported as complex signals: only their real part was kept (with a `ComplexWarning`). Integer signals beyond 2⁵³ now emit Sigima's precision warning instead of being rounded silently, and 2D tables with complex X values or uncertainties are reported as unsupported instead of being truncated.
* `NodeFactory.unregister` removes a node class and its post triggers, so that an application plugin can remove the node classes it registered when it is unloaded.
* Files containing broken links (soft links to a missing object, or external links to a missing file, as in synchrotron master files whose detector files are not available) can now be opened: the broken links are skipped with a warning in the console, instead of preventing the whole file from being browsed or imported.
* Files containing a link back to a parent group (a group linked into itself or into one of its subgroups) can now be opened: such links are skipped with a warning in the console, instead of raising a `RecursionError`. Other aliases of a group or dataset are still shown at each of their paths, and the HDF5 file is now closed when its tree cannot be built.

See the [HDF5 guide](../user_guide/hdf5_workspace.rst) for a complete JSON mapping and registration example, NeXus import limits and multidimensional selection examples.

### Requirements ###

* Sigima 1.4.0 or later is required: the HDF5 import modules use its experimental-source API, integer conversions use its precision-preserving converter, and the tooltips of rectangular ROIs use its pixel-range conversions.
* hdf5plugin 4.0 or later is required, for the HDF5 compression filters of detector data.