"""BOX EDGE -- a length of the printed edge that holds two panels of a box."""

import math

from primlib.core import Machined, Param, grouped

SECTION = (
    Param("panel_t", "6.5", "the panels' thickness"),
    Param("skin", "5", "the wall over the panels' outsides"),
    Param("panel_gap", "3", "the web's width: how far the panels stop short of the inside corner"),
    Param("size", "27", "across the section, each way, from the outside face"),
    Param("bevel", "15", "the width of the big 45 degree bevel across the outside corner"),
    Param("chamfer", "0.5", "the small 45 degree chamfer on the outward square edges"),
    Param("glue", "0", "the glue line's thickness: how deep the pockets are behind the ridges; 0 for none"),
    Param("glue_ridge", "0.6", "the width of the ridges that hold a panel off the pockets' floor"),
    Param("relief", "0", "the -x wall's outside face cut back by this, across the whole section, "
                         "its small chamfers carried round; 0 for none"),
)
SCREWS = (
    Param("drill_inset", "6", "the screw rows' first and last holes from the ends, and "
                              "the rows' line from the panel's edge"),
    Param("nominal_spacing", "30", "the longest pitch along a row"),
    Param("min_spacing", "7", "under this between the end holes, a single middle hole"),
    Param("screw_r", "1.4", "screw hole radius"),
    Param("head_r", "2.75", "countersink radius at the outside face"),
    Param("head_h", "2.7", "countersink depth"),
    Param("screw_len", "20", "the hole tool's length from the outside face"),
    Param("holes_x", "1", "1 for the row through the -x wall, 0 for none"),
    Param("holes_y", "1", "1 for the row through the -y wall, 0 for none"),
)
OUT = "(panel_t + skin)"
ROOT2 = math.sqrt(2)


def section_lines(size):
    """The section as lines, in order round the outline: each ((nx, ny), d) with
    points inside where nx * x + ny * y < d (expressions). `size` is the outside
    width. The inside corner is at the origin, the walls towards -x and -y."""
    reach, c = f"(({size}) - {OUT})", "chamfer"
    b = f"(bevel / {ROOT2:.10f})"
    s = 1 / ROOT2
    return (
        ((0, 1), "0"),
        ((s, s), f"((panel_gap - {c}) * {s:.10f})"),
        ((1, 0), "panel_gap"),
        ((0, 1), "(-panel_t)"),
        ((s, s), f"(({reach} - panel_t - {c}) * {s:.10f})"),
        ((1, 0), reach),
        ((s, -s), f"(({reach} + {OUT} - {c}) * {s:.10f})"),
        ((0, -1), OUT),
        ((-s, -s), f"((2 * {OUT} - {b}) * {s:.10f})"),
        ((-1, 0), OUT),
        ((-s, s), f"(({reach} + {OUT} - {c}) * {s:.10f})"),
        ((0, 1), reach),
        ((s, s), f"(({reach} - panel_t - {c}) * {s:.10f})"),
        ((1, 0), "(-panel_t)"),
        ((0, 1), "panel_gap"),
        ((s, s), f"((panel_gap - {c}) * {s:.10f})"),
        ((1, 0), "0"),
    )


def section_points(size, inset="0"):
    """The section's corners, every face moved `inset` inwards, as (a, b)
    expressions: each corner is where two neighbouring lines meet."""
    lines = section_lines(size)
    pts = []
    for ((a1, b1), d1), ((a2, b2), d2) in zip(lines, lines[1:] + lines[:1]):
        det = a1 * b2 - a2 * b1
        e1, e2 = f"({d1} - ({inset}))", f"({d2} - ({inset}))"
        pts.append((f"({e1} * ({b2:.10f}) - {e2} * ({b1:.10f})) / ({det:.10f})",
                    f"({e2} * ({a1:.10f}) - {e1} * ({a2:.10f})) / ({det:.10f})"))
    return pts


