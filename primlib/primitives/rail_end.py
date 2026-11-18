"""RAIL END -- the hybrid case's rail end piece: a notched box edge over the
rail's width, fused to a topeak_rail tongue out to the outside face, with a
drop-on entry into the rack."""

from primlib.core import Builder, Param, Primitive, grouped
from primlib.primitives.box_edge import BoxEdge
from primlib.primitives.rail15 import SHAPE
from primlib.primitives.topeak_rail import FIXED, TopeakRail, screw_rows

EDGE = (
    Param("size", "27", "the edge's section, each way, from the outside face"),
    Param("panel_t", "6.5", "the panels' thickness"),
    Param("skin", "5", "the wall over the panels' outsides"),
    Param("panel_gap", "3", "the web's width"),
    Param("bevel", "15", "the 45 degree bevel across each outside edge"),
    Param("chamfer", "0.5", "on the outward square edges"),
    Param("glue", "0", "the glue line's pockets behind the ridges; 0 for none"),
    Param("glue_ridge", "0.6", "the ridges the panels sit on"),
    Param("notch", "3.85", "the edge's underside cut back by this over the rail's width, to clear the rack "
                           "(box_edge's relief)"),
    Param("corner_size", "40", "the case's corner across each wall: the end piece is at least this long"),
)
SCREWS = (
    Param("drill_inset", "6", "the edge's screw row from the inside corner, past the web"),
    Param("nominal_spacing", "30", "the longest pitch along a row"),
    Param("min_spacing", "7", "under this between the end holes, a single middle hole"),
    Param("screw_r", "1.4", "the screw hole"),
    Param("head_r", "2.75", "the countersink at the outside face"),
    Param("head_h", "2.7", "the countersink's depth"),
    Param("screw_len", "20", "the edge's holes' length from the outside face"),
    Param("screws", "1", "1 for the tongue's two rows of screws up into the bottom panel; 0 none"),
)
RAIL = (
    Param("base_depth", "2", "the rail's support, against the bottom panel"),
    Param("printer_width_offset", "0.2", "topeak_rail's: added to its width in the model"),
    Param("drop_on", "15", "after the bevel: the tongue cut back to a straight key that drops into the rack"),
    Param("taper", "10", "after the drop-on: the tongue widens back to full size"),
    Param("drop_clear", "0.5", "the key inside the tongue's neck, each side"),
    Param("drop_chamfer", "1", "45 degrees on the key's tip edges"),
)


