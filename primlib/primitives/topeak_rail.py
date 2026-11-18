"""TOPEAK RAIL -- a tongue for a Topeak rack, with fixed sizes, its width what calipers read."""

from primlib.core import Builder, Param, Primitive, grouped
from primlib.primitives.box_edge import away
from primlib.primitives.rail15 import (LENGTH, SHAPE, SHAPE_CHECKS, TAPER, TAPER_CHECKS, left, rail_body,
                                     right, trimmed)

# The fixed parameters: they define the shape and are not for changing.
FIXED = (
    ("width", "61.4", "the outside width, between vertical tangents to the tip radii, what "
                      "calipers read on the print"),
    ("angle", "60", "the slope of the sides, flank to the tip face, deg"),
    ("depth", "6.35", "the depth of the tongue, root to tip (1/4\", set by the rack)"),
    ("tip_radius", "0.7", "the radius of the two tip corners"),
    ("root_radius", "1", "the radius of the two root corners"),
    ("groove_width", "19.95", "the width of the centre groove at the tip face"),
    ("groove_depth", "1.2", "the depth of the centre groove, up from the tip face"),
    ("groove_angle", "45", "the slope of the groove's sides to the tip face, deg"),
)
RAIL = (
    LENGTH,
    Param("base_depth", "2", "the depth of the support on the root, up from it"),
    Param("base_width", "-1", "the width of the support; -1 (any negative): as wide as "
                              "the root including its radius"),
    TAPER,
    Param("printer_width_offset", "0.2", "added to the width in the model, half to each side, "
                                         "so that the part prints at its design width; 0.2 is "
                                         "PETG on the test printer, standing on end; not part of the fit"),
)
SCREWS = (
    Param("screws", "0", "1 for two rows of countersunk holes up through the tongue, "
                         "heads in the tip face, to screw it to a panel; 0 for none"),
    Param("screw_y", "18.4", "each row's line off the centre line, along y"),
    Param("drill_inset", "6", "the rows' first and last holes from the ends, along x"),
    Param("nominal_spacing", "30", "the longest pitch along a row"),
    Param("min_spacing", "7", "under this between the end holes, a single middle hole"),
    Param("screw_r", "1.4", "screw hole radius"),
    Param("head_r", "2.75", "countersink radius at the tip face"),
    Param("head_h", "2.7", "countersink depth, up from the tip face"),
)
SCREW_CHECKS = (
    ("screw_y - head_r - groove_width / 2", "the screw heads break into the groove (screw_y)"),
    ("tip_hw - t_tip - screw_y - head_r", "the screw heads break out of the tip face (screw_y)"),
    ("root_hw - screw_y - screw_r", "the screw holes break out of the tongue's flanks (screw_y)"),
    ("head_r - screw_r", "head_r must be more than screw_r"),
    ("depth - head_h", "the countersink is deeper than the tongue"),
    ("span", "length is too short for drill_inset"),
)
GROOVE_CHECK = (("tip_hw - t_tip - groove_width / 2 - end_taper",
                 "the groove and the tip radii leave no tip face between them"),)


def groove_points(g):
    """The groove's four corners, in (y, z) from the left, with its faces
    moved `g` normal to themselves towards the centre: `g` = -e opens the
    rail's groove for a lead-in; `g` = clearance gives the housing's guide."""
    foot_y = f"groove_width / 2 + ({g}) / tan(groove_angle) - ({g}) / sin(groove_angle)"
    top_y = (f"groove_width / 2 - (groove_depth - ({g})) / tan(groove_angle) "
             f"- ({g}) / sin(groove_angle)")
    foot_z, top_z = f"-depth - ({g})", f"-depth + groove_depth - ({g})"
    return [(f"-({foot_y})", foot_z), (f"-({top_y})", top_z), (top_y, top_z), (foot_y, foot_z)]


def rail_points(base_hw, e="0"):
    """The rail in (y, z) as modelled, from the tip's left corner
    anticlockwise, the root at z = 0, the support `base_hw` to each side.
    `e` shrinks the tongue, normal to its faces; the support stays."""
    tip_y, root_y = f"tip_hw - ({e}) / tan(angle / 2)", f"root_hw - ({e}) / sin(angle)"
    tip_z, tip_r = f"-depth + ({e})", f"tip_radius - ({e})"
    return [(left(tip_y), tip_z, tip_r)] + groove_points(f"-({e})") + [
        (right(tip_y), tip_z, tip_r),
        (right(root_y), "0", "root_radius"), (right(base_hw), "0"),
        (right(base_hw), "base_depth"), (left(base_hw), "base_depth"), (left(base_hw), "0"),
        (left(root_y), "0", "root_radius")]


