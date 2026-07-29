# SigimaX - Reusable GUI Framework for Scientific Applications

[![license](https://img.shields.io/pypi/l/sigimax.svg)](./LICENSE)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/sigimax.svg)](https://pypi.org/project/sigimax/)

**SigimaX** is an **open-source Python framework for building Qt-based scientific desktop applications**. It provides a reusable application skeleton — main window, configuration system, embedded widgets, and HDF5 infrastructure — so that developers can focus on domain-specific features.

🔬 Developed by the [DataLab Platform Developers](https://github.com/DataLab-Platform), SigimaX is extracted from [DataLab](https://datalab-platform.com/) and powers its GUI layer.

---

## 🌟 Project & Sponsors

| Project/Sponsor                                                                                                                                                                               | Description                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a href="https://datalab-platform.com/"><img src="https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/resources/DataLab-Banner.svg" alt="DataLab logo" style="height:80px;"/></a> | Open-source platform for scientific signal and image processing, built on SigimaX.                                                                          |
| <a href="https://nlnet.nl/"><img src="https://nlnet.nl/logo/banner.svg" alt="NLnet logo" style="height:80px;width:209px;"/></a>                                                               | European non-profit supporting open-source and internet projects. SigimaX has received funding from NLnet for its development, through the DataLab project. |

---

## ✨ Highlights

- **Extensible configuration system** — `OptionField`-based settings with `get()`/`set()`/`context()` API and JSON persistence
- **Rich widget catalog** — 15 ready-to-use scientific widgets: curve fitting, peak detection, signal baseline, HDF5 browser, log viewer, wizard dialogs, and more
- **Complete HDF5 infrastructure** — built-in file browser, importer, and workspace save/load
- **Embedded Python console** — `DockableConsole` with error-to-console routing and configurable namespace
- **Production-grade status bar** — memory usage monitoring with alarm threshold, console toggle
- **PlotPy integration** — `DockablePlotWidget` and adapters for signal/image/ROI objects
- **Derivation pattern** — subclass `SigimaXOptions` + `SGMXMainWindow` + call `run()` to build a full app in minutes

---

## 💡 Use Cases

SigimaX is meant to be:

- A **framework for building scientific desktop apps** with Qt
- A **reusable main window** with menus, toolbars, docks, and HDF5 workspace management
- A **widget library** for signal/image analysis dialogs (fitting, peak detection, baseline, cursor, delta-X)
- A **configuration backbone** for apps that need persistent user preferences

---

## 📖 Design Philosophy

SigimaX separates the **generic application skeleton** from **domain-specific logic**. Derived applications follow a three-step pattern:

1. **Subclass `SigimaXOptions`** to add application-specific configuration fields
2. **Subclass `SGMXMainWindow`** to customize menus, toolbars, and dock widgets
3. **Call `sigimax.app.run()`** to launch the application with splash screen support

This architecture is proven in production: [DataLab](https://datalab-platform.com/) is built entirely on this derivation pattern.

### Position in the Stack

```text
End-user apps (DataLab, custom scientific apps)
         ↓  subclass / configure
      SigimaX            ← THIS PROJECT (framework layer)
         ↓  depends on
   Sigima (computation) + PlotPy + guidata + PythonQwt
         ↓
     NumPy / SciPy / Qt
```

---

## 🚀 Quick Start

```python
from sigimax.app import run
from sigimax.config import CONF as Conf, SigimaXOptions, EnumOptionField, _
from sigimax.mainwindow import SGMXMainWindow
from sigimax.widgets.plotdock import DockablePlotWidget
from sigimax.config import TypedOptionField
from plotpy.constants import PlotType

# A missing option may be initialized on first read:
color_mode = Conf.color_mode.get("auto")


# 1. Define custom options
class MyAppOptions(SigimaXOptions):
    def __init__(self):
        super().__init__()
        self.app_name.set("MyApp")
        self.greeting = TypedOptionField(
            self, "greeting", default="Hello!",
            expected_type=str, description="Startup message",
        )


# 2. Customize the main window
class MyAppMainWindow(SGMXMainWindow):
    def __init__(self, console=None, hide_on_close=False):
        Conf.app_name.set("MyApp")
        super().__init__(console=console, hide_on_close=hide_on_close)
        # Add a dockable curve plot
        self.curve_dock = DockablePlotWidget(self, PlotType.CURVE)
        dock, loc = self.curve_dock.create_dockwidget(_("Curve Viewer"))
        self.addDockWidget(loc, dock)


# 3. Launch
run(window_class=MyAppMainWindow)
```

---

## ⚙️ Architecture

```text
sigimax/
├── app.py              # Application launcher (create / run)
├── config.py           # Configuration system (SigimaXOptions, CONF singleton)
├── env.py              # Runtime environment (verbosity, unattended mode)
├── mainwindow.py       # SGMXMainWindow (generic main window)
├── widgets/            # Reusable Qt widgets
│   ├── plotdock.py     # DockablePlotWidget
│   ├── splashscreen.py # Configurable splash screen
│   ├── h5browser.py    # HDF5 file browser
│   ├── logviewer.py    # Log viewer dialog
│   ├── status.py       # Status bar widgets (memory, console)
│   ├── fitdialog.py    # Curve fitting dialogs
│   ├── signalpeak.py   # Signal peak detection
│   ├── signalbaseline.py # Signal baseline selection
│   ├── signalcursor.py # Signal cursor selection
│   ├── signaldeltax.py # Signal delta-X measurement
│   ├── wizard.py       # Multi-page wizard dialog
│   └── ...             # File dialogs, warning/error boxes
├── h5/                 # HDF5 I/O (read/write/import)
├── adapters_plotpy/    # Converters between PlotPy/guidata and Sigima objects
├── utils/              # Qt helpers, config dir resolution
├── data/               # Icons, resources
└── locale/             # Translations (EN, FR)
```

---

## 📦 Installation

```bash
pip install sigimax
```

Or in a development environment:

```bash
git clone https://github.com/DataLab-Platform/SigimaX.git
cd SigimaX
pip install -e .
```

---

## 📚 Documentation

📖 Full documentation (in progress) is available at:
👉 <https://sigimax.readthedocs.io/>

> Want to use SigimaX as part of the full DataLab platform?
> Check out: [DataLab](https://datalab-platform.com/)

---

## 🧪 Testing

SigimaX comes with a comprehensive test suite based on `pytest` (155 tests).

### ✅ Validated Environments

The test suite has been checked with the following matrix:

- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
- **Operating systems**: Windows, Linux
- **Qt bindings**: PyQt5, PyQt6, PySide6 (future fix needed)

> ⚠️ Note: PySide6 is currently known to be not fully working in this matrix.

```bash
# Run all tests (offscreen, no GUI)
python scripts/run_with_env.py python -m pytest

# Show Qt windows during tests
python scripts/run_with_env.py python -m pytest --show-windows
```

---

## 🧠 License

SigimaX is distributed under the terms of the BSD 3-Clause license.
See [LICENSE](./LICENSE) for details.

---

## 🤝 Contributing

Bug reports, feature requests and pull requests are welcome!
See the [CONTRIBUTING](https://datalab-platform.com/en/contributing) guide to get started.

---

![Python](https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/doc/images/logos/Python.png)
![NumPy](https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/doc/images/logos/NumPy.png)
![SciPy](https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/doc/images/logos/SciPy.png)
![scikit-image](https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/doc/images/logos/scikit-image.png)
![OpenCV](https://raw.githubusercontent.com/DataLab-Platform/DataLab/main/doc/images/logos/OpenCV.png)

---

© DataLab Platform Developers
