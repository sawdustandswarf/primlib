"""BOX CORNER -- the printed corner where three panels of a box meet."""

from primlib.core import Machined, Param, grouped
from primlib.primitives.box_edge import OUT, ROOT2, SCREWS, SECTION, glue_pocket, screw, swept

EDGE_ONLY = {"relief", "holes_x", "holes_y"}     # box_edge options a corner doesn't have
CORNER_SECTION = tuple(Param("size", "40", p.note) if p.name == "size" else p
                       for p in SECTION if p.name not in EDGE_ONLY)

CORNER_SCREWS = (
    Param("drill_spacing", "12", "between the holes, each way"),
    Param("drill_rows", "2", "rows of holes each way, on each of the three faces"),
)


class BoxCorner(Machined):
    """Three walls meeting at a corner, each the `box_edge` section carried on: a
    `skin` over each of the three panels, a web `panel_gap` wide where two panels'
    edges meet, and a `bevel` across each of the three outside edges. `size` here
    is the corner's own outside width, usually more than the edges'. Each panel
    has `drill_rows` by `drill_rows` countersunk holes.

    **Frame:** the inside corner at the origin, the walls towards -x, -y and -z,
    each panel's inner face on x = 0, y = 0 or z = 0. The eight corners of a box
    are this part, mirrored.

    It's built as three edge sections swept along x, y and z, so the small
    `chamfer` is part of the shape at every size: no feature picked from its edges
    can lose it. Their far ends are chamfered all round, then the three bevels are
    cut across the whole, with a flat triangular facet where they meet.

    **Glue line:** with `glue` above 0, each panel's three faces here are cut back
    by `glue`, leaving ridges `glue_ridge` wide, as on `box_edge`. The panels sit on
    the ridges, exactly where they sit with no glue. Each pocket is open at the
    corner's far end, so glue and air can get out. Its sides are at 45 degrees.
    """

    title = "Box corner"
    params, groups = grouped(("Section", CORNER_SECTION),
                             ("Screws", SCREWS[:1] + CORNER_SCREWS + tuple(p for p in SCREWS[3:] if p.name not in EDGE_ONLY)))
    derived = (
        ("reach", f"size - {OUT}", "the walls' length from the inside corner"),
        ("inset", "panel_gap + drill_inset", "the first hole from the inside corner"),
        ("leg", f"bevel / {ROOT2:.10f}", "the bevel's width along each face"),
        ("facet", f"-3 * {OUT} + 2 * leg", "the facet's plane, x + y + z, where the bevels meet"),
    )
    checks = (
        ("chamfer", "chamfer must be positive"),
        ("skin - 2 * chamfer", "skin is too thin for its chamfers"),
        ("panel_gap - 2 * chamfer", "panel_gap is too small for its chamfers"),
        ("reach - inset - (drill_rows - 1) * drill_spacing - head_r",
         "the screw heads break out of the corner's edge"),
        ("drill_spacing - 2 * head_r", "the screw heads run into each other"),
        (f"2 * {OUT} - leg - 2 * chamfer", "bevel is too wide"),
        ("glue >= 0 ? 1 : 0", "glue must not be negative"),
        ("glue_ridge", "glue_ridge must be positive"),
        ("skin - glue - 2 * chamfer", "glue leaves the skin too thin"),
        ("panel_gap - glue - 2 * chamfer", "glue leaves the web too thin"),
        ("panel_t - chamfer - 2 * glue_ridge - 2 * glue", "the panel's edge is too thin for its ridges"),
        ("reach - chamfer - panel_gap - 2 * glue_ridge - 2 * glue", "the rebate is too narrow for its ridges"),
    )

    @classmethod
    def body(cls, b):
        walls = b.fuse("walls", [swept(b, f"along_{axis}", "size", plane, f"-{OUT}", "reach", False)
                                 for axis, plane in (("z", "xy"), ("x", "yz"), ("y", "zx"))])
        outside, far = f"(-{OUT} - 1)", f"(-{OUT} + leg + 1)"
        bevels = [b.prism(f"bevel_{axis}", [(outside, outside), (far, outside), (outside, far)], plane,
                          (outside, "reach + 1"))
                  for axis, plane in (("z", "xy"), ("x", "yz"), ("y", "zx"))]
        # The flat facet where the three bevels meet, and the small chamfer on each
        # bevel's far end, which the walls' own ends don't reach.
        s, r3 = 1 / ROOT2, 1 / 3 ** 0.5
        facet = [b.beyond("facet_cut", (-r3, -r3, -r3), f"(-(facet)) * {r3:.10f}")]
        ends = [b.beyond(f"bevel_end_{axis}", normal, f"({OUT} - leg / 2) + "
                                                      f"(reach - chamfer) * {s:.10f}")
                for axis, normal in (("z", (-0.5, -0.5, s)), ("x", (s, -0.5, -0.5)), ("y", (-0.5, s, -0.5)))]
        holes = []
        for axis, (u, v) in (("z", "xy"), ("y", "xz"), ("x", "yz")):
            rows = ("drill_rows", "inset", "drill_spacing")
            holes.append(b.grid(f"holes_{axis}", screw(b, f"hole_{axis}", axis, ("0", "0")),
                                {u: rows, v: rows}))
        # Each panel: its skin, then its edge against each of the other two panels' webs.
        # They run so that upright pockets stay upright when it prints standing on z.
        skin = ("panel_gap + glue_ridge", "reach - chamfer - glue_ridge", "-panel_t")
        web = ("-panel_t + glue_ridge", "-chamfer - glue_ridge", "panel_gap")
        run = ("panel_gap", "reach + 1")
        pockets = [
            glue_pocket(b, "glue_z_skin", "zx", *skin, run, flip=True),
            glue_pocket(b, "glue_z_web_x", "zx", *web, run),
            glue_pocket(b, "glue_z_web_y", "yz", *web, run, flip=True),
            glue_pocket(b, "glue_x_skin", "xy", *skin, run, flip=True),
            glue_pocket(b, "glue_x_web_y", "xy", *web, run),
            glue_pocket(b, "glue_x_web_z", "zx", *web, run, flip=True),
            glue_pocket(b, "glue_y_skin", "xy", *skin, run),
            glue_pocket(b, "glue_y_web_x", "xy", *web, run, flip=True),
            glue_pocket(b, "glue_y_web_z", "yz", *web, run),
        ]
        return walls, bevels + facet + ends + holes + pockets