class TopeakRail(Primitive):
    """The tongue that slides in a Topeak rack. Eight fixed parameters define its shape,
    and aren't for changing. Its variable parameters are `length`,
    `base_depth`, `base_width`, `end_taper` and `printer_width_offset`. The
    rail has no tolerance. The full dimensioned specification, with the
    working, is `topeak_rail_spec.html`.

    **The width is 61.40, what the print should measure.** A PETG piece modelled
    at 61.6 printed at 61.4 and fits a real rack, a whisker tight. So the default
    `printer_width_offset` is 0.2, and the default model is 61.6.

    The width is measured where calipers measure it, between vertical
    tangents to the tip radii, and everything else is worked from it.

    The rail runs along x from 0 to `length`, centred on y = 0, its root at
    z = 0, its tip at z = -`depth`, and its support above the root. A
    `topeak_rail_housing` built at the same origin sits around it, mated.

    The root radius always runs its full turn, into the support's underside,
    so the support can't be left out: `base_depth` must be more than 0. With
    `base_width` -1 the support is as wide as the root including its radius,
    so the radius ends exactly at the support's edge. Otherwise `base_width`
    must be wider than that. Whether `base_width` is negative is fixed when
    the part is built: rebuild after changing its sign.

    `end_taper` is an option, 0 (off) by default: lead-ins at both ends. Over
    the last `end_taper` of its length the tongue shrinks by `end_taper`,
    normal to its faces, so at 45 degrees along x, the groove opening with it
    and the tip radius going down to match. The support doesn't change. The
    choice of on or off is fixed when the part is built: rebuild after
    changing it.

    `printer_width_offset` is added to the width in the model, half to each
    side, across y only, so the depth, angle and radii stay exact. The groove
    doesn't move. For another printer or filament, print at 0, measure the
    width, and use `width` - measured.
    """

    title = "Topeak rail"
    params, groups = grouped(("Variable", RAIL), ("Screws", SCREWS))
    fixed = FIXED
    derived = SHAPE + (
        ("base_hw", "base_width < base_width * 0 ? root_hw + t_root : base_width / 2",
         "the support's half-width"),
        ("span", "length - 2 * drill_inset", "between the end holes"),
        ("holes", "span < min_spacing ? 1 : ceil(span / nominal_spacing) + 1", "holes per row"),
    )
    derived_on_page = False
    checks = SHAPE_CHECKS + TAPER_CHECKS + GROOVE_CHECK + (
        ("base_depth", "base_depth must be more than 0: the root radius needs the support"),
        ("base_width < base_width * 0 ? 1 : base_width / 2 - root_hw - t_root",
         "base_width is narrower than the root and its radius"),
    ) + SCREW_CHECKS
    fits = (("topeak_rail_housing", "the rail slid into a housing built at the same origin"),)
    views = (
        ("front", "u", ("0", "-width / 2", "tip_radius - depth"),
         ("0", "width / 2", "tip_radius - depth"), 1, "width"),
        ("front", "v", ("0", "-root_hw", "-depth"), ("0", "-root_hw", "0"), 1, "depth"),
        ("front", "v", ("0", "base_hw", "0"), ("0", "base_hw", "base_depth"), -1, "base_depth"),
        ("front", "angle", ("0", "tip_hw", "-depth"),
         (("0", "tip_hw - 3", "-depth"), ("0", "root_hw", "0")), 2.5, "angle"),
        ("side", "u", ("0", "0", "-depth"), ("length", "0", "-depth"), 1, "length"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        body = b.choose("base_width >= 0", lambda: rail_body(b, rail_points, "base_hw", "rail"),
                        lambda: trimmed(b, rail_body(b, rail_points, "base_hw + 1", "rail"), "trimmed"))
        if body is None:
            return None
        return b.finish(b.cut(None, body, [screw_rows(b)]))


def screw_rows(b, length="length", inset="drill_inset", holes="holes", span="span"):
    """The two rows of countersunk holes, up from the tip face through the tongue
    and support, as one tool. With `screws` 0 they sit far off and cut nothing,
    so the rows turn on and off live. The names of the rail's length, the
    rows' inset, holes per row and span may be given (`rail_end` cuts its
    tongue's rows again under names of its own)."""
    y = f"screw_y + {away('screws')}"
    tip, top = "-depth", "base_depth + 1"
    hole = b.fuse("hole", [
        part for k, c in (("lo", (f"-({y})")), ("hi", y)) for part in (
            b.cylinder(f"hole_{k}_shank", "z", ("0", c), "screw_r", (f"{tip} - 1", top)),
            b.cylinder(f"hole_{k}_bore", "z", ("0", c), "head_r", (f"{tip} - 1", tip)),
            b.cone(f"hole_{k}_head", "z", ("0", c), "head_r", "screw_r", (tip, f"{tip} + head_h")))])
    step = f"{holes} > 1 ? {span} / ({holes} - 1) : 0"
    first = f"{holes} > 1 ? {inset} : {length} / 2"
    return b.array("holes", hole, "x", holes, first, step)
