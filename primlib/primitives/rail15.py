"""15 MM RAIL -- a sliding dovetail rail, 15.00 wide, with fixed corners."""

from primlib.core import Builder, Param, Primitive, grouped

# The fixed parameters: they define the shape and are not for changing.
FIXED = (
    ("width", "15", "the outside width, between vertical tangents to the tip radii, "
                    "what calipers read"),
    ("angle", "60", "the slope of the sides, flank to the tip face, deg"),
    ("tip_radius", "1", "the radius of the two tip corners"),
    ("root_radius", "0.2", "the radius of the two root corners"),
)
# Worked in from the width. Used to build the part; not shown on the sheet.
SHAPE = (
    ("t_tip", "tip_radius / tan(angle / 2)", "tip radius's tangent length"),
    ("t_root", "root_radius / tan(angle / 2)", "root radius's tangent length, into a "
                                               "base wider than the root"),
    ("tip_hw", "width / 2 + t_tip - tip_radius", "tip half-width, sharp"),
    ("root_hw", "tip_hw - depth / tan(angle)", "root half-width, sharp"),
    ("width_check", "2 * (tip_hw - t_tip + tip_radius)", "the width, worked back from "
                                                         "the sharp corners"),
)
LENGTH = Param("length", "20", "along x")
DEPTH = Param("depth", "4", "the depth of the tapered part, root to tip")
TAPER = Param("end_taper", "0", "lead-ins at both ends: 0 none; otherwise how far the "
                                "profile changes at the very end, normal to its faces, "
                                "over the same length along x, so at 45 deg")
OFFSET = Param("printer_width_offset", "0", "added to the width in the model, half to "
                                            "each side, so that the part prints at its "
                                            "design width; not part of the fit")
RAIL = (
    LENGTH,
    DEPTH,
    Param("base_depth", "1", "the depth of the support on the root, up from it"),
    Param("base_width", "-1", "the width of the support; -1 (any negative): as wide as "
                              "the root including its radius"),
    TAPER,
    OFFSET,
)
SHAPE_CHECKS = (
    ("length", "length must be positive"),
    ("0.000001 - abs(width_check - width)", "the tip radii don't come to the width"),
    ("root_hw + printer_width_offset / 2", "depth leaves no root"),
)


def right(expr):
    """`expr`, a design half-width, as modelled on the +y side: moved out by
    half the printer offset."""
    return f"({expr}) + printer_width_offset / 2"


def left(expr):
    """The same on the -y side."""
    return f"-({right(expr)})"


def rail_points(base_hw, e="0"):
    """The rail in (y, z) as modelled, from the tip's left corner
    anticlockwise, the root at z = 0, the support `base_hw` to each side.
    `e` shrinks the tapered part, normal to its faces; the support stays."""
    tip_y, root_y = f"tip_hw - ({e}) / tan(angle / 2)", f"root_hw - ({e}) / sin(angle)"
    tip_z, tip_r = f"-depth + ({e})", f"tip_radius - ({e})"
    return [(left(tip_y), tip_z, tip_r), (right(tip_y), tip_z, tip_r),
            (right(root_y), "0", "root_radius"), (right(base_hw), "0"),
            (right(base_hw), "base_depth"), (left(base_hw), "base_depth"), (left(base_hw), "0"),
            (left(root_y), "0", "root_radius")]


def along(points, *ends):
    """Loft sections for tapered ends: `points(e)` at each end, the full
    profile `end_taper` in, each (e, x) of `ends` being one more section."""
    return [(points(e), x) for e, x in ends]


TAPER_CHECKS = (
    ("end_taper >= end_taper * 0 ? 1 : 0", "end_taper can't be negative"),
    ("tip_radius - end_taper", "end_taper must be less than the tip radius"),
    ("length - 2 * end_taper", "length is too short for its two tapered ends"),
)


def rail_body(b, points, base, suffix):
    """The rail, `points(base, e)` its section, on a support `base` wide each
    side: a loft with tapered ends when `end_taper` is over 0, else a prism."""
    return b.choose(
        "end_taper > 0",
        lambda: b.loft(suffix, along(lambda e: points(base, e), ("end_taper", "0"),
                                     ("0", "end_taper"), ("0", "length - end_taper"),
                                     ("end_taper", "length")), "yz"),
        lambda: b.prism(suffix, points(base), "yz", ("0", "length")))


