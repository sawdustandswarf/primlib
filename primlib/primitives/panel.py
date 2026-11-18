"""PANEL -- a flat sheet cut to size: a plywood panel."""

from primlib.core import Builder, Param, Primitive


class Panel(Primitive):
    """A flat sheet `length` (x) by `width` (y), `thickness` (z) thick, its
    corner at the origin: a panel cut from plywood or other sheet, as the
    hybrid case's walls are. It isn't printed; an assembly turns it into
    place, so it is cut and listed lying flat."""

    title = "Panel"
    params = (
        Param("length", "300", "size along x"),
        Param("width", "200", "size along y"),
        Param("thickness", "6.5", "the sheet's thickness, along z"),
    )
    checks = (
        ("length", "length must be positive"),
        ("width", "width must be positive"),
        ("thickness", "thickness must be positive"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        return b.finish(b.box("sheet", ("0", "length"), ("0", "width"), ("0", "thickness")))
