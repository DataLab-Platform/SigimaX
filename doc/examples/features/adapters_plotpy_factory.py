# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
PlotPy Adapter Factory
========================

SigimaX converts Sigima objects (:class:`~sigima.objects.SignalObj`,
:class:`~sigima.objects.ImageObj`, ROIs) to/from PlotPy plot items through a
small set of adapter classes. Which adapter class is used for a given object
is resolved by :class:`~sigimax.adapters_plotpy.factories.PlotPyAdapterFactory`
— a single, overridable indirection point.

This is useful when a derived application:

- adds a **new object type** that needs its own PlotPy rendering, or
- wants to **substitute** one of SigimaX's built-in adapters (e.g. to draw
  images with a custom colormap policy) without touching SigimaX itself.
"""

# %%
# Importing necessary modules
# ---------------------------

import numpy as np
from sigima import SignalObj

from sigimax.adapters_plotpy import (
    SignalObjPlotPyAdapter,
    create_adapter_from_object,
)
from sigimax.adapters_plotpy.factories import (
    PlotPyAdapterFactory,
    get_adapter_factory,
    reset_adapter_factory,
    set_adapter_factory,
)

# %%
# Default resolution
# --------------------
#
# :func:`~sigimax.adapters_plotpy.create_adapter_from_object` asks the
# *currently active* factory
# (:func:`~sigimax.adapters_plotpy.factories.get_adapter_factory`)
# for the right adapter class, then instantiates it. Out of the box, this is
# a :class:`~sigimax.adapters_plotpy.factories.PlotPyAdapterFactory` that
# dispatches on the Sigima object type.

signal = SignalObj()
signal.set_xydata(np.linspace(0, 10, 100), np.sin(np.linspace(0, 10, 100)))
signal.title = "Demo signal"

adapter = create_adapter_from_object(signal)
print(f"Adapter class: {type(adapter).__name__}")
assert isinstance(adapter, SignalObjPlotPyAdapter)

item = adapter.make_item()
print(f"PlotPy item: {type(item).__name__}")

# %%
# Overriding the factory
# ------------------------
#
# Subclass :class:`~sigimax.adapters_plotpy.factories.PlotPyAdapterFactory`
# and override
# :meth:`~sigimax.adapters_plotpy.factories.PlotPyAdapterFactory.get_adapter_class`,
# delegating to ``super()`` for the types you don't need to change. Install it
# with :func:`~sigimax.adapters_plotpy.factories.set_adapter_factory` so that
# every SigimaX component (dock widgets, HDF5 browser preview, ROI editing)
# picks it up transparently.


class LoggingAdapterFactory(PlotPyAdapterFactory):
    """Adapter factory that logs every resolution (for demonstration)."""

    def get_adapter_class(self, object_to_adapt) -> type:
        adapter_class = super().get_adapter_class(object_to_adapt)
        print(f"Resolved {type(object_to_adapt).__name__} -> {adapter_class.__name__}")
        return adapter_class


set_adapter_factory(LoggingAdapterFactory())
try:
    adapter = create_adapter_from_object(signal)
    print(f"Active factory: {type(get_adapter_factory()).__name__}")
finally:
    # Always restore the base factory so later examples/tests are unaffected
    reset_adapter_factory()

# %%
# Summary
# -------
#
# - :func:`~sigimax.adapters_plotpy.create_adapter_from_object` is the single
#   entry point application code should use to go from a Sigima object to a
#   PlotPy adapter
# - :func:`~sigimax.adapters_plotpy.factories.get_adapter_factory` /
#   :func:`~sigimax.adapters_plotpy.factories.set_adapter_factory` let a
#   derived application install its own factory once, globally
# - Override
#   :meth:`~sigimax.adapters_plotpy.factories.PlotPyAdapterFactory.get_adapter_class`
#   for object-to-item resolution and ``get_adapter_class_for_plot_item()``
#   for the reverse (item-to-ROI) direction
# - Call :func:`~sigimax.adapters_plotpy.factories.reset_adapter_factory` to
#   restore the SigimaX base factory (mostly useful in tests)
