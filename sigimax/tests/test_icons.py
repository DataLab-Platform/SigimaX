# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Icon tests
----------

SigimaX icons are SVG files, like those of guidata and PlotPy: icon names shared
with these libraries must be designated explicitly (``"sigimax:filename"``), which
requires icon file names to be unique in SigimaX.
"""

from __future__ import annotations

import collections
import os
import os.path as osp
import re

import pytest
from guidata import configtools

import sigimax
import sigimax.config  # noqa: F401  (registers SigimaX's icon path)

pytestmark = pytest.mark.unit


def _referenced_icon_names() -> set[str]:
    """Return the SVG image names referenced as string literals in SigimaX's code
    (tests excluded)"""
    names = set()
    pattern = re.compile(r"[\"']((?:[\w.]+:)?[\w\-]+\.svg)[\"']")
    root = osp.dirname(sigimax.__file__)
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath == root:
            dirnames.remove("tests")
        for filename in filenames:
            if filename.endswith(".py"):
                with open(osp.join(dirpath, filename), encoding="utf-8") as fdesc:
                    names.update(pattern.findall(fdesc.read()))
    return names


def test_unique_icon_file_names() -> None:
    """Test that SigimaX icon file names are unique"""
    root = configtools.get_module_data_path("sigimax", "data/icons")
    paths = collections.defaultdict(list)
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            paths[filename].append(osp.join(dirpath, filename))
    assert not {name: pths for name, pths in paths.items() if len(pths) > 1}


def test_referenced_icons_exist() -> None:
    """Test that the icons referenced in SigimaX's code exist and are not ambiguous
    (``ImageNameConflictWarning`` is turned into an error in the test suite)"""
    names = _referenced_icon_names()
    assert {"sigimax:image.svg", "sigimax:signal.svg"} <= names
    missing = []
    for name in sorted(names):
        try:
            configtools.get_image_file_path(name, default=None)
        except RuntimeError:
            missing.append(name)
    assert not missing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
