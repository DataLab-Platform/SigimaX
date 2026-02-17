# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 import application test
"""

# guitest: show

from sigimax import app
from sigimax.env import execenv
from sigimax.tests import helpers
from sigimax.utils.qthelpers import datalab_app_context


def test_hdf5_import():
    """Testing DataLab app launcher"""
    with datalab_app_context(exec_loop=True):
        win = app.create(console=False)
        fname = helpers.get_test_fnames("*.h5")[-1]
        execenv.print(f"Importing HDF5 file: {fname}")
        win.import_h5_file(fname)


if __name__ == "__main__":
    test_hdf5_import()
