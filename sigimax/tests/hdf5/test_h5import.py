# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
HDF5 import application test
"""

# guitest: show

import pytest

from sigimax.env import execenv
from sigimax.tests import helpers, sigimax_test_app_context

pytestmark = pytest.mark.app


def test_hdf5_import():
    """Testing SigimaX app launcher"""
    with sigimax_test_app_context(console=False) as win:
        fname = helpers.get_test_fnames("*.h5")[-1]
        execenv.print(f"Importing HDF5 file: {fname}")
        win.import_all_from_h5_file(fname)


if __name__ == "__main__":
    test_hdf5_import()
