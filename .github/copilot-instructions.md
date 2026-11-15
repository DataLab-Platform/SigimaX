# SigimaX AI Coding Agent Instructions

## Project Overview

**SigimaX** is a reusable GUI application framework extracted from DataLab. It provides the generic "application skeleton" that any scientific computing Qt application can build upon by subclassing its main window and configuration system.

### Position in the Stack

```
End-user apps (DataLab, custom scientific apps)
         ↓  subclass / configure
      SigimaX            ← THIS PROJECT (framework layer)
         ↓  depends on
   Sigima (computation) + PlotPy + guidata + PythonQwt
         ↓
     NumPy / SciPy / Qt
```

### Technology Stack

- **Python**: 3.10+ (`from __future__ import annotations`)
- **Core**: guidata (≥3.17.2), PlotPy (≥2.12.1), Sigima (≥1.4.0), hdf5plugin (≥4.0), psutil (≥5.7)
- **GUI**: Qt via QtPy (PyQt5/PyQt6/PySide6)
- **Testing**: pytest
- **Linting**: Ruff (preferred), Pylint

### Architecture

```
sigimax/
├── app.py              # Application launcher (create / run)
├── config.py           # Configuration system (SigimaXOptions, CONF singleton)
├── env.py              # SGMXExecEnv runtime environment (verbosity, unattended)
├── mainwindow.py        # SGMXMainWindow (generic main window)
├── widgets/            # Reusable Qt widgets
│   ├── plotdock.py     # DockablePlotWidget
│   ├── splashscreen.py # Configurable splash screen
│   ├── h5browser.py    # HDF5 file browser
│   ├── logviewer.py    # Log viewer dialog
│   ├── status.py       # Status bar widgets (memory, console)
│   ├── warningerror.py # Warning/error message box
│   ├── wizard.py       # Multi-page wizard dialog
│   ├── fitdialog.py    # Curve fitting dialogs
│   ├── filedialog.py   # File dialog with multi-selection
│   ├── fileviewer.py   # Read-only file viewer
│   ├── imagebackground.py    # Image background selection
│   ├── signalbaseline.py     # Signal baseline selection
│   ├── signalcursor.py       # Signal cursor selection
│   ├── signaldeltax.py       # Signal delta-X measurement
│   └── signalpeak.py         # Signal peak detection
├── h5/                 # HDF5 browsing and import (read-only)
├── adapters_plotpy/    # Converters between PlotPy/guidata and Sigima objects
├── utils/              # Qt helpers, config dir resolution
├── data/               # Icons, resources
├── locale/             # Translations (EN, FR)
└── tests/              # pytest suite
```

## Development Workflows

### Running Commands

**ALWAYS use `scripts/run_with_env.py`** to load `.env` before running Python commands (`.env` is not versioned: create it from `.env.template`, otherwise the script fails):

```powershell
# ✅ CORRECT
python scripts/run_with_env.py python -m pytest

# ❌ WRONG - Misses local PYTHONPATH
python -m pytest
```

### Testing

```powershell
# Run all tests
python scripts/run_with_env.py python -m pytest --ff

# Run specific test
python scripts/run_with_env.py python -m pytest sigimax/tests/mainwindow/test_derived_app.py

# Show Qt windows during tests (default is offscreen)
python scripts/run_with_env.py python -m pytest --show-windows
```

**Pytest Configuration** (`conftest.py`):
- `execenv.unattended = True` (no GUI interaction by default)
- `set_validation_mode(ValidationMode.STRICT)` for tests
- `QT_QPA_PLATFORM=offscreen` unless `--show-windows` is passed
- Custom marker: `@pytest.mark.validation`

### Linting and Formatting

```powershell
# Ruff (preferred)
python scripts/run_with_env.py python -m ruff format
python scripts/run_with_env.py python -m ruff check --fix

# Pylint
python scripts/run_with_env.py python -m pylint sigimax \
    --disable=duplicate-code,fixme,too-many-arguments, \
    too-many-branches,too-many-instance-attributes,too-many-lines, \
    too-many-locals,too-many-public-methods,too-many-statements
```

### Translations

```powershell
# Scan and update .po files
python scripts/run_with_env.py python -m guidata.utils.translations scan \
    --name sigimax --directory . --copyright-holder "DataLab Platform Developers" \
    --languages fr

# Compile .mo files
python scripts/run_with_env.py python -m guidata.utils.translations compile \
    --name sigimax --directory .
```

