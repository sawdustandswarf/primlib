"""Primitive registry: every module here defines one Primitive subclass."""

import importlib
import inspect
import pkgutil

from primlib.core import Primitive


def available():
    """{key: Primitive subclass} for every module in this package."""
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Primitive) and cls.__module__ == module.__name__:
                found[info.name] = cls
    return dict(sorted(found.items()))
