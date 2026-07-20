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

- **Python**: 3.9+ (`from __future__ import annotations`)
- **Core**: guidata (≥3.13.4), PlotPy (≥2.8.2), Sigima (≥1.1.0), psutil (≥5.7)
- **GUI**: Qt via QtPy (PyQt5/PyQt6/PySide6)
- **Testing**: pytest
- **Linting**: Ruff (preferred), Pylint

### Architecture

```
sigimax/
├── app.py              # Application launcher (create / run)
├── config.py           # Configuration system (SigimaXOptions, CONF singleton)
├── env.py              # ExecEnv runtime environment (verbosity, unattended)
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
├── h5/                 # HDF5 I/O (read/write/import)
├── adapters_plotpy/    # Converters between PlotPy/guidata and Sigima objects
├── utils/              # Qt helpers, config dir resolution
├── data/               # Icons, resources
├── locale/             # Translations (EN, FR)
└── tests/              # pytest suite
```

## Development Workflows

### Running Commands

**ALWAYS use `scripts/run_with_env.py`** to load `.env` before running Python commands:

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
python scripts/run_with_env.py python -m pytest sigimax/tests/derivated_app_test.py

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
    ENV_VAR = "MYAPP_OPTIONS_JSON"
    APP_NAME = "MyApp"

    def __init__(self):
        super().__init__()
        self.app_name.set("MyApp", sync_env=False)
        self.greeting = TypedOptionField(
            self, "greeting", default="Hello!",
            expected_type=str, description="Startup message",
        )
        self.unit_system = EnumOptionField(
            self, "unit_system", default="metric",
            choices=["metric", "imperial"],
            description="Default units",
        )
```

**Step 2 — Subclass `SGMXMainWindow`** for custom UI:

```python
from sigimax.mainwindow import SGMXMainWindow
from sigimax.config import CONF as Conf

class MyAppMainWindow(SGMXMainWindow):
    def __init__(self, console=None, hide_on_close=False):
        Conf.app_name.set("MyApp")
        super().__init__(console=console, hide_on_close=hide_on_close)
        self._add_custom_menus()
        self._add_custom_docks()
```

**Step 3 — Launch with `sigimax.app.run()`**:

```python
from sigimax.app import run
from sigimax.widgets.splashscreen import SplashScreenConfig

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

Embeds PlotPy plots in dock widgets:

```python
from sigimax.widgets.plotdock import DockablePlotWidget

dock = DockablePlotWidget(self, plot_type=PlotType.CURVE, title="My Plot")
self.addDockWidget(Qt.RightDockWidgetArea, dock)
```

### 5. HDF5 Workspace

The main window provides built-in HDF5 workspace management:
- `open_h5_files()` — open HDF5 files
- `save_to_h5_file()` — save workspace
- `browse_h5_files()` — browse HDF5 files with `H5BrowserDialog`

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
| HDF5 I/O + browser (`h5/`, `widgets/h5browser.py`) | Macro editor, new-object dialogs |
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

**Always define `__all__`** in every module:

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
| `sigimax/__init__.py` | Package metadata (`__version__`, URLs) |
| `sigimax/app.py` | Application launcher (`create()`, `run()`) |
| `sigimax/config.py` | Configuration system (`SigimaXOptions`, `CONF`) |
| `sigimax/env.py` | Runtime environment (`ExecEnv`, `execenv` singleton) |
| `sigimax/mainwindow.py` | `SGMXMainWindow` — generic main window |
| `sigimax/widgets/plotdock.py` | `DockablePlotWidget` — embeddable plot docks |
| `sigimax/widgets/__init__.py` | Convenience re-exports of common widgets |
| `sigimax/widgets/splashscreen.py` | `SplashScreenConfig`, `SigimaXSplashScreen` |
| `sigimax/widgets/h5browser.py` | HDF5 browser widget and dialog |
| `sigimax/h5/__init__.py` | HDF5 I/O handler |
| `sigimax/adapters_plotpy/__init__.py` | PlotPy/Sigima object converters |
| `sigimax/tests/derivated_app_test.py` | Reference example of derived application |
| `scripts/run_with_env.py` | Environment loader (loads `.env`) |
| `.env` | Local PYTHONPATH for development |

## VS Code Tasks

`.vscode/tasks.json` provides shortcuts:

- **🧽 Ruff Formatter**: Format code
- **🔦 Ruff Linter**: Lint with auto-fix
- **🧽🔦 Ruff**: Format + lint (sequential)
- **🔦 Pylint**: Pylint checks
- **🚀 Pytest**: Run tests (`--ff` flag)
- **📚 Compile translations**: Build .mo files
- **🔎 Scan translations**: Update .po files

## Related Projects

- **Sigima**: Headless computation library (sibling, upstream)
- **guidata**: Dataset/parameter framework (upstream)
- **PlotPy**: Interactive plotting (upstream)
- **PythonQwt**: Low-level Qt plotting (upstream)
- **DataLab**: Primary downstream application using SigimaX

---

**Remember**: Always use `scripts/run_with_env.py` for Python commands, wrap UI strings with `_()`, define `__all__` in every module, and follow the subclassing pattern for derived applications.
