"""ROTARY LATCH -- a hex knob on the body turning over an arc of 15 mm rail on the lid."""

from primlib.core import Builder, Param, Primitive, grouped
from primlib.primitives.rail15 import FIXED as RAIL15_FIXED
from primlib.primitives.rail15 import SHAPE as RAIL15_SHAPE
from primlib.primitives.rail15 import left, rail_points, right

LATCH = (
    Param("knob_af", "56", "knob, a hexagon: across the flats (a flat at 12 o'clock, open)"),
    Param("knob_len", "11", "knob length, rib tips to front face, z"),
    Param("rail_r", "15", "the rail's centre line, radius about the pin"),
    Param("rail_span", "60", "the rail's arc, centred at 12 o'clock, deg"),
    Param("turn", "90", "knob turn from open to locked, either way, deg"),
    Param("pull_down", "1", "how far a ramp draws the rail (and lid) down"),
    Param("preload", "0.5", "mounted, the lid plate sits this far above locked: locking pulls it in; "
                            "pull_down - preload is left for tolerance"),
    Param("joint_y", "7.6", "axis to the lid joint: the middle of the gap between the plates, mounted"),
    Param("clearance", "0.2", "every gap between parts, normal to the faces"),
)
BASE = (
    Param("plate_t", "3", "base plate thickness, z"),
    Param("plate_w", "80", "both plates' width, x"),
    Param("plate_bot", "-27", "base plate's lower edge, y"),
    Param("screw_x", "36", "axis to every screw, x (both plates: the screws line up)"),
    Param("screw_y1", "0", "base plate's upper screws, y"),
    Param("screw_y2", "-20", "base plate's lower screws, y"),
    Param("screw_d", "3.4", "M3 clearance hole"),
    Param("head_d", "6", "M3 countersink diameter at the face"),
    Param("root_r", "1", "pin root, 45 deg"),
    Param("wall_in", "1.5", "knob wall between bore and groove: sets the pin, as big as fits"),
    Param("pilot_d", "2.5", "pilot hole in the pin for the M3 cap screw"),
    Param("pilot_l", "6", "pilot hole depth"),
    Param("ring_r1", "7", "inner V rib's tip radius"),
    Param("ring_r2", "23.5", "outer V rib's tip radius (outside the groove)"),
    Param("ring_h", "1", "V rib height (45 deg flanks)"),
    Param("tip_w", "0.2", "V rib tip's flat"),
    Param("cap_d", "15", "cap diameter"),
    Param("cap_t", "2", "cap thickness"),
)
RAIL = (
    Param("depth", "4", "rail15 depth, root to tip"),
    Param("base_depth", "1", "rail15 support under the root, into the lid plate"),
    Param("ramp_a", "20", "each lead-in ramp's length from the notch's edge, deg"),
)
LID = (
    Param("lid_h", "24", "lid plate height, y, up from its lower edge"),
    Param("lid_screw_in", "5", "lid plate's screws, in from its lower and upper edges, y"),
)
PRINT = (
    Param("bridge_t", "0.2", "alignment bridge: one layer"),
    Param("bridge_lap", "1", "alignment bridge: how far it runs under each plate"),
)