class RailEnd(Primitive):
    """The end of the hybrid case's Topeak rail: the bottom Y edge over the
    rail's width (a box_edge, notched by `notch` underneath to clear the
    rack, no screws through its lower wall) fused to a topeak_rail tongue
    that runs from the case's outside face in under the bottom panel, so
    the rail's end is one piece with the edge above it.

    **The drop-on entry:** the edges' 45 degree bevel is carried down
    through the support and tongue; from its foot on the tip, over
    `drop_on`, the tongue's flanks are cut back to a straight key (its tip
    edges chamfered by `drop_chamfer`, `drop_clear` inside the neck each
    side) that drops into the rack; over `taper` the cut narrows to
    nothing.

    The tongue is `end_length` long: the corner's size, or what the entry
    needs if longer. Its two screw rows run up into the bottom panel, the
    first and last holes `end_inset` from its ends, past the bevel's foot
    by a head and 1 mm; they are cut again after the fuse, as the edge's
    wall lies over them.

    **Frame:** x from the left panel's inside face (the outside face at
    -(panel_t + skin)), y = 0 on the rail's centre line, z = 0 the inside
    floor: the case's left end. The right end is the same turned half
    round about z. As the original hybrid case model builds it."""

    title = "Rail end"
    params, groups = grouped(("Edge", EDGE), ("Screws", SCREWS), ("Rail", RAIL))
    fixed = FIXED
    derived = SHAPE + (
        ("key_hw", "root_hw + t_root - root_radius", "the drop-on key's half-width, at the neck"),
        ("widest", "tip_hw + printer_width_offset / 2", "the tongue's sharp corner, as modelled"),
        ("rail_w", "width + printer_width_offset", "the rail's modelled width: the edge piece's length"),
        ("screw_y", "(groove_width / 2 + key_hw - drop_clear - drop_chamfer) / 2",
         "each screw row off the centre line: midway between the groove and the key's side"),
        ("end_length", "max(corner_size; bevel * cos(45) + base_depth + depth - skin + drop_on + taper + 1)",
         "the tongue, from the outside face"),
        ("end_inset", "bevel * cos(45) - skin + base_depth + depth + head_r + 1",
         "the screw rows' end holes from the tongue's ends"),
        ("end_span", "end_length - 2 * end_inset", "between the end holes"),
        ("end_holes", "end_span < min_spacing ? 1 : ceil(end_span / nominal_spacing) + 1", "holes per row"),
        ("x0", "-(panel_t + skin)", "the outside face"),
        ("face", "-panel_t - base_depth", "the tongue's root"),
        ("tip", "face - depth", "the tongue's tip"),
        ("z0", "x0 + bevel * cos(45)", "the bevel at the outside face"),
        ("foot", "x0 + z0 - tip", "the bevel's foot on the tip"),
        ("x1", "foot + drop_on", "the drop-on's end"),
        ("x2", "x1 + taper", "the taper's end"),
        ("key", "key_hw - drop_clear", "the key's half-width"),
        ("out", "widest + 1", "past the tongue's side"),
    )
    derived_on_page = False
    checks = (
        ("notch >= 0 ? 1 : 0", "notch must not be negative"),
        ("end_span", "the tongue is too short for its screw rows"),
        ("drop_on", "drop_on must be positive"),
        ("taper", "taper must be positive"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        same = lambda c, **over: dict({p.name: p.name for p in c.params}, **over)  # noqa: E731
        edge = b.part(BoxEdge, "edge", same(BoxEdge, length="rail_w", relief="notch", holes_x="0", holes_y="1"))
        tongue = b.part(TopeakRail, "tongue", same(TopeakRail, length="end_length", base_width="-1",
                                                   end_taper="0", drill_inset="end_inset"))
        if edge is None or tongue is None:
            return None
        # box_edge runs along its z, walls to -x and -y: here along +y, its -x wall down,
        # its -y wall out to -x; across the rail's width, centred.
        edge = b.move(b.turn(b.turn(edge, "x", "-90"), "y", "-90"), (None, "-rail_w / 2", None))
        tongue = b.move(tongue, ("x0", None, "face"))
        body = b.fuse("body", [edge, tongue])
        holes = b.move(screw_rows(b, "end_length", "end_inset", "end_holes", "end_span"), ("x0", None, "face"))
        tools = []
        for k, sign in (("lo", "-"), ("hi", "")):
            y = lambda e: f"{sign}({e})"  # noqa: E731
            tools.append(b.prism(f"{k}_key", [(y("key"), "face"), (y("out"), "face"), (y("out"), "tip - 1"),
                                              (y("key - drop_chamfer - 1"), "tip - 1"),
                                              (y("key"), "tip + drop_chamfer")],
                                 "yz", ("x0 - 1", "x1")))
            tools.append(b.prism(f"{k}_taper", [("x1", y("key")), ("x2", y("widest")), ("x2", y("out")),
                                                ("x1", y("out"))], "xy", ("tip - 1", "face")))
        # The bevel: everything outside the plane through (x0, z0) at 45 degrees.
        tools.append(b.prism("bevel", [("tip - 1", "x0 - 1"), ("tip - 1", "foot + 1"), ("z0 + 1", "x0 - 1")],
                             "zx", ("-out", "out")))
        if None in tools:
            return None
        return b.finish(b.cut(None, body, tools + [holes]))
