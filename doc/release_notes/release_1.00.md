# Version 1.0 #

## SigimaX Version 1.0.2 ##

### Changes ###

* Reworked the release automation: documentation is now built and hosted by
  Read the Docs (dedicated GitHub Pages workflow removed), and the publication
  workflow relies on PyPI Trusted Publishing, gated on the PyQt5 and PyQt6 test
  workflows
* Added `scripts/ci_release_helpers.py` to check release tags and extract
  release notes

## SigimaX Version 1.0.1 ##

### Changes ###

* Added `_on_h5_save_requested()` and `_on_h5_open_requested()` hooks to
  `SGMXMainWindow`, called before writing or reading an HDF5 workspace, so that
  derived applications can react to those operations (e.g. to maintain a recent
  files history)
* Fixed the main window layout persistence: running tests in unattended mode no
  longer overwrites the user's saved window position, size and state


## SigimaX Version 1.0.0 ##

### Highlights ###

This release turns `SGMXMainWindow` and the SigimaX configuration system into a real
extension surface: derived applications (DataLab and others) can now compose menus,
docks, status bar widgets, HDF5 import and the whole application lifecycle by
overriding small, well-documented hooks instead of duplicating entire methods. It
also brings a simplified, more robust configuration option system, new remote-control
widgets for connecting to a running DataLab-Kernel instance, and a batch of fixes
ported from DataLab's `develop` branch.

### Application framework ###

* Made the main window setup sequence an extension point: `setup()` now calls
  optional `_setup_panels()`, `_setup_docks()` and `_post_setup()` hooks so that
  derived applications add their panels, docks and final wiring without
  reimplementing the whole startup sequence
* Turned the dock registry into an explicit extension point: `_add_dockwidget()`
  now owns registration in `self.docks`, assigns a stable Qt object name and
  handles tabification through new `name`, `key` and `tabify_with` arguments,
  so derived applications no longer register docks by hand
* Let derived applications compose the menu bar through `_get_menubar_layout()`
  and extend the Help menu through `_get_help_doc_actions()`,
  `_get_help_support_actions()` and `_get_help_about_actions()`, instead of
  reimplementing `_add_menus()` entirely
* Let derived applications contribute status bar widgets via
  `_get_extra_status_widgets()`, inserted between the console and memory status,
  instead of rebuilding the whole status bar
* Exposed a broad set of protected lifecycle hooks (status bar, actions, central
  widget, menus, console, geometry, window state, toolbar, dock, memory and
  color-mode steps, plus pre/post setup, post-show and shutdown hooks), all
  documented and covered by dedicated lifecycle-ordering tests
* Fixed the derived main window lifecycle: singleton instances are now created
  from the requested derived window class, with protected setup running before
  virtual startup hooks
