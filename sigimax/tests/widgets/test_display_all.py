# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Display all SigimaX widgets
----------------------------

This script displays all widgets from :mod:`sigimax.widgets` using data
implementations found in the test modules :mod:`sigimax.tests.widgets`
and :mod:`sigimax.tests.hdf5`.
"""

# guitest: show

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

import numpy as np
from guidata.qthelpers import exec_dialog, qt_app_context
from sigima.objects import NormalDistribution1DParam
from sigima.tests.data import (
    create_noisy_gaussian_image,
    create_noisy_signal,
    create_paracetamol_signal,
    get_test_signal,
)
from sigima.tools.signal.peakdetection import peak_indices

from sigimax.env import execenv
from sigimax.tests import helpers, sigimax_test_app_context
from sigimax.tests.hdf5.test_h5browser_app import create_h5browser_dialog
from sigimax.widgets import fitdialog as fdlg
from sigimax.widgets.imagebackground import ImageBackgroundDialog
from sigimax.widgets.logviewer import exec_sigimax_logviewer_dialog
from sigimax.widgets.signalbaseline import SignalBaselineDialog
from sigimax.widgets.signalcursor import SignalCursorDialog
from sigimax.widgets.signaldeltax import SignalDeltaXDialog
from sigimax.widgets.signalpeak import SignalPeakDetectionDialog


def display_signal_baseline_dialog() -> None:
    """Display the signal baseline selection dialog."""
    execenv.print("--- SignalBaselineDialog ---")
    sig = create_paracetamol_signal()
    dlg = SignalBaselineDialog(sig)
    dlg.resize(640, 480)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    execenv.print(f"  baseline: {dlg.get_baseline()}")
    execenv.print(f"  X range: {dlg.get_x_range()}")


def display_signal_cursor_dialog_horizontal() -> None:
    """Display the signal cursor dialog in horizontal mode."""
    execenv.print("--- SignalCursorDialog (horizontal) ---")
    sig = create_paracetamol_signal()
    dlg = SignalCursorDialog(signal=sig, cursor_orientation="horizontal")
    dlg.resize(640, 480)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    x, y = dlg.get_cursor_position()
    execenv.print(f"  cursor position: x={x}, y={y}")


def display_signal_cursor_dialog_vertical() -> None:
    """Display the signal cursor dialog in vertical mode."""
    execenv.print("--- SignalCursorDialog (vertical) ---")
    sig = create_paracetamol_signal()
    dlg = SignalCursorDialog(signal=sig, cursor_orientation="vertical")
    dlg.resize(640, 480)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    x, y = dlg.get_cursor_position()
    execenv.print(f"  cursor position: x={x}, y={y}")


def display_signal_deltax_dialog() -> None:
    """Display the signal delta X dialog."""
    execenv.print("--- SignalDeltaXDialog ---")
    sig = create_paracetamol_signal()
    dlg = SignalDeltaXDialog(signal=sig)
    dlg.resize(640, 480)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    y = dlg.get_y_value()
    x0, y0, x1, y1 = dlg.get_coords()
    execenv.print(f"  y={y}, coords=({x0}, {y0}, {x1}, {y1})")


def display_signal_peak_detection_dialog() -> None:
    """Display the signal peak detection dialog."""
    execenv.print("--- SignalPeakDetectionDialog ---")
    s = get_test_signal("paracetamol.txt")
    dlg = SignalPeakDetectionDialog(s)
    dlg.resize(640, 300)
    plot = dlg.get_plot()
    plot.set_axis_limits(plot.xBottom, 16, 30)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    execenv.print("  peaks:")
    execenv.pprint(dlg.get_peaks())
    execenv.print(f"  min_dist: {dlg.get_min_dist()}")


def display_image_background_dialog() -> None:
    """Display the image background dialog."""
    execenv.print("--- ImageBackgroundDialog ---")
    img = create_noisy_gaussian_image()
    xcoords = np.linspace(0, 10, img.data.shape[1])
    img.set_coords(xcoords, 0.02 * xcoords**3)
    dlg = ImageBackgroundDialog(img)
    dlg.resize(640, 480)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)
    if execenv.unattended:
        dlg.test_compute_background()
    execenv.print(f"  background: {dlg.get_background()}")
    execenv.print(f"  rect coords: {dlg.get_rect_coords()}")


def display_fit_dialogs() -> None:
    """Display all curve fitting dialogs."""
    execenv.print("--- Fit Dialogs ---")
    s1 = get_test_signal("paracetamol.txt")
    peakidx = peak_indices(s1.y)
    s2 = create_noisy_signal(NormalDistribution1DParam.create(sigma=5.0))
    s3 = get_test_signal("gaussian_fit.txt")
    s4 = get_test_signal("piecewiseexponential_fit.txt")

    ep = execenv.print
    tn = helpers.get_default_test_name

    ep("  Polynomial fit:")
    ep(fdlg.polynomial_fit(s2.x, s2.y, 4, name=tn("00")))
    ep("  Linear fit:")
    ep(fdlg.linear_fit(s2.x, s2.y, name=tn("01")))
    ep("  Gaussian fit:")
    ep(fdlg.gaussian_fit(s3.x, s3.y, name=tn("02")))
    ep("  Lorentzian fit:")
    ep(fdlg.lorentzian_fit(s3.x, s3.y, name=tn("03")))
    ep("  Multi-Gaussian fit:")
    ep(fdlg.multigaussian_fit(s1.x, s1.y, peakidx, name=tn("04")))
    ep("  Multi-Lorentzian fit:")
    ep(fdlg.multilorentzian_fit(s1.x, s1.y, peakidx, name=tn("05")))
    ep("  Voigt fit:")
    ep(fdlg.voigt_fit(s3.x, s3.y, name=tn("06")))
    ep("  Exponential fit:")
    ep(fdlg.exponential_fit(s2.x, s2.y, name=tn("07")))
    ep("  Sinusoidal fit:")
    ep(fdlg.sinusoidal_fit(s2.x, s2.y, name=tn("08")))
    ep("  CDF fit:")
    ep(fdlg.cdf_fit(s2.x, s2.y, name=tn("09")))
    ep("  Planckian fit:")
    ep(fdlg.planckian_fit(s3.x, s3.y, name=tn("10")))
    ep("  Two-half Gaussian fit:")
    ep(fdlg.twohalfgaussian_fit(s3.x, s3.y, name=tn("11")))
    ep("  Piecewise exponential fit:")
    ep(fdlg.piecewiseexponential_fit(s4.x, s4.y, name=tn("12")))


def display_logviewer_dialog() -> None:
    """Display the log viewer dialog."""
    execenv.print("--- LogViewer Dialog ---")
    exec_sigimax_logviewer_dialog()


def display_h5browser_dialog() -> None:
    """Display the HDF5 browser dialog."""
    execenv.print("--- H5BrowserDialog ---")
    fnames = helpers.get_test_fnames("*.h5")[-2:]
    dlg = create_h5browser_dialog(fnames, toggle_all=True, select_all=True)
    dlg.setObjectName(dlg.objectName() + "_00")
    exec_dialog(dlg)


def display_memory_status() -> None:
    """Display the memory status widget in the main window."""
    execenv.print("--- Memory Status Widget ---")
    with sigimax_test_app_context(console=False) as win:
        win.memorystatus.update_status()


def display_h5import() -> None:
    """Display HDF5 import in the main window."""
    execenv.print("--- HDF5 Import ---")
    with sigimax_test_app_context(console=False) as win:
        fnames = helpers.get_test_fnames("*.h5")
        if fnames:
            fname = fnames[-1]
            execenv.print(f"  Importing HDF5 file: {fname}")
            win.import_all_from_h5_file(fname)


def display_all_widgets() -> None:
    """Display all SigimaX widgets with test data."""
    with qt_app_context():
        # Signal widgets
        display_signal_baseline_dialog()
        display_signal_cursor_dialog_horizontal()
        display_signal_cursor_dialog_vertical()
        display_signal_deltax_dialog()
        display_signal_peak_detection_dialog()

        # Image widgets
        display_image_background_dialog()

        # Fit dialogs
        display_fit_dialogs()

        # Log viewer
        display_logviewer_dialog()

        # HDF5 browser
        display_h5browser_dialog()

    # Main window widgets (need their own app context)
    display_memory_status()
    display_h5import()


if __name__ == "__main__":
    display_all_widgets()