def swept(b, suffix, size, plane, start, end, near_chamfer):
    """The section along the normal of `plane` ("xy" along z, its walls towards
    -x and -y; "yz" along x; "zx" along y), from `start` to `end`, the far end
    chamfered all round, and the near end too if `near_chamfer`."""
    full, shrunk = section_points(size), section_points(size, "chamfer")
    near = [(shrunk, start), (full, f"({start}) + chamfer")] if near_chamfer else [(full, start)]
    return b.loft(suffix, near + [(full, f"({end}) - chamfer"), (shrunk, end)], plane)


def glue_pocket(b, suffix, plane, lo, hi, face, along, flip=False, glue="glue"):
    """A cut tool for a glue pocket in a face that holds a panel. Its section, in
    `plane`, runs from `lo` to `hi` across the face, on the face's plane `face`,
    going `glue` towards -`face`'s axis. The sides are at 45 degrees, so it prints
    in any direction. `flip` swaps the section's two coordinates. With no glue the
    tool sits far away, cutting nothing, so glue can be turned on and off live."""
    at = f"(({face}) + ({glue} > 0 ? 0 : 1000))"
    deep = f"({glue} > 0 ? {glue} : 0.01)"
    corners = [(f"({lo})", at), (f"({hi})", at),
               (f"({hi}) - {deep}", f"{at} - {deep}"), (f"({lo}) + {deep}", f"{at} - {deep}")]
    return b.prism(suffix, [(v, u) for u, v in corners] if flip else corners, plane, along)


def screw(b, suffix, axis, centre):
    """A countersunk hole tool along +`axis`, its head at the outside face."""
    return b.fuse(suffix, [
        b.cylinder(f"{suffix}_shank", axis, centre, "screw_r", (f"-{OUT}", f"-{OUT} + screw_len")),
        b.cone(f"{suffix}_head", axis, centre, "head_r", "screw_r", (f"-{OUT}", f"-{OUT} + head_h"))])


def relief_cuts(b):
    """The relief as flat cuts: the -x wall's face, and 45 degree chamfers where it
    meets the two ends and the wall's own end. A section shrunk for the end
    chamfers would cross itself on a wall under about 2.8 chamfers thick; these
    don't. With `relief` 0 they sit far off and cut nothing."""
    s = 1 / ROOT2
    face = f"({OUT} - relief + (relief > 0 ? 0 : 1000))"
    size = f"(2 * length + 2 * size + 100)"
    cut = lambda suffix, normal, d: b.beyond(f"relief_{suffix}", normal, d, size)  # noqa: E731
    return [cut("face", (-1, 0, 0), face),
            cut("start", (-s, 0, -s), f"(({face}) - chamfer) * {s:.10f}"),
            cut("end", (-s, 0, s), f"(({face}) - chamfer + length) * {s:.10f}"),
            cut("wall_end", (-s, s, 0), f"(({face}) - chamfer + reach) * {s:.10f}")]


def away(flag):
    """0, or far enough to cut nothing when `flag` is 0, so a row turns off live."""
    return f"({flag} > 0 ? 0 : 1000)"


