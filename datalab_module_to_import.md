# SigimaX - Datalab modules to import

### Main purpose
The main purpose of the SigimaX lib is to extract main modules from the Datalab application to be reuse outside indepedantly for others app.

This file list all identified Datalab modules and show which one will be integrated in SigimaX library.

Here is a the features goal list for the SigimaX library : 
- Application configuration manager : settings, parameters, preferences  
- Logs handler : logger, dock display, verbosity (infomation)
- Files/projets history
- Main window base structure : menu, toolbars, docks
- Reusable GUI widgets
- HDF5 Explorer : IO Module and widget
- Main structure for standardized Dialog Boxes (expl : app main window)
- Resources Manager : icons, access path, locale and translation

### Modules
| Module                  | ⬇️ | Description                                                              | Note                                 | Deps                            |
| ----------------------- | ---- | ------------------------------------------------------------------------ | ------------------------------------ | ------------------------------- |
| adapters_metadata       | ✅   | Sigima adapters TableResult, GeometryResult -> SignalObject, ImageObject |                                      | sigima                          |
| adapters_plotpy         | ✅   | Adapters/converters for plotpy, guidata objects <-> sigima objects       |                                      | sigima, plotpy, guidata         |
| control                 | ❌   | XML-RPC Remote control                                                   |                                      |                                 |
| data/icon               | ✅   | SVG icon use in widget and windows                                       |                                      |                                 |
| data/logo               | ❌   | Datalab app logo                                                         |                                      |                                 |
| data/tests              | ✅❓ | H5 empty and tests files                                                 |                                      |                                 |
| data/tutorials          | ✅❓ | JPG images use for tutorials                                             |                                      |                                 |
| gui/panels              | ✅   | GUI panel objects: Signal Panel, Image Panel and Macro Panel             | Macro Panel ?                        | qt, h5, guidata, plotpy, sigima |
| gui/processor           | ✅   | Processor objects (link between sigima and GUI)                          |                                      | qt, guidata, plotpy, sigima     |
| gui/actionhandler       | ✅   | Module handles app actions(menus, toolbars, context menu,...)            |                                      | sigima, guidata, qt             |
| gui/docks               | ✅   | Module provides the dockable widgets for main window                     |                                      | guidata, plotpy, qt, sigima     |
| gui/h5io                | ✅   | Module provides the H5 open/save into/from data model/main window.       |                                      | guidata, qt, sigima, h5         |
| gui/macroeditor         | ✅   | Module provides the macro editor widget (python console)                 | archi -> to widget/ ?                | guidata, qt, env                |
| gui/main                | ✅❓ | Module provides the main window                                          | Configurable ?                       | guidata, plotpy, qt, sigima     |
| gui/newobject           | ✅   | Module provides New object creation GUI (signals an img)                 |                                      | guidata, plotpy, qt, sigima     |
| gui/objectview          | ✅   | Widgets to display object (signal/image) trees.                          |                                      | guidata, qt, sigima             |
| gui/plothandler         | ✅   | Handling PlotPy plot items for representing signals and images           |                                      | plotpy, qt, sigima              |
| gui/profiledialog       | ✅   | profile extraction dialog                                                |                                      |                                 |
| gui/roieditor           | ✅   | ROI editor widgets for signals and images.  (archi -> to widget/ ? )     | (archi ?) see also: roigrideditor.py | guidata, plotpy, qt, sigima     |
| gui/settings            | ✅   | Module for app settings dialog and related classes                       |                                      | guidata, qt, plotpy             |
| gui/tour                | ❌   | GUI Datalab tour features (tutorials, demo)                              |                                      |                                 |
| h5                      | ✅   | HDF5 IO Module file handler (read/write)                                 |                                      | h5                              |
| locale                  | ✅   | Translations (EN-FR)                                                     |                                      |                                 |
| plugins                 | ❌   | Datalab plugins system                                                   |                                      |                                 |
| tests                   | ✅   | Tests Units                                                              | case-by-case                         |                                 |
| utils/conf              | ✅   | Configuration utilities                                                  |                                      | qt, guidata                     |
| utils/dephash           | ❌   | Module checking dependencies with respect to a reference                 |                                      |                                 |
| utils/qthelpers         | ✅   | Qt utilities                                                             |                                      | qt, guidata                     |
| utils/string            | ✅❓ | Generates HTML diff between two strings  (use in test units H5)          |                                      |                                 |
| widgets/connection      | ❌   | Connection dialog for proxy client (remote control)                      |                                      |                                 |
| widgets/filedialog      | ✅   | file dialog widget (enhanced QFileDialog with multi file preselection)   |                                      | guidata, qt                     |
| widgets/fileviewer      | ✅   | file viewer widget                                                       |                                      | guidata, qt                     |
| widgets/fitdialog       | ✅   | Curve fitting dialog widgets                                             |                                      | guidata, plotpy, sigima         |
| widgets/h5browser       | ✅   | HDF5 browser module                                                      |                                      | guidata, plotpy, qt, sigima, h5 |
| widgets/imagebackground | ✅   | Image background selection dialog                                        |                                      | guidata, plotpy, qt, sigima     |
| widgets/instconfviewer  | ❌❓ | Installation configuration widget                                        | linked with datalab plugin system    |                                 |
| widgets/logviewer       | ✅   | Log viewer widget                                                        |                                      | guidata, qt, env                |
| widgets/signalbaseline  | ✅   | Signal base line selection dialog                                        |                                      | guidata, plotpy, sigima, qt     |
| widgets/signalcursor    | ✅   | Signal h/v cursor selection dialog                                       |                                      | guidata, qt, plotpy, sigima     |
| widgets/signaldeltax    | ✅   | GUI dialog for analyzing signals and calculating full width at Y.        |                                      | guidata, plotpy, qt, sigima     |
| widgets/signalpeak      | ✅   | Signal peak detection feature dialog                                     |                                      | guidata, plotpy, qt, sigima     |
| widgets/status          | ❌❓ | Main window status bar widgets                                           | linked with plugin and remote system | guidata, qt, plugins            |
| widgets/textimport      | ✅   | Text Import Wizard                                                       |                                      | guidata, plotpy, qt, sigima     |
| widgets/warningerror    | ✅   | warning/error message dialog box                                         |                                      | guidata, qt                     |
| widgets/wizard          | ✅   | Wizard Widget (enhanced QWizard with complete styling support )          |                                      | qt                              |
| app launcher            | ❌   |                                                                          | datalab/app.py                       |                                 |
| config                  | ✅❓ |                                                                          | datalab/config.py                    | sigima, plotpy, guidata         |
| objectmodel             | ✅   |                                                                          | datalab/objectmodel.py               | sigima                          |
| env                     | ✅   | environmnent utilities                                                   | datalab/env.py                       | guidata                         |