## Core Patterns

### 1. The Derivation Pattern (Subclassing)

SigimaX is designed around **subclassing**. Derived applications follow three steps:

**Step 1 — Subclass `SigimaXOptions`** for app-specific configuration:

```python
from sigimax.config import EnumOptionField, SigimaXOptions, TypedOptionField


class MyAppOptions(SigimaXOptions):
    APP_NAME = "MyApp"

    def __init__(self):
        super().__init__()
        self.app_name.set("MyApp")
        self.greeting = TypedOptionField(
            self,
            "greeting",
            default="Hello!",
            expected_type=str,
            description="Startup message",
        )
        self.unit_system = EnumOptionField(
            self,
            "unit_system",
            default="metric",
            choices=["metric", "imperial"],
            description="Default units",
        )
```

**Step 2 — Subclass `SGMXMainWindow`** for custom UI, by overriding the hooks called during setup (see `doc/user_guide/lifecycle.rst`), not by adding widgets after `super().__init__()`:

```python
from plotpy.constants import PlotType

from sigimax.config import _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.widgets.plotdock import DockablePlotWidget


class MyAppMainWindow(SGMXMainWindow):
    def _setup_docks(self):
        # Docks added here get the saved layout and follow color theme changes
        self.plot_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.plot_dock, _("My Plot"), name="my_plot")

    def _post_setup(self, console):
        # Custom menus, toolbars and wiring, once the whole UI exists
        ...
```

**Step 3 — Install the configuration with `set_conf()`, then launch with `sigimax.app.run()`**:

```python
from sigimax.app import run
from sigimax.config import set_conf
from sigimax.widgets.splashscreen import SplashScreenConfig

set_conf(MyAppOptions())  # SigimaX modules read options through get_conf()
run(
    window_class=MyAppMainWindow,
    splash_config=SplashScreenConfig(
        image_path="myapp/data/splash.png",
        app_name="MyApp",
        app_version="1.0.0",
    ),
)
```

### 2. Configuration System

The configuration system follows Sigima's `OptionField` pattern extended for GUI apps:

```python
from sigimax.config import CONF as Conf

# Get/set options
colormap = Conf.ima_def_colormap.get()
Conf.ima_def_colormap.set("gray")

# Context manager for temporary overrides
with Conf.fft_shift_enabled.context(False):
    # FFT shift disabled in this block
    ...

# JSON persistence
Conf.save()  # Save to config file
Conf.load()  # Load from config file
```

`CONF` is the SigimaX base container. SigimaX modules read the active container through `get_conf()`: once a derived application has installed its own container with `set_conf()`, read options with `get_conf()`, not `CONF`.

**Custom option field types**:
- `TypedOptionField` — type-checked (int, str, bool, float)
- `EnumOptionField` — constrained to a set of choices
- `TupleOptionField` — fixed-length tuples
- `ImageIOOptionField` — image I/O settings (inherited from Sigima)

### 3. Widgets Package

Common widgets are re-exported from `sigimax.widgets` for convenience:

```python
# Tier 1 — direct import from package
from sigimax.widgets import H5Browser, Wizard, LogViewerWindow, SplashScreenConfig

# Tier 2 — specialized dialogs via submodule
from sigimax.widgets.fitdialog import gaussian_fit
from sigimax.widgets.signalpeak import SignalPeakDetectionDialog
```

### 4. DockablePlotWidget

Embeds PlotPy plots in dock widgets. Add them in the `_setup_docks()` hook, with `_add_dockwidget()` (which registers them in `self.docks` and gives them a stable Qt object name):

```python
from plotpy.constants import PlotType

from sigimax.widgets.plotdock import DockablePlotWidget


class MyAppMainWindow(SGMXMainWindow):
    def _setup_docks(self):
        self.plot_dock = DockablePlotWidget(self, PlotType.CURVE)
        self._add_dockwidget(self.plot_dock, _("My Plot"), name="my_plot")
```

### 5. HDF5 Workspace

