"""PLATE -- rectangular plate with a grid of screw holes."""

from primlib.core import Machined, Param
from primlib.primitives.hole import Hole


class Plate(Machined):
    """**Deprecated: part of the old ring hinge (`hinge_deprecated`), used only
    by `latch`.** Don't use it for new work; it goes when the latch moves to
    `hinge`.

    A rectangular plate `length` (x) by `width` (y) by `thickness` (z),
    its corner at the origin, with a grid of `screws_x` by `screws_y`
    screw holes. The holes are spread evenly between the edge margins:
    the outer hole centres sit `edge_margin` in from each edge, and a
    count of 1 centres the holes in that direction.

    The holes are the screw hole primitive -- `hole_type` 0 none, 1 plain,
    2 countersunk, 3 counterbored, heads at the top face -- with the same
    parameters, so a sheet edit switches the hole type, counts or sizes.
    Built as a box minus a Draft array of one hole tool; the array is moved
    clear of the plate when `hole_type` is 0.
    """

    title = "Plate"
    params = (
        Param("length", "40", "size along x"),
        Param("width", "20", "size along y"),
        Param("thickness", "5", "size along z"),
        Param("screws_x", "3", "number of screws along x"),
        Param("screws_y", "2", "number of screws along y"),
        Param("edge_margin", "5", "plate edge to the nearest screw centre"),
    ) + tuple(p for p in Hole.params if p.name != "thickness")
    derived = Hole.derived + (
        ("pitch_x", "screws_x > 1 ? (length - 2 * edge_margin) / (screws_x - 1) : 0",
         "screw spacing along x"),
        ("pitch_y", "screws_y > 1 ? (width - 2 * edge_margin) / (screws_y - 1) : 0",
         "screw spacing along y"),
        ("x0", "screws_x > 1 ? edge_margin : length / 2", "first screw centre, x"),
        ("y0", "screws_y > 1 ? edge_margin : width / 2", "first screw centre, y"),
        ("drop", "hole_type == 0 ? -(3 * thickness + 10) : 0",
         "moves the holes clear of the plate for hole_type 0"),
    )
    checks = Hole.checks + (
        ("screws_x", "screws_x must be at least 1"),
        ("screws_y", "screws_y must be at least 1"),
        ("length - 2 * edge_margin", "length leaves no room inside the edge margins"),
        ("width - 2 * edge_margin", "width leaves no room inside the edge margins"),
        ("hole_type == 0 ? 1 : edge_margin - r_b",
         "edge_margin is too small: the holes break out of the plate edge"),
        ("hole_type == 0 ? 1 : (screws_x > 1 ? pitch_x - 2 * r_b : 1)",
         "screws_x is too many: the holes overlap"),
        ("hole_type == 0 ? 1 : (screws_y > 1 ? pitch_y - 2 * r_b : 1)",
         "screws_y is too many: the holes overlap"),
    )
    section_y = "y0"

    @classmethod
    def body(cls, b):
        blank = b.box("blank", ("0", "length"), ("0", "width"), ("0", "thickness"))
        # One hole tool bound to the plate's params (no rows of its own).
        tool = b.part(Hole, "hole")
        if tool is None:
            return None
        holes = b.grid("holes", tool, {"x": ("screws_x", "x0", "pitch_x"), "y": ("screws_y", "y0", "pitch_y")})
        return blank, [b.move(holes, (None, None, "drop"))]