def trimmed(b, body, suffix):
    """`body`, drawn on a support 1 wider each side, cut back to `base_hw`.
    With `base_width` under 0 the root's radius ends exactly at the
    support's edge, leaving no flat for the sketch: so draw it wider and
    cut it back."""
    if body is None:
        return None
    span = (("-1", "length + 1"), ("0", "base_depth + 1"))
    return b.cut(suffix, body, [
        b.box("trim_right", span[0], (right("base_hw"), right("base_hw + 2")), span[1]),
        b.box("trim_left", span[0], (left("base_hw + 2"), left("base_hw")), span[1])])


class Rail15(Primitive):
    """Four fixed parameters define its shape, and aren't for changing: `width` 15,
    `angle` 60, `tip_radius` 1 and `root_radius` 0.2. Its variable
    parameters are `length`, `depth`, `base_depth`, `base_width` and
    `printer_width_offset`. The rail has no tolerance. The full dimensioned
    specification, with the working, is `rail15_spec.html`.

    **The width is 15.00 by design:** everything else is worked from it, and
    it is measured where calipers measure it, between vertical tangents to
    the tip radii. It doesn't depend on `depth` or on the root.

    The rail runs along x from 0 to `length`, centred on y = 0, its root at
    z = 0, its tip at z = -`depth`, and its support above the root. A
    `rail15_housing` built at the same origin sits around it, mated.

    The root radius is always there and always runs its full turn, into the
    support's underside, so the support can't be left out: `base_depth`
    must be more than 0. With `base_width` -1 the support is as wide as the
    root including its radius, so the radius ends exactly at the support's
    edge. Otherwise `base_width` must be wider than that. Whether
    `base_width` is negative is fixed when the part is built: rebuild after
    changing its sign.

    `end_taper` is an option, 0 (off) by default: lead-ins at both ends, so
    the rail finds its way into a housing. Over the last `end_taper` of its
    length the tapered part shrinks by `end_taper`, normal to its faces, so
    at 45 degrees along x, the tip radius going down to match. The support
    doesn't change. Between the lead-ins the profile is exact, and that's
    where to measure the width. The choice of on or off is fixed when the
    part is built: rebuild after changing it.

    `printer_width_offset` is added to the width in the model, half to each
    side, across y only, so the depth, angle and radii stay exact. It isn't
    part of the fit. To set it, print at 0, measure the width, and use 15 -
    measured.
    """

    title = "15 mm rail"
    params, groups = grouped(("Variable", RAIL))
    fixed = FIXED
    derived = SHAPE + (
        ("base_hw", "base_width < base_width * 0 ? root_hw + t_root : base_width / 2",
         "the support's half-width"),
    )
    derived_on_page = False
    checks = SHAPE_CHECKS + TAPER_CHECKS + (
        ("(depth - end_taper) / sin(angle) - (tip_radius - end_taper) / tan(angle / 2) - t_root",
         "depth is too small for end_taper: the flanks are too short for their radii"),
        ("depth / sin(angle) - t_tip - t_root", "depth is too small: the flanks are too "
                                                "short for their radii"),
        ("base_depth", "base_depth must be more than 0: the root radius needs the support"),
        ("base_width < base_width * 0 ? 1 : base_width / 2 - root_hw - t_root",
         "base_width is narrower than the root and its radius"),
    )
    fits = (("rail15_housing", "the rail slid into a housing built at the same origin"),)
    views = (
        ("front", "u", ("0", "-width / 2", "tip_radius - depth"),
         ("0", "width / 2", "tip_radius - depth"), 1, "width"),
        ("front", "v", ("0", "-root_hw", "-depth"), ("0", "-root_hw", "0"), 1, "depth"),
        ("front", "v", ("0", "base_hw", "0"), ("0", "base_hw", "base_depth"), -1, "base_depth"),
        ("front", "angle", ("0", "tip_hw", "-depth"),
         (("0", "tip_hw - 3", "-depth"), ("0", "root_hw", "0")), 2.5, "angle"),
        ("front", "a", ("0", "width / 2 - tip_radius", "tip_radius - depth"),
         ("0", "width / 2", "tip_radius - depth"), 0, "tip_radius"),
        ("front", "a", ("0", "root_hw + t_root", "-root_radius"),
         ("0", "root_hw + t_root - root_radius", "-root_radius"), 0, "root_radius"),
        ("side", "u", ("0", "0", "-depth"), ("length", "0", "-depth"), 1, "length"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        result = b.choose("base_width >= 0", lambda: rail_body(b, rail_points, "base_hw", None),
                          lambda: trimmed(b, rail_body(b, rail_points, "base_hw + 1", "rail"), None))
        return result and b.finish(result)
