# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
ROI Adapter Factory
-------------------

Factory functions for creating ROI adapters without circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sigima.objects.base import TypeObj


def create_roi_adapter(roi):
    """Create ROI adapter from ROI object

    Args:
        roi: ROI object

    Returns:
        ROI adapter instance
    """
    # pylint: disable=import-outside-toplevel,cyclic-import
    from sigimax.adapters_plotpy.factories import create_adapter_from_object

    return create_adapter_from_object(roi)


def create_single_roi_plot_item(single_roi, obj: TypeObj):
    """Create plot item from single ROI

    Args:
        single_roi: single ROI object
        obj: object (signal/image), for physical-indices coordinates conversion

    Returns:
        Plot item
    """
    # pylint: disable=import-outside-toplevel,cyclic-import
    from sigimax.adapters_plotpy.factories import create_adapter_from_object

    return create_adapter_from_object(single_roi).to_plot_item(obj)
