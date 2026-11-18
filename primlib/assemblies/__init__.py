"""Assembly registry: every module here defines one Assembly subclass."""

import importlib
import inspect
import pkgutil

from primlib.recipe import Assembly


def available():
    """{key: Assembly subclass} for every module in this package."""
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Assembly) and cls.__module__ == module.__name__:
                found[info.name] = cls
    return dict(sorted(found.items()))
