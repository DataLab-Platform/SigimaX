# Version 0.1 #

## SigimaX Version 0.1.0 (2026-03-04) (pre-release)##

Initial development release — SigimaX is extracted from DataLab as a reusable GUI
application framework for scientific computing Qt applications.

### Highlights ###

SigimaX provides the generic "application skeleton" that any scientific computing Qt
application can build upon by subclassing its main window and configuration system.
This release contains the full extraction from DataLab, including:

* Generic main window (`SGMXMainWindow`) with customizable menus, toolbars, and console
* Configuration system based on Sigima's typed option fields
* HDF5 browsing, generic import, and workspace persistence hooks
* Splash screen and application launcher (`create()` / `run()`)
* PlotPy adapters for signal/image plot items
* Reusable scientific widgets (fit dialogs, baseline, peak detection, cursor, etc.)
* Comprehensive test suite with 155+ tests across unit, GUI, and app categories
* Full Sphinx documentation with API reference and gallery examples
* Complete French translation (189 strings)

### Application framework ###

* Implemented `SGMXMainWindow` — a generic main window that derived applications
  subclass to build their own UI, with customizable menu order, toolbar actions,
  and console namespace
* Added `create()` and `run()` application launcher functions in `app.py` with
  configurable splash screen support (`SplashScreenConfig`)
* Provided overridable hooks for derived apps: `reset_all()`, `_is_save_enabled()`,
  `_update_file_menu()`, `_update_view_menu()`, `_about()`
* Added generic main toolbar configuration — derived apps can redefine toolbar actions
* Added quit action to the file menu

### Configuration system ###

* Implemented typed configuration options inspired by Sigima's non-INI-file config
  system, with `TypedOptionField`, `EnumOptionField`, `TupleOptionField`, and
  `FontOptionField`
* Added generic application metadata options (`app_name`, `app_version`,
  `app_logo_path`, `app_desc`, `app_docurl`, `app_homeurl`, `app_supporturl`)
* Configuration supports JSON persistence via `save()` / `load()`
* Removed `process_isolation_enabled` option (DataLab-specific — the framework only
  used it cosmetically; the actual mechanism stays in DataLab)

### HDF5 support ###

* Ported generic HDF5 browsing and dataset import
* Added workspace persistence hooks for derived applications; SigimaX does not
  impose a universal workspace format or serializer
* Added `import_dataset_from_file()` hook for derived apps to handle
  application-specific dataset import from HDF5
* Ported `H5BrowserDialog` widget for interactive HDF5 file browsing

### Widgets ###

* Ported scientific dialog widgets from DataLab: curve fitting (`fitdialog`),
  signal baseline selection, signal peak detection, signal cursor, signal delta-X
  measurement, image background selection
* Added `DockablePlotWidget` for embedding PlotPy plots in dock widgets, with
  configurable watermark and dock location via `SigimaXOptions`
* Ported status bar widgets: `BaseStatus`, `MemoryStatus`, `ConsoleStatus`
* Added `Wizard` multi-page dialog widget
* Added `LogViewerWindow` for log display
* Added `FileViewerWidget` for read-only file viewing
* Added `WarningErrorMessageBox` for warning/error display
* Added convenience re-exports in `widgets/__init__.py` with `__all__`

### PlotPy adapters ###

* Ported `adapters_plotpy` module for converting between Sigima objects
  (`SignalObj`, `ImageObj`) and PlotPy plot items
* Added `iterate_metadata_shape_items()` hook on `BaseObjPlotPyAdapter` —
  a no-op generator that derived apps (DataLab) can override to yield plot items
  for app-specific metadata entries (geometry results, table results)
* Cleaned up commented-out scalar adapter code (`GeometryPlotPyAdapter`,
  `TableAdapter`) — these stay in DataLab

### Environment and utilities ###

* Implemented `SGMXExecEnv` runtime environment singleton (renamed from DataLab's
  `DLExecEnv`) with verbosity levels, demo mode, and unattended mode
* Ported Qt helper utilities (`utils/qthelpers.py`): log file management,
  signal blocking context manager, stdout/stderr save/restore
* Added local PDF documentation path handling in the Help menu

### Package structure ###

* Dissolved `gui/` subpackage — moved `gui/main.py` → `mainwindow.py` (top-level)
  and `gui/docks.py` → `widgets/plotdock.py` for clearer naming
* Added `__all__` declarations in all public modules
* Added `from __future__ import annotations` across all modules
* Top-level `__init__.py` re-exports `SGMXMainWindow`, `create`, `run`
  (follows Sigima's pattern)
* Fixed circular import between `__init__.py` and `config.py` by extracting
  metadata to `_metadata.py`
* Removed dead code: commented-out imports, `config_old.py`, DataLab-specific
  action handler dependencies

### Testing ###

* Built comprehensive test suite with 155+ tests organized into subpackages:
  `config/`, `mainwindow/`, `widgets/`, `hdf5/`, `adapters_plotpy/`, `utils/`
* Standardized test file naming to `test_*.py` convention; non-test helpers
  prefixed with `_`
* Added pytest markers: `@pytest.mark.unit` (pure logic, no Qt),
  `@pytest.mark.gui` (Qt widget tests), `@pytest.mark.app` (full main window)
* Added `--show-windows` flag for visual test validation (offscreen by default)
* PlotPy adapter tests cover factory dispatch, make/update item roundtrips,
  ROI coordinate roundtrips, and annotation integration

### Documentation ###

* Added full Sphinx documentation with API reference pages for all public modules
  (`app`, `config`, `env`, `mainwindow`, `widgets`, `h5`, `adapters_plotpy`, `utils`)
* Added Sphinx-Gallery examples: getting started (`minimal_app.py`), features
  (`configuration.py`, `plot_widget.py`), and use cases (`full_app.py`)
* Added user guide pages: overview, installation, contributing
* Documentation builds cleanly with `-W` (warnings-as-errors)

### Internationalization ###

* Added complete French translation of all 189 UI strings
  (`sigimax/locale/fr/LC_MESSAGES/sigimax.po`)
* Translations cover menus, toolbar, HDF5 browser, fit dialogs, signal widgets,
  status bar, error/warning dialogs, wizard, and about/help
* Terminology aligned with DataLab's existing French translations for consistency

### Project infrastructure ###

* Created `pyproject.toml` with Ruff rules (`D202`, `D403`, `RUF022`, Google
  pydocstyle), pytest config (`--import-mode=importlib`, `filterwarnings`)
* Added Sphinx documentation scaffolding (imported from Sigima's structure)
* Added copilot instructions (`.github/copilot-instructions.md`)
* Changed maintainer email to `datalab@codra.fr`
* Fixed `run_with_env.py` to substitute `sys.executable` when command starts
  with `python`, ensuring the correct venv interpreter is used