class BoxEdge(Machined):
    """One length of the edge along which two panels of a box meet. The section
    is an L: a `skin` over each panel's outside, a web `panel_gap` wide between
    the panels' edges, and a `bevel` across the outside corner. The panels drop
    into the two rebates and are screwed through the skin.

    **Glue line:** with `glue` above 0, the faces that hold the panels are cut back
    by `glue`, leaving two ridges `glue_ridge` wide on each face, along the edge. The
    panels sit on the ridges, exactly where they sit with no glue, so no other size
    changes, and the pockets between them are the glue line. They're open at both
    ends, so glue and air can get out. Their sides are at 45 degrees.

    **Relief:** with `relief` above 0, the -x wall's outside face is cut back by
    `relief` over the whole section and length, for something to pass beneath
    it, with the small chamfers carried round the new face. `holes_x` and
    `holes_y` turn either screw row off (0), for a wall left too thin for the
    countersinks, say.

    **Frame:** the inside corner at the origin, the walls towards -x and -y, the
    edge along +z from 0 to `length`. Each panel's inner face is on x = 0 or y = 0.

    The small `chamfer` is part of the shape, not a feature picked from its edges,
    so nothing can lose it when a size changes. Its faces are on every outward
    square edge along the section and all round both ends.

    Two rows of countersunk holes go through the skins, one per panel, on the line
    `panel_gap` + `drill_inset` from the inside corner, from `drill_inset` from
    one end to `drill_inset` from the other, at no more than `nominal_spacing`.
    """

    title = "Box edge"
    params, groups = grouped(("Length", (Param("length", "100", "along the edge"),)),
                             ("Section", SECTION), ("Screws", SCREWS))
    derived = (
        ("reach", f"size - {OUT}", "the walls' length from the inside corner"),
        ("inset", "panel_gap + drill_inset", "the screw rows' line from the inside corner"),
        ("span", "length - 2 * drill_inset", "between the end holes"),
        ("holes", "span < min_spacing ? 1 : ceil(span / nominal_spacing) + 1", "holes per row"),
    )
    checks = (
        ("length - 2 * chamfer", "length is too short for its chamfers"),
        ("chamfer", "chamfer must be positive"),
        ("skin - 2 * chamfer", "skin is too thin for its chamfers"),
        ("panel_gap - 2 * chamfer", "panel_gap is too small for its chamfers"),
        ("reach - panel_gap - 2 * chamfer", "size is too small to leave a rebate"),
        ("reach - inset - head_r", "the screw heads break out of the skin's edge"),
        (f"2 * {OUT} - bevel / {ROOT2:.10f} - 2 * chamfer", "bevel is too wide"),
        ("glue >= 0 ? 1 : 0", "glue must not be negative"),
        ("glue_ridge", "glue_ridge must be positive"),
        ("skin - glue - 2 * chamfer", "glue leaves the skin too thin"),
        ("panel_gap - glue - 2 * chamfer", "glue leaves the web too thin"),
        ("panel_t - chamfer - 2 * glue_ridge - 2 * glue", "the panel's edge is too thin for its ridges"),
        ("relief >= 0 ? 1 : 0", "relief must not be negative"),
        ("skin - relief - 2 * chamfer", "relief leaves the -x wall too thin"),
        (f"bevel / {ROOT2:.10f} - relief - chamfer", "relief reaches past the bevel"),
        ("reach - chamfer - panel_gap - 2 * glue_ridge - 2 * glue", "the rebate is too narrow for its ridges"),
    )

    @classmethod
    def body(cls, b):
        body = swept(b, "body", "size", "xy", "0", "length", True)
        run = ("-1", "length + 1")
        skin = ("panel_gap + glue_ridge", "reach - chamfer - glue_ridge", "-panel_t")
        web = ("-panel_t + glue_ridge", "-chamfer - glue_ridge", "panel_gap")
        pockets = [glue_pocket(b, "glue_skin_a", "xy", *skin, run),
                   glue_pocket(b, "glue_skin_b", "xy", *skin, run, flip=True),
                   glue_pocket(b, "glue_web_a", "xy", *web, run, flip=True),
                   glue_pocket(b, "glue_web_b", "xy", *web, run)]
        head = b.fuse("hole", [screw(b, "hole_y", "y", (f"inset + {away('holes_y')}", "0")),
                               screw(b, "hole_x", "x", (f"inset + {away('holes_x')}", "0"))])
        step = "holes > 1 ? span / (holes - 1) : 0"
        first = "holes > 1 ? drill_inset : length / 2"
        return body, [b.array("holes", head, "z", "holes", first, step)] + pockets + relief_cuts(b)