class RotaryLatch(Primitive):
    """A rotary latch for a box lid: a hex knob on the
    body reaches over the lid joint and turns over an arc of 15 mm rail on
    the lid. Five parts, each its own object in the result compound
    (`{name}_base`, `_knob`, `_cap`, `_lid`, `_bridge`).

    **Frame:** the case surface is z = 0, the knob's axis is z (out of the
    case), y is up towards the lid and x across; the pin's axis is the
    origin.

    **Base** (on the body): a plate `plate_w` wide from `plate_bot` up to
    the gap at the joint, four countersunk M3 at x = ±`screw_x`, the pin
    (as big as fits: `wall_in` of knob between its bore and the groove,
    with a 45 deg root and a pilot hole for the cap screw) and two V ribs
    the knob's flat back runs on, cut off at the plate's edge.

    **Knob:** one piece, a hexagon `knob_af` across the flats. Its back
    carries the `rail15_housing` slot at `clearance`, revolved all round
    about the pin at radius `rail_r`, with one notch through the slot's
    outer wall at 12 o'clock, `notch_x` either side, where the rail drops
    in. Each side of the notch is a lead-in ramp: over `ramp_a` the slot's
    outer lip comes in from `pull_down` further out to true (an eccentric
    copy of the slot, `ecc` off the axis, kept to the ramp's sector and
    outside `rail_r`). The ramps mirror, so the knob locks turned `turn`
    either way, and a lid sitting up to `pull_down` high is drawn down.
    Printed front face down: the slot's flanks lean 30 deg. Held on the
    pin by the **cap** and an M3 into the pilot.

    **Lid** (on the box lid): a plate `plate_w` wide and `lid_h` high with
    four countersunk M3 lined up with the base's, carrying the `rail15`
    profile revolved over `rail_span` at radius `rail_r`, its support cut
    off at the plate's lower edge. It is built where it is mounted:
    `preload` above the locked position, so turning the knob pulls it in
    by that much (`preload` - `clearance` of it against the parts, which
    must flex) and `pull_down` - `preload` of the ramps is left for
    tolerance.

    **Bridge:** a print aid, one layer (`bridge_t`) across the gap between
    the plates and `bridge_lap` under each, so the two plates print as one
    piece in their mounted places. Screw both on, then cut it along the
    joint.

    The fixed parameters are the rail's (`rail15`).
    """

    title = "Rotary latch"
    params, groups = grouped(("Latch", LATCH), ("Base and knob", BASE), ("Rail", RAIL),
                             ("Lid plate", LID), ("Print", PRINT))
    fixed = RAIL15_FIXED
    derived = (("printer_width_offset", "0", "rail15: no offset (its print measured 14.95)"),) + RAIL15_SHAPE + (
        ("base_hw", "root_hw + t_root", "rail15: support half-width"),
        ("pin_d", "2 * (rail_r - width / 2 - clearance - wall_in - clearance)",
         "pin diameter: the largest leaving wall_in between bore and slot"),
        ("knob_rc", "knob_af / 2 / cos(30)", "knob's corners, radius (its sweep)"),
        ("gap_r", "clearance * sqrt(2)", "radial gap that is clearance normal to a 45 deg face"),
        ("z_body", "plate_t + ring_h", "the knob's back face"),
        ("z_front", "plate_t + knob_len", "the knob's front face"),
        ("z_pin_top", "z_front - cap_t", "the pin's end"),
        ("z_shoulder", "z_pin_top - clearance * (sqrt(2) - 1)", "counterbore floor at its wall"),
        ("bore_r", "pin_d / 2 + clearance", "knob bore radius"),
        ("cap_wall", "cap_d / 2 - bore_r", "cap overlap on the counterbore's floor"),
        ("grow", "clearance / tan(angle / 2)", "slot: how far clearance moves the sharp corners"),
        ("floor_hw", "tip_hw + grow", "slot floor half-width, sharp"),
        ("mouth_hw", "root_hw + grow", "slot mouth half-width, sharp"),
        ("root_z", "z_body - clearance", "rail root: the lid plate's face"),
        ("z_floor", "root_z + depth + clearance", "slot floor"),
        ("groove_in", "rail_r - width / 2 - clearance", "slot's inner wall at its widest"),
        ("groove_out", "rail_r + width / 2 + clearance", "slot's outer wall at its widest"),
        ("mouth_in", "rail_r - mouth_hw", "slot mouth, inner edge"),
        ("mouth_out", "rail_r + mouth_hw", "slot mouth, outer edge (the lip)"),
        ("notch_x", "(rail_r + width / 2) * sin(rail_span / 2) + clearance", "notch half-width"),
        ("notch_a", "asin(notch_x / mouth_out) / 1deg", "notch edge's angle from 12 o'clock at the lip"),
        ("ecc", "pull_down / sin(ramp_a)", "ramp circle's offset from the axis"),
        ("ecc_a", "notch_a + ramp_a - 90", "its direction, from 12 o'clock towards the ramp"),
        ("margin", "turn - notch_a - ramp_a - rail_span / 2", "locked: the ramp's end past the rail's end, deg"),
        ("spare", "pull_down - preload", "ramp left for tolerance, mounted"),
        ("base_top", "joint_y - clearance - preload / 2", "base plate's upper edge"),
        ("lid_bot", "joint_y + clearance + preload / 2", "lid plate's lower edge, mounted"),
        ("rail_low", "(rail_r - base_hw) * cos(rail_span / 2) + preload", "the rail root's lowest point, mounted"),
    )
    checks = (
        ("knob_af / 2 - 0.3 - ring_r2 - tip_w / 2", "the outer rib isn't under the knob"),
        ("ring_r2 - tip_w / 2 - mouth_out - 0.3", "the outer rib isn't outside the slot"),
        ("mouth_in - 0.3 - ring_r1 - tip_w / 2", "the inner rib isn't inside the slot"),
        ("ring_r1 - tip_w / 2 - pin_d / 2 - gap_r - 0.5", "the inner rib doesn't clear the bore"),
        ("cap_wall - 1.5 + 0.000001", "the cap overlaps the floor by less than 1.5"),
        ("z_pin_top - plate_t - pilot_l", "the pilot hole reaches the plate"),
        ("wall_in", "wall_in must be positive"),
        ("knob_af / 2 - groove_out - pull_down - 2.5 + 0.000001", "less than 2.5 of wall outside the slot at a ramp"),
        ("z_front - z_floor - 2 + 0.000001", "less than 2 of knob in front of the slot"),
        ("rail_low - lid_bot + 0.000001", "the rail's root reaches below the lid plate"),
        ("base_top - pin_d / 2 - root_r - 0.5 + 0.000001", "the base plate doesn't reach 0.5 past the pin's root"),
        ("margin - 3 + 0.000001", "locked, the rail isn't 3 deg past the ramp"),
        ("screw_x - head_d / 2 - knob_rc", "the screw heads are under the knob's corners"),
        ("-plate_bot - ring_r2 - tip_w / 2 - ring_h - 0.5 + 0.000001", "the base plate doesn't carry the outer rib"),
        ("screw_y2 - head_d / 2 - plate_bot", "the lower base screws are off the plate"),
        ("base_top - screw_y1 - head_d / 2", "the upper base screws are off the plate"),
        ("lid_h - 2 * lid_screw_in - head_d", "the lid plate's screws overlap"),
        ("lid_screw_in - head_d / 2", "the lid plate's screws are off its edge"),
        ("spare", "preload must be less than pull_down"),
        ("preload + 0.000001", "preload can't be negative"),
        ("bridge_t", "bridge_t must be positive"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        parts = [make_base(b), make_knob(b), make_cap(b), make_lid(b), make_bridge(b)]
        if None in parts:
            return None
        return b.finish(b.compound(None, parts))


def countersunk(b, suffix, top, x, y):
    """An M3 clearance hole along z through a part whose face is at `top`,
    countersunk at that face."""
    sink = f"({top}) - (head_d - screw_d) / 2"
    return [b.cylinder(f"{suffix}_shank", "z", (x, y), "screw_d / 2", ("-1", f"({top}) + 1")),
            b.cone(f"{suffix}_sink", "z", (x, y), "screw_d / 2", "head_d / 2 + 1", (sink, f"({top}) + 1"))]


def v_rib(b, suffix, r):
    """A rib of V section, its tip (tip_w flat) at radius `r` on z_body;
    45 deg flanks down into the plate."""
    span = ("plate_t - 0.01", "z_body")
    return b.cut(suffix, b.cone(f"{suffix}_out", "z", ("0", "0"), f"{r} + tip_w / 2 + ring_h + 0.01",
                                f"{r} + tip_w / 2", span),
                 [b.cone(f"{suffix}_in", "z", ("0", "0"), f"{r} - tip_w / 2 - ring_h - 0.01",
                         f"{r} - tip_w / 2", span)])


def to_rz(pts):
    """rail15 (y, z[, radius]) points, root at z = 0 and tip at -depth, to
    (r, z) about the pin: y along the radius from rail_r, the tip out of the case."""
    return [(f"rail_r + ({p[0]})", f"root_z - ({p[1]})") + tuple(p[2:]) for p in pts]


def slot_points(b):
    """The rail15_housing slot at `clearance` (end_taper 0): the rail grown
    by the clearance normal to every face, the floor radius concentric, the
    lip sharp from a clearance of 0.2 up; reaching 1 past the mouth."""
    lip_end = "mouth_hw + t_root + 1"
    lip = ("root_radius - clearance",)
    floor = ("-depth - clearance", "tip_radius + clearance")
    return to_rz([(left("floor_hw"),) + floor, (right("floor_hw"),) + floor,
                  (right("mouth_hw"), "-clearance") + lip, (right(lip_end), "-clearance"),
                  (right(lip_end), "-clearance + 1"), (left(lip_end), "-clearance + 1"),
                  (left(lip_end), "-clearance"), (left("mouth_hw"), "-clearance") + lip])


def make_base(b):
    plate = b.box("base_plate", ("-plate_w / 2", "plate_w / 2"), ("plate_bot", "base_top"), ("0", "plate_t"))
    pin = b.cut("base_pin", b.fuse("base_pin_body", [
        b.cylinder("base_pin_shaft", "z", ("0", "0"), "pin_d / 2", ("plate_t - 0.5", "z_pin_top")),
        b.cone("base_pin_root", "z", ("0", "0"), "pin_d / 2 + root_r + 0.5", "pin_d / 2",
               ("plate_t - 0.5", "plate_t + root_r"))]),
        [b.cylinder("base_pilot", "z", ("0", "0"), "pilot_d / 2", ("z_pin_top - pilot_l", "z_pin_top + 1"))])
    ribs = b.common("base_ribs", [
        b.fuse("base_rib_rings", [v_rib(b, "base_rib1", "ring_r1"), v_rib(b, "base_rib2", "ring_r2")]),
        b.box("base_rib_clip", ("-plate_w", "plate_w"), ("plate_bot", "base_top"), ("0", "z_body + 1"))])
    holes = []
    for i, (sx, y) in enumerate((("-", "screw_y1"), ("", "screw_y1"), ("-", "screw_y2"), ("", "screw_y2"))):
        holes += countersunk(b, f"base_hole{i}", "plate_t", f"{sx}screw_x", y)
    return b.cut("base", b.fuse("base_body", [plate, pin, ribs]), holes)


def make_knob(b):
    # corners on +-x: a flat at 12 o'clock
    hexagon = b.polygon("knob_hexagon", 6, "knob_rc", ("z_body", "z_front"))
    centre = ("0", "0")
    cuts = [b.cylinder("knob_bore", "z", centre, "bore_r", ("plate_t - 1", "z_front + 1")),
            b.cone("knob_bore_chamfer", "z", centre, "pin_d / 2 + root_r + gap_r + 1", "pin_d / 2 + gap_r",
                   ("plate_t - 1", "plate_t + root_r")),
            b.cylinder("knob_counterbore", "z", centre, "cap_d / 2 + clearance", ("z_shoulder", "z_front + 1")),
            b.cone("knob_counterbore_floor", "z", centre, "bore_r - 0.5", "cap_d / 2 + clearance",
                   ("z_shoulder - (cap_d / 2 + clearance - bore_r) - 0.5", "z_shoulder")),
            b.revolve("knob_slot", slot_points(b), ("0", "360"))]
    if None in cuts:
        return None
    big, z = "knob_rc + 2", ("z_body - 1", "z_floor + 0.5")
    # Ramps: the slot again, ecc off the axis towards the ramp, kept to the
    # ramp's sector and outside rail_r (the lip). FreeCAD angles: from +x.
    for side, sx, start in (("r", "", "90 - notch_a - ramp_a"), ("l", "-", "90 + notch_a - 5")):
        shifted = b.revolve(f"knob_ramp_{side}_slot", slot_points(b), ("0", "360"))
        if shifted is None:
            return None
        shifted = b.move(shifted, (f"{sx}ecc * sin(ecc_a)", "ecc * cos(ecc_a)", None))
        zone = b.cut(f"knob_ramp_{side}_zone", b.sector(f"knob_ramp_{side}_sector", big, z, start, "ramp_a + 5"),
                     [b.cylinder(f"knob_ramp_{side}_inner", "z", centre, "rail_r", ("z_body - 2", "z_floor + 2"))])
        cuts.append(b.common(f"knob_ramp_{side}", [shifted, zone]))
    # Notch: the band the rail drops through, keeping the slot's inner side
    # (the rail only ever moves towards the axis).
    cuts.append(b.cut("knob_notch", b.box("knob_notch_box", ("-notch_x", "notch_x"), ("0", big),
                                          ("z_body - 1", "z_floor")),
                      [b.cylinder("knob_notch_keep", "z", centre, "mouth_in", ("z_body - 2", "z_floor + 2"))]))
    return b.cut("knob", hexagon, cuts)


def make_cap(b):
    return b.cut("cap", b.cylinder("cap_disc", "z", ("0", "0"), "cap_d / 2", ("z_pin_top", "z_front")),
                 countersunk(b, "cap_hole", "z_front", "0", "0"))


def make_lid(b):
    """The lid plate and its rail, mounted: preload above locked."""
    arc = b.revolve("lid_rail_arc", to_rz(rail_points("base_hw + 1")),
                    ("90 - rail_span / 2", "90 + rail_span / 2"))
    if arc is None:
        return None
    arc = b.move(arc, (None, "preload", None))
    rail = b.cut("lid_rail", arc, [b.box("lid_rail_clip", ("-knob_af", "knob_af"), ("-knob_af", "lid_bot"),
                                         ("-1", "root_z"))])
    plate = b.box("lid_plate", ("-plate_w / 2", "plate_w / 2"), ("lid_bot", "lid_bot + lid_h"), ("0", "root_z"))
    holes = []
    for i, (sx, y) in enumerate((("-", "lid_bot + lid_screw_in"), ("", "lid_bot + lid_screw_in"),
                                 ("-", "lid_bot + lid_h - lid_screw_in"), ("", "lid_bot + lid_h - lid_screw_in"))):
        holes += countersunk(b, f"lid_hole{i}", "root_z", f"{sx}screw_x", y)
    return b.cut("lid", b.fuse("lid_body", [plate, rail]), holes)


def make_bridge(b):
    return b.box("bridge", ("-plate_w / 2", "plate_w / 2"), ("base_top - bridge_lap", "lid_bot + bridge_lap"),
                 ("0", "bridge_t"))