The main window provides the HDF5 actions, the HDF5 browser and the workspace-state contract (modified state, save prompt on close); the derived application provides the workspace persistence:
- `open_h5_files()` — open/import HDF5 files: through the `import_dataset_from_file()` hook (a no-op in the base class) with `import_all=True` (*Open HDF5 files...*), through `browse_h5_files()` with `import_all=None` (*Browse HDF5 file...*)
- `save_to_h5_file()` — save the workspace through `save_h5_workspace()`, which the derived application must override (the base implementation raises `NotImplementedError`)
- `browse_h5_files()` — browse HDF5 files with `H5BrowserDialog`, and hand the checked datasets to `_handle_imported_objects()`

### 6. Application Launcher

```python
from sigimax.app import create, run

# create() — instantiate window with splash, return it (for embedding)
window = create(window_class=MyWindow, splash=True, console=True)

# run() — create() + enter Qt event loop (for standalone apps)
run(window_class=MyWindow, splash_config=config)
```

## What SigimaX Provides vs What Stays in DataLab

| **In SigimaX** | **Stays in DataLab** |
|---|---|
| Configuration system (`config.py`) | Signal/Image panels, processors |
| Generic main window (`mainwindow.py`) | Action handler, plugin system |
| Dockable plot widgets (`widgets/plotdock.py`) | Remote control (XML-RPC, Web API) |
| HDF5 browsing and import (`h5/`, `widgets/h5browser.py`) | Macro editor, new-object dialogs |
| Scientific dialogs (fit, baseline, peak, cursor…) | DataLab-specific UI and processing |
| Log viewer, status bar, splash screen, wizard | Object model, plot handler |
| PlotPy adapters (`adapters_plotpy/`) | Processor registration pattern |
| Environment/exec utilities (`env.py`) | Tour/tutorial features |

## Coding Conventions

### Type Annotations

```python
from __future__ import annotations
```

Always use `from __future__ import annotations` for forward references.

### Qt Imports

Use QtPy for Qt binding abstraction:

```python
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QPen, QBrush, QColor
from qtpy.QtWidgets import QWidget
```

### Imports

**Order**: Standard library → Third-party → SigimaX

```python
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
from guidata.qthelpers import create_action

from sigimax.config import CONF as Conf
from sigimax.config import _
from sigimax.mainwindow import SGMXMainWindow

if TYPE_CHECKING:
    from sigima.objects import SignalObj
```

### Module Exports

**Define `__all__`** in every new module (some existing modules, such as `app.py`, `config.py`, `utils/qthelpers.py` and the `h5/` and `adapters_plotpy/` submodules, do not define it yet):

```python
__all__ = [
    "MyClass",
    "my_function",
]
```

### Docstrings

Google-style with Args/Returns:

```python
def my_function(x: np.ndarray, param: int) -> np.ndarray:
    """One-line summary.

    Longer description if needed.

    Args:
        x: Input array description
        param: Parameter description, with long description that
         continues on next line.

    Returns:
        Output array description
    """
```

For continued lines in enumerations (args, returns), indent subsequent lines by 1 space.

### Internationalization

Wrap UI strings with `_()`:

```python
from sigimax.config import _

menu_title = _("Processing")
action_text = _("Open HDF5 files")
```

### Naming

