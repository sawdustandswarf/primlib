"""primlib: parametric, spreadsheet-driven FreeCAD primitives.

    import primlib
    pin = primlib.make("pin", doc, "Pin", diam=8)
"""

__version__ = "0.1.0"

from primlib.core import Mate, Param, Primitive, Revolved  # noqa: F401
from primlib.primitives import available


def make(key, doc, name, **kwargs):
    """Build primitive `key` (e.g. "pin"); see Primitive.make for kwargs."""
    return available()[key].make(doc, name, **kwargs)
