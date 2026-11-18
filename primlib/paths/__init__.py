"""Path registry: every module here defines one Path subclass (see core.Path)."""

import importlib
import inspect
import pkgutil

from primlib.core import Path


def available():
    """{key: Path subclass} for every module in this package."""
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Path) and cls.__module__ == module.__name__:
                found[info.name] = cls
    return dict(sorted(found.items()))