- **Functions**: `snake_case` (e.g., `get_log_filenames`)
- **Classes**: `PascalCase` (e.g., `SGMXMainWindow`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MOD_NAME`, `DEBUG`)
- **Private methods**: `_snake_case` or `__snake_case`

## Key Files Reference

| File | Purpose |
|------|---------|
| `sigimax/_metadata.py` | Package metadata (`__version__`, URLs), re-exported by `sigimax/__init__.py` |
| `sigimax/app.py` | Application launcher (`create()`, `run()`) |
| `sigimax/config.py` | Configuration system (`SigimaXOptions`, `CONF`, `get_conf()`, `set_conf()`) |
| `sigimax/env.py` | Runtime environment (`SGMXExecEnv`, `execenv` singleton) |
| `sigimax/mainwindow.py` | `SGMXMainWindow` — generic main window |
| `sigimax/widgets/plotdock.py` | `DockablePlotWidget` — embeddable plot docks |
| `sigimax/widgets/__init__.py` | Convenience re-exports of common widgets |
| `sigimax/widgets/splashscreen.py` | `SplashScreenConfig`, `SigimaXSplashScreen` |
| `sigimax/widgets/h5browser.py` | HDF5 browser widget and dialog |
| `sigimax/h5/__init__.py` | HDF5 browsing and import (`H5Importer`, node registry) |
| `sigimax/adapters_plotpy/__init__.py` | PlotPy/Sigima object converters |
| `sigimax/tests/mainwindow/test_derived_app.py` | Reference example of derived application |
| `sigimax/tests/hdf5/test_h5_derived_app.py` | Reference example of derived application with HDF5 workspace persistence |
| `scripts/run_with_env.py` | Environment loader (loads `.env`) |
| `.env` | Local PYTHONPATH for development (created from `.env.template`) |

## VS Code Tasks

`.vscode/tasks.json` provides shortcuts:

- **🧽 Ruff Formatter**: Format code
- **🔦 Ruff Linter**: Lint with auto-fix
- **🧽🔦 Ruff**: Format + lint (sequential)
- **🔦 Pylint**: Pylint checks
- **🚀 Pytest**: Run tests (`--ff` flag)
- **📚 Compile translations**: Build .mo files
- **🔎 Scan translations**: Update .po files

## Release Notes Guidelines

**Location**: `doc/release_notes/release_MAJOR.MINOR.md` where MINOR is zero-padded to 2 digits (e.g., `release_1.00.md` for v1.0.x, `release_1.01.md` for v1.1.x).

### Dependency Version Tracking (`Requirements` section)

Every new release entry in the release notes must include a dedicated **`### Requirements ###`** section tracking minimum version updates from `pyproject.toml` (`requires-python`, `[project.dependencies]`, and relevant `[project.optional-dependencies]`).

Distinguish three categories of dependencies:

1. **DataLab-Platform** (`datalab-platform` ecosystem packages): `Sigima` (≥ 1.4.0)
2. **PlotPyStack**: `guidata` (≥ 3.17.2), `PlotPy` (≥ 2.12.1), `PythonQwt`
3. **Third-party** (and Python runtime): `Python` (`requires-python`), `hdf5plugin` (≥ 4.0), `psutil` (≥ 5.7), `PyQt5` (≥ 5.15.6), etc.

**Rules**:
- Whenever a minimum required version is bumped or a dependency is added/updated in `pyproject.toml`, document it in the release's `### Requirements ###` section, grouped/distinguished according to these three categories, and briefly state the user-visible reason for the update.
- Keep `requirements.txt` and `doc/requirements.rst` synchronized with `pyproject.toml` (via `python -m guidata.utils.genreqs all`), along with the French documentation `.po` catalogs.

**Example**:
```markdown
### Requirements ###

* **DataLab-Platform**:
  * Sigima ≥ 1.4.0 is required: the HDF5 import modules use its experimental-source API, integer conversions use its precision-preserving converter, and the tooltips of rectangular ROIs use its pixel-range conversions.
* **PlotPyStack**:
  * guidata ≥ 3.17.2 is required: the splash screen and the watermark of empty plots use its `get_pixmap` function on high-DPI displays, and windows follow the color theme on Windows.
  * PlotPy ≥ 2.12.1 is required: auto downsampling of signals relies on its min/max downsampling.
* **Third-party**:
  * Python ≥ 3.10 is now required. Python 3.9 users must keep an earlier compatible release.
  * hdf5plugin ≥ 4.0 is required, for the HDF5 compression filters of detector data.
```

## Releasing

Follow [RELEASING.md](../RELEASING.md). **Never create a GitHub release by hand** (with `gh release create` or from the GitHub web page): pushing a tag `vX.Y.Z` (or `vX.Y.Z-rcN`) makes `.github/workflows/release.yml` create a draft release, and only publishing that draft uploads to PyPI (or TestPyPI). Each version needs a `## SigimaX Version X.Y.Z ##` section in the release notes: it becomes the description of the GitHub release.

## Related Projects

- **Sigima**: Headless computation library (sibling, upstream)
- **guidata**: Dataset/parameter framework (upstream)
- **PlotPy**: Interactive plotting (upstream)
- **PythonQwt**: Low-level Qt plotting (upstream)
- **DataLab**: Primary downstream application using SigimaX

---

**Remember**: Always use `scripts/run_with_env.py` for Python commands, wrap UI strings with `_()`, define `__all__` in every new module, and follow the subclassing pattern for derived applications.
