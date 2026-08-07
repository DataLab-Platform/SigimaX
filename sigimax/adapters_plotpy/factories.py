# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
PlotPy Adapter Factories
------------------------
"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

from __future__ import annotations

__all__ = [
    "PlotPyAdapterFactory",
    "create_adapter_from_object",
    "get_adapter_factory",
    "reset_adapter_factory",
    "set_adapter_factory",
]


class PlotPyAdapterFactory:
    """Resolve the PlotPy adapter class associated with an object or plot item.

    A derived application subclasses this factory to substitute its own
    adapters or to support additional object types, then installs it with
    :func:`set_adapter_factory` so that SigimaX components use it too.
    """

    def get_adapter_class(self, object_to_adapt) -> type:
        """Return the adapter class for the given object.

        Args:
            object_to_adapt: The object to adapt (signal, image or ROI)

        Returns:
            The adapter class (instantiated with the object as sole argument)

        Raises:
            TypeError: If the object type is not supported
        """
        # pylint: disable=import-outside-toplevel
        from sigima.objects import (
            CircularROI,
            ImageObj,
            ImageROI,
            PolygonalROI,
            RectangularROI,
            SegmentROI,
            SignalObj,
            SignalROI,
        )

        from sigimax.adapters_plotpy.objects.image import ImageObjPlotPyAdapter
        from sigimax.adapters_plotpy.objects.signal import SignalObjPlotPyAdapter
        from sigimax.adapters_plotpy.roi.image import (
            CircularROIPlotPyAdapter,
            ImageROIPlotPyAdapter,
            PolygonalROIPlotPyAdapter,
            RectangularROIPlotPyAdapter,
        )
        from sigimax.adapters_plotpy.roi.signal import (
            SegmentROIPlotPyAdapter,
            SignalROIPlotPyAdapter,
        )

        if isinstance(object_to_adapt, SignalObj):
            return SignalObjPlotPyAdapter
        if isinstance(object_to_adapt, SignalROI):
            return SignalROIPlotPyAdapter
        if isinstance(object_to_adapt, SegmentROI):
            return SegmentROIPlotPyAdapter
        if isinstance(object_to_adapt, ImageObj):
            return ImageObjPlotPyAdapter
        if isinstance(object_to_adapt, RectangularROI):
            return RectangularROIPlotPyAdapter
        if isinstance(object_to_adapt, CircularROI):
            return CircularROIPlotPyAdapter
        if isinstance(object_to_adapt, PolygonalROI):
            return PolygonalROIPlotPyAdapter
        if isinstance(object_to_adapt, ImageROI):
            return ImageROIPlotPyAdapter
        raise TypeError(f"Unsupported object type: {type(object_to_adapt)}")

    def get_adapter_class_for_plot_item(self, plot_item) -> type:
        """Return the single-ROI adapter class matching the given PlotPy item.

        Args:
            plot_item: The PlotPy item to convert back into a single ROI

        Returns:
            The single-ROI adapter class

        Raises:
            TypeError: If the plot item type is not supported
        """
        # pylint: disable=import-outside-toplevel
        from plotpy.items import (
            AnnotatedCircle,
            AnnotatedPolygon,
            AnnotatedRectangle,
            AnnotatedXRange,
        )

        from sigimax.adapters_plotpy.roi.image import (
            CircularROIPlotPyAdapter,
            PolygonalROIPlotPyAdapter,
            RectangularROIPlotPyAdapter,
        )
        from sigimax.adapters_plotpy.roi.signal import SegmentROIPlotPyAdapter

        if isinstance(plot_item, AnnotatedXRange):
            return SegmentROIPlotPyAdapter
        if isinstance(plot_item, AnnotatedRectangle):
            return RectangularROIPlotPyAdapter
        if isinstance(plot_item, AnnotatedCircle):
            return CircularROIPlotPyAdapter
        if isinstance(plot_item, AnnotatedPolygon):
            return PolygonalROIPlotPyAdapter
        raise TypeError(f"Unsupported PlotPy item type: {type(plot_item)}")

    def create_adapter(self, object_to_adapt):
        """Create an adapter instance for the given object.

        Args:
            object_to_adapt: The object to adapt (signal, image or ROI)

        Returns:
            An adapter instance
        """
        return self.get_adapter_class(object_to_adapt)(object_to_adapt)


#: The currently active adapter factory. Defaults to the SigimaX base factory;
#: a derived application installs its own via :func:`set_adapter_factory`. All
#: SigimaX modules resolve adapters through :func:`get_adapter_factory` (never
#: by binding the base factory directly), so that a derived application's
#: adapters are honoured transparently regardless of import order.
_active_factory: PlotPyAdapterFactory = PlotPyAdapterFactory()


def get_adapter_factory() -> PlotPyAdapterFactory:
    """Return the currently active adapter factory.

    Returns:
        The active factory (the SigimaX base by default, or the one installed
         by a derived application via :func:`set_adapter_factory`).
    """
    return _active_factory


def set_adapter_factory(factory: PlotPyAdapterFactory) -> None:
    """Install a derived application's adapter factory as the active one.

    Args:
        factory: The factory to activate (typically a subclass of
         :class:`PlotPyAdapterFactory`).

    Raises:
        TypeError: If the factory is not a :class:`PlotPyAdapterFactory`.
    """
    if not isinstance(factory, PlotPyAdapterFactory):
        raise TypeError(
            "Cannot install adapter factory: expected a PlotPyAdapterFactory "
            f"instance, got {type(factory)}"
        )
    global _active_factory  # pylint: disable=global-statement
    _active_factory = factory


def reset_adapter_factory() -> None:
    """Restore the SigimaX base adapter factory as the active one."""
    global _active_factory  # pylint: disable=global-statement
    _active_factory = PlotPyAdapterFactory()


def create_adapter_from_object(object_to_adapt):
    """Create an adapter for the given object to integrate with PlotPy

    Args:
        object_to_adapt: The object to adapt (signal, image, ROI, or scalar result)

    Returns:
        An adapter instance
    """
    return get_adapter_factory().create_adapter(object_to_adapt)
