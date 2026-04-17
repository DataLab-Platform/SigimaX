# SigimaX - DataLab modules to import

## Main purpose

The main purpose of the SigimaX library is to extract generic application components from DataLab into an independent module, facilitating the creation of scientific applications.

This file lists all identified DataLab modules and shows which ones will be integrated into the SigimaX library.

## Features goal list

Here is the functional content targeted for the SigimaX library (cf. NLnet project specs):

- **Application configuration management**: settings, parameters, preferences
- **Log handler**: logger, dock display, verbosity (information)
- **Files/projects history**: recent files/projects tracking
- **Main window base structure**: menus, toolbars, docks
- **HDF5 Explorer**: IO module and widget
- **Reusable GUI widgets**: a subset of those defined in `datalab.widgets`
- **Resources management**: icons, paths, locale and translations
- **Standard dialog infrastructure**: e.g., application welcome screen

## Modules

Legend: ✅ = Include in SigimaX | ❌ = Exclude (DataLab-specific) | ❓ = To be discussed | ⚠️ = Proceed with caution

| Module                  | ⬇️   | Description                                                              | Note                                                 | Dependencies                    |
| ----------------------- | --- | ------------------------------------------------------------------------ | ---------------------------------------------------- | ------------------------------- |
| adapters_metadata       | ❌   | Sigima adapters TableResult, GeometryResult -> SignalObject, ImageObject |                                                      | sigima                          |
| adapters_plotpy         | ✅⚠️  | Adapters/converters for PlotPy, guidata objects <-> Sigima objects       | Check consistency with `sigima.viz` (future feature) | sigima, plotpy, guidata         |
| control                 | ❌   | XML-RPC remote control                                                   | DataLab-specific                                     |                                 |
| data/icons              | ✅   | SVG icons used in widgets and windows                                    | Case-by-case                                         |                                 |
| data/logo               | ❌   | DataLab app logo                                                         | DataLab-specific                                     |                                 |
| data/tests              | ✅❓  | H5 empty and test files                                                  | Case-by-case                                         |                                 |
| data/tutorials          | ❌   | JPG images used for tutorials                                            | DataLab-specific                                     |                                 |
| gui/actionhandler       | ❌   | Module handles app actions (menus, toolbars, context menu, ...)          | DataLab-specific                                     | sigima, guidata, qt             |
| gui/docks               | ✅⚠️  | Module provides the dockable widgets for main window                     | Minimal support                                      | guidata, plotpy, qt, sigima     |
| gui/h5io                | ❌   | Module provides H5 open/save into/from data model/main window            | DataLab-specific                                     | guidata, qt, sigima, h5         |
| gui/macroeditor         | ❌   | Module provides the macro editor widget (Python console)                 | DataLab-specific                                     | guidata, qt, env                |
| gui/main                | ✅❓  | Module provides the main window                                          | Extract a generic main window                        | guidata, plotpy, qt, sigima     |
| gui/newobject           | ❌   | Module provides new object creation GUI (signals and images)             |                                                      | guidata, plotpy, qt, sigima     |
| gui/objectview          | ❌   | Widgets to display object (signal/image) trees                           |                                                      | guidata, qt, sigima             |
| gui/panel               | ❌   | GUI panel objects: Signal Panel, Image Panel, Macro Panel                |                                                      | qt, h5, guidata, plotpy, sigima |
| gui/plothandler         | ❌   | Handling PlotPy plot items for representing signals and images           |                                                      | plotpy, qt, sigima              |
| gui/processor           | ❌   | Processor objects (link between Sigima and GUI)                          |                                                      | qt, guidata, plotpy, sigima     |
| gui/profiledialog       | ❌   | Profile extraction dialog                                                |                                                      | guidata, plotpy, qt, sigima     |
| gui/roieditor           | ❌   | ROI editor widgets for signals and images                                | Consider moving to widgets/                          | guidata, plotpy, qt, sigima     |
| gui/roigrideditor       | ❌   | ROI grid editor for structured ROI management                            | Related to roieditor.py                              | guidata, plotpy, qt, sigima     |
| gui/settings            | ❓   | Module for app settings dialog and related classes                       | Future feature                                       | guidata, qt, plotpy             |
| gui/tour                | ❌   | GUI DataLab tour features (tutorials, demo)                              | DataLab-specific                                     |                                 |
| h5                      | ✅   | HDF5 IO module file handler (read/write)                                 | ⚠️ 'h5/native': DataLab-specific                      | h5py                            |
| locale                  | ✅   | Translations (EN-FR)                                                     |                                                      |                                 |
| plugins                 | ❌   | DataLab plugins system (directory)                                       | DataLab-specific                                     |                                 |
| plugins.py              | ❌   | Plugin base classes and registry                                         | DataLab-specific                                     |                                 |
| tests                   | ✅❓  | Test units                                                               | Case-by-case                                         |                                 |
| utils/conf              | ✅   | Configuration utilities                                                  |                                                      | qt, guidata                     |
| utils/dephash           | ❌   | Module checking dependencies with respect to a reference                 | DataLab-specific                                     |                                 |
| utils/qthelpers         | ✅   | Qt utilities                                                             |                                                      | qt, guidata                     |
| utils/strings           | ✅❓  | Generates HTML diff between two strings (used in H5 test units)          |                                                      |                                 |
| utils/tests             | ✅❓  | Test utilities                                                           | Case-by-case                                         |                                 |
| webapi                  | ❌   | Web API module                                                           | DataLab-specific                                     |                                 |
| widgets/connection      | ❌   | Connection dialog for proxy client (remote control)                      | DataLab-specific                                     |                                 |
| widgets/filedialog      | ✅   | File dialog widget (enhanced QFileDialog with multi-file preselection)   |                                                      | guidata, qt                     |
| widgets/fileviewer      | ✅   | File viewer widget                                                       |                                                      | guidata, qt                     |
| widgets/fitdialog       | ✅   | Curve fitting dialog widgets                                             |                                                      | guidata, plotpy, sigima         |
| widgets/h5browser       | ✅⚠️  | HDF5 browser module                                                      |                                                      | guidata, plotpy, qt, sigima, h5 |
| widgets/imagebackground | ✅   | Image background selection dialog                                        |                                                      | guidata, plotpy, qt, sigima     |
| widgets/instconfviewer  | ❌   | Installation configuration widget                                        | Linked with DataLab plugin system                    |                                 |
| widgets/logviewer       | ✅   | Log viewer widget                                                        |                                                      | guidata, qt, env                |
| widgets/signalbaseline  | ✅   | Signal baseline selection dialog                                         |                                                      | guidata, plotpy, sigima, qt     |
| widgets/signalcursor    | ✅   | Signal H/V cursor selection dialog                                       |                                                      | guidata, qt, plotpy, sigima     |
| widgets/signaldeltax    | ✅   | GUI dialog for analyzing signals and calculating full width at Y         |                                                      | guidata, plotpy, qt, sigima     |
| widgets/signalpeak      | ✅   | Signal peak detection feature dialog                                     |                                                      | guidata, plotpy, qt, sigima     |
| widgets/status          | ✅   | Main window status bar widgets                                           | Only `MemoryStatus`, `ConsoleStatus`                 | guidata, qt, plugins            |
| widgets/textimport      | ❌   | Text Import Wizard                                                       |                                                      | guidata, plotpy, qt, sigima     |
| widgets/warningerror    | ✅   | Warning/error message dialog box                                         |                                                      | guidata, qt                     |
| widgets/wizard          | ✅   | Wizard widget (enhanced QWizard with complete styling support)           |                                                      | qt                              |
| app.py                  | ❌   | Application launcher                                                     | DataLab-specific                                     |                                 |
| config.py               | ✅❓  | Application configuration                                                | Must be made generic                                 | sigima, plotpy, guidata         |
| env.py                  | ✅   | Environment utilities                                                    |                                                      | guidata                         |
| objectmodel.py          | ❌   | Object model definitions                                                 |                                                      | sigima                          |