* Deferred command-line argument parsing so that the module-level SigimaX
  execution environment no longer intercepts application-specific options (such
  as DataLab's `--version`) before the derived environment is initialized
* Improved the application window factory to preserve the concrete derived
  window type, and made splash screen resource loading more robust (direct
  paths, guidata image path resolution, safe fallback when the configured
  resource is missing)
* Dropped DataLab code that only duplicated unchanged SigimaX main window
  behavior (tab icon size handling)

### Configuration system ###

* Simplified application configuration state management: removed unused
  environment-variable synchronization from application options and
  simplified get/set/context/serialization/reset operations
* Added an `option_changed` hook so derived applications can persist option
  changes without polling the configuration
* Added a storage serialization protocol (`to_storage`/`from_storage`) to
  option fields, fixing `to_dict`/`from_dict` and `reset_to_defaults` for
  fields whose getter/setter transform the stored value
* Let option fields declare their own storage metadata (`storage_key`,
  `runtime`), removing the need for key-mapping tables in consuming
  applications
* Moved generic option field types (`ConfigPathOptionField`,
  `WorkingDirOptionField`, `FormatStringOptionField`, `DataSetOptionField`,
  `FontOptionField`) from DataLab into `sigimax.config`, and removed the
  legacy `Section`/`Option` class hierarchy, which had no remaining consumer
* Added support for optional defaults on option fields and for standalone
  option field containers
* Fixed option state not being preserved when restored from a temporary
  context
* Made PlotPy default colors (foreground/background) color-mode aware by
  reading them at call time, so re-applying defaults after a color mode
  change now uses the current theme

### HDF5 support ###

* Made the HDF5 import contract explicit: `import_h5_file()` is renamed to
  `import_all_from_h5_file()` (it imports every supported dataset without a
  dialog), and a single `_handle_imported_objects()` convergence point now
  receives the imported objects together with the `reset_all` flag, so a
  derived application is never asked whether to clear the workspace only to
  have the answer ignored
* Added `_is_workspace_empty()` and `_get_clear_workspace_message()` hooks so
  derived applications can control the "clear workspace" question and its
  wording without reimplementing the import orchestrator
* Fixed safe HDF5 workspace contracts: derived applications are now required
  to implement workspace persistence instead of silently acknowledging a save
  that wrote no data
* Ported the latest HDF5 and widget fixes from DataLab's `develop` branch,
  including a fix for `DIMENSION_LIST`/`REFERENCE` attributes breaking
  picklability in `h5/common.py`

### Widgets ###

* Added `DataLabSimpleClient` widgets: a connection dialog and an object
  browsing dialog for remote-controlling a running DataLab-Kernel instance
  over HTTP ([DataLab-Platform/DataLab#183](https://github.com/DataLab-Platform/DataLab/issues/183))
* Aligned the plot dock's curve statistics with PlotPy: the hand-written,
  NaN-robust statistics label functions are replaced by PlotPy's own
  `CurveStatsTool.LABELFUNCS`, and the y-range cursor sum is now a plain sum
  instead of a trapezoidal integral, matching PlotPy's behavior
* Opened up the plot dock for customization: added
  `SigimaXPlotWidget._customize_image_panels()` to tweak the X/Y cross
  section panels, and `DockablePlotWidget.PLOTWIDGET_CLASS` to let a derived
  application select its own plot widget class
* Fixed signal update for plain `CurveItem`: when a signal's `xydata` has 4
  rows but `dx`/`dy` are all `NaN`, `update_item` no longer calls
  `set_data` with error-bar arguments on a plain curve item

### PlotPy adapters ###

* Made the adapter factory overridable: introduced `PlotPyAdapterFactory`
  with `get_adapter_factory()`/`set_adapter_factory()`/`reset_adapter_factory()`
  (following the existing `get_conf`/`set_conf`/`reset_conf` pattern), so a
  derived application can substitute an adapter or register an additional
  object type without forking the whole dispatch chain
* Promoted DataLab's signal ROI adapters into SigimaX: ROI fills are now
  clipped to the signal curve instead of covering the whole canvas height,
  and sibling ROIs cycle through a color palette indexed by ROI title so
  colors stay stable across deletions

### Testing ###

* Added regression tests for the HDF5 and widget fixes ported from DataLab
  (interactive fit metadata, `WarningErrorMessageBox` construction, config
  field coverage, HDF5 utility helpers, `DIMENSION_LIST`/`REFERENCE`
  picklability, `adapters_plotpy.coordutils` rounding)
* Added tests covering lifecycle hook overridability and call order for the
  main window setup and shutdown sequence
* Added tests for splash screen resource resolution (registered resources,
  missing-image fallback, disabled progress messages)
* Preserved coverage for the legacy HDF5 dataset selector contract
* Cleaned up remaining Pylint and pytest warnings (adapter factory dispatch
  table, import-outside-toplevel/cyclic-import disables, `pytest.warns` usage)

### Documentation and internationalization ###

* Updated and completed the French translation, including fixes to the SVG
  icon `.po` file format
* Updated the documentation pipeline and refreshed all user guide pages,
  examples and API references to reflect the simplified configuration API,
  the new lifecycle hooks and the `DataLabSimpleClient` widgets
* Updated the documentation banner
