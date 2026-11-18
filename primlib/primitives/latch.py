"""LATCH -- over-centre bail latch: boxes and cylinders on printed ring hinges."""

# ##########################################################################
# !!! TODO, NEXT UPDATE: MOVE THE LATCH TO THE NEW HINGE.                !!!
# !!! The latch is built on `hinge_deprecated`, the old ring hinge (with  !!!
# !!! pin, sleeve, sleeve_clearance, plate and hole under it). The        !!!
# !!! library's hinge is now `hinge` (VerticalHinge3). The next change to !!!
# !!! the latch must rebuild its main and bail hinges on `hinge`, print-  !!!
# !!! test them, and then delete hinge_deprecated and the primitives only !!!
# !!! it uses.                                                            !!!
# ##########################################################################

from primlib.core import Builder, Param, Primitive, _hide, expand, grouped, value
from primlib.primitives.hinge_deprecated import HingeDeprecated
from primlib.primitives.support_rect import SupportRect

CATCH = (
    Param("height", "52", "latch height along the hinge axes: the main hinge sections, the arms and their gaps (a 50 mm bolt, its head recessed)"),
    Param("arms", "2", "bail arms, each between two main hinge sections (arms + 1 of them)"),
    Param("latch_width", "74", "overall, lever tip to the far side of the bail bar"),
    Param("max_depth", "11.5", "box wall to the lever front: how far the latch stands proud"),
    Param("hinge_diam", "9", "main hinge ring outside diameter"),
    Param("hinge_spacing", "12.5", "effective length to the body: bail hinge axis to main hinge axis"),
    Param("bail_length", "41.8", "effective length to the bail: bail hinge axis to bail bar axis"),
    Param("backset", "3.58",
          "bail hinge behind the line from the main hinge axis to the bar, closed (the over-centre lock)"),
    Param("bar_offset", "-2.1",
          "bail bar axis out from the main hinge axis, closed (+ = away from the wall)"),
    Param("arm_gap", "1.4", "bail arm to the parts below and above it (room for the slicer's supports)"),
    Param("bar_height", "=height / (2 * arms + 1) - 2 * arm_gap",
          "each bail arm's thickness along the hinge axes (print height): its band one bail hinge ring"),
    Param("main_gap", "1", "base top to keeper bottom: the gap at the lid/body parting line"),
)
HINGE_PARAMS = (
    Param("rings", "3", "rings in each main hinge, alternating base / lever (odd: a base ring at each end)"),
    Param("pin_diam", "4", "main hinge pin shaft diameter"),
    Param("pin_end", "6", "main hinge pin flare diameter"),
    Param("pin_angle", "45 deg", "main and bail hinge pin flare flank angle"),
    Param("hinge_tol", "0.4", "pin to ring clearance, normal to the faces"),
    Param("end_gap", "0.1", "gap between neighbouring rings"),
    Param("roll_clearance", "0.6", "base / lever to the other's rings"),
)
BAIL = (
    Param("bail_diam", "8", "bail hinge ring outside diameter (the arm's boss in the lever)"),
    Param("bail_bore", "3.4", "bail hinge rings' bore round their bolt, the hinge's pin"),
    Param("bail_flare", "5", "bail hinge bore's flare diameter at the ring ends (pointed, as with a printed pin)"),
    Param("slot_clr", "0.4", "arm to its slots in the base, lever and keeper"),
    Param("bolt_d", "3", "bolts' diameter (M3), along the bail bar and as the bail hinge pin"),
    Param("bolt_len", "50", "bolts' length under the head (ISO 7380 button head)"),
    Param("bolt_head_d", "5.7", "bolt button head diameter"),
    Param("bolt_head_h", "1.65", "bolt button head height"),
    Param("head_clr", "0.3", "head recess clearance over the head's diameter"),
    Param("head_gap", "0.2", "head recess depth past the head"),
    Param("bridge_skin", "0.2", "sacrificial layer across the bore at each head recess's roof, so the roof bridges; the bolt is pushed through it"),
    Param("bar_hole", "3.3", "bolt hole along the bail bar (M3 + print tolerance)"),
    Param("nut_af", "5.5", "nut across flats (M3)"),
    Param("nut_h", "4", "nut height (M3 nylock)"),
    Param("nut_clr", "0.3", "nut pocket clearance across flats (print tolerance)"),
    Param("seat_clr", "0.2", "keeper seat clearance round the bail bar"),
)
MOUNT = (
    Param("screw_len", "16", "countersunk mounting screw length, head included (4g x 5/8 in self-tapper)"),
    Param("screw_len_tol", "0.5", "added to screw_len when setting the head: the tip stops this short"),
    Param("ply_t", "6", "box wall the screws go into (ply sheet)"),
    Param("screw_past", "0", "screw tip past the far side of the ply (+ for a nut behind it)"),
    Param("screw_diam", "2.9", "screw thread diameter (4g)"),
    Param("screw_head_d", "5.6", "countersunk head diameter (4g)"),
    Param("screw_head_angle", "90 deg", "countersunk head included angle"),
    Param("screw_tol", "0.3", "print tolerance added to the screw holes' and countersinks' diameters"),
)
PARTS = (
    Param("wall_gap", "0.3", "lever back face to the box wall"),
    Param("lever_top", "7.5", "lever top below the main hinge axis"),
    Param("keeper_lip", "1.5", "keeper in front of the bail bar"),
    Param("keeper_min_wall", "0.5", "keeper's thinnest edge between the wall and the bar seat: anything thinner is cut off"),
    Param("support_gap", "0.2", "print supports to the parts across (print layout only)"),
    Param("support_z_gap", "0.1", "print supports' interface layers to the parts above and below"),
    Param("support_line_w", "0.44", "print supports' line width"),
    Param("support_layer_h", "0.2", "print supports' layer height (each interface layer)"),
    Param("support_lines", "4", "print supports' gap between walls, in line widths"),
    Param("support_density", "0.33", "print supports' interface layers, share of the area in strips"),
    Param("lever_taper", "3", "lever back face in from the wall plane at the tip, tapering to nothing at the bail hinge"),
    Param("lift_r", "6", "lever lift recess radius"),
    Param("lift_depth", "3", "lift recess depth into the lever's bottom face"),
    Param("lift_inset", "3", "lift recess centre in from the lever back"),
)

# Each main hinge section, between base (side A, leaf up) and lever (side B,
# leaf down), its axis on z; arms + 1 of them, `hinge_height` long, one at
# each end and one between each pair of arms.
# Both mounting faces are behind the axis, so the lever swings out. The
# base's tab runs from the wall to the axis plane; the lever's tab is the
# lever's full thickness, back to front. They reach 1 mm into the base and
# lever. No plates: the base and lever are the leaves.
HINGE = {"length": "hinge_height", "rings": "rings", "pin_diam": "pin_diam",
         "flare_diam": "pin_end", "flare_angle": "pin_angle", "barrel_diam": "hinge_diam",
         "tolerance": "hinge_tol", "end_gap": "end_gap", "ring_ends": "1",
         "roll_clearance": "roll_clearance",
         "pose_a": "90 deg", "pose_b": "270 deg",
         "pin_offset_a": "pin_y", "pin_offset_b": "pin_y - wall_gap",
         "tab_reach_a": "roll_clearance + 1",
         "tab_reach_b": "lever_top + 1 - hinge_diam / 2",
         "iface_thick": "pin_y - wall_gap",
         "iface_thick_b": "hinge_diam / 2 + pin_y - wall_gap",
         "angle_min": "0 deg", "angle_max": "180 deg",
         "plates": "0", "leaf_length": "1", "plate_thick": "1",
         "screws_x": "1", "screws_y": "1", "edge_margin": "0",
         "hole_type": "0", "screw_diam": "1", "head_diam": "2",
         "head_angle": "90 deg", "head_height": "1", "hole_tolerance": "0"}
# The bail hinge: 2 * arms + 1 rings the latch's width -- lever, arm, lever,
# ... -- so each arm's ring fills a gap between main hinge sections. Only its
# rings are used: the bolt is its pin, so the rings' bore is the pin's
# envelope round it; the lever and arms stand in for its tabs.
BAIL_HINGE = dict(HINGE, length="height", rings="2 * arms + 1", pin_diam="bolt_d",
                  flare_diam="bail_flare", barrel_diam="bail_diam",
                  tolerance="(bail_bore - bolt_d) / 2",
                  roll_clearance="slot_clr", pose_a="0 deg", pose_b="180 deg",
                  pin_offset_a="1", pin_offset_b="1", tab_reach_a="slot_clr + 1",
                  tab_reach_b="slot_clr + 1", iface_thick="1", iface_thick_b="1")


class Latch(Primitive):
    """**Needs updating: built on the deprecated hinge.** Its main and bail
    hinges are `hinge_deprecated`, the old ring hinge. The next update to
    the latch must move them to the library's `hinge` (VerticalHinge3) and
    print-test them; then `hinge_deprecated` and the primitives only it uses
    (`pin`, `sleeve`, `sleeve_clearance`, `plate`, `hole`) can go.

    An over-centre bail latch, closed, made to print and kept plain:
    hinge primitives for the hinges, and boxes and cylinders for
    everything else.

    The latch is `latch_width` from the lever tip to the far side of the
    bail bar, `height` along the hinge axes, and stands `max_depth` proud
    of the box wall. The base screws to the box body under the lid/body
    parting line; the lever hangs from it on `arms` + 1 main hinge
    sections, one at each end of the latch and one between each pair of
    arms (`rings` each, alternating base / lever round a captive pin
    column, a base ring at each end). Each of the `arms` bail arms,
    `bar_height` thick, works in a band between two sections, `arm_gap`
    clear of them, where there is no pin; the sections share the rest of
    the height, `hinge_height` each. The arms are straight bars pivoting
    in the lever on the bail hinge, `hinge_spacing` from the main hinge
    axis -- 2 * `arms` + 1 equal rings the latch's height, alternating
    lever and arm, round an M3 bolt as their pin, so for now each
    arm and its gaps must be one ring long (the build prints the
    difference). At `bail_length` along the arms they join the bail bar, a
    cylinder the main hinges' diameter the latch's height, reinforced by
    an M3 bolt along it; it drops into a half-round seat on top of the
    keeper, which screws to the lid. Both bolts are `bolt_len` button head
    bolts, the head in a recess in the bottom end, `recess_h` deep, and a
    nylock in a hex pocket in the top end; the recess's roof is a
    `bridge_skin` across the bore, printed as a bridge and pushed through
    by the bolt. The bail hinge's rings keep the bore of a printed pin
    (flared to pointed ring ends) round the bolt.

    Closed, the bar sits `bar_offset` out from the main hinge axis, and the
    bail hinge lies `backset` behind the line from the main hinge axis
    through the bar -- the lock: pulling the bail tight holds the lever
    shut. The over-centre angle, the stretch the bail takes while the bail
    hinge passes centre, and the arm's lean follow from these, and the
    build prints them with recommended targets.

    Each arm is the latch's depth, flush with the lever's back and front
    faces, a plain bar from the bail hinge axis to the bail bar. In each
    arm band the lever is cut right through from just under the bail hinge
    ring to its top, and deeper ahead of the bail hinge so the bail can
    swing 90 deg forward; the base is cut right through, so the base is a separate pad on
    each main hinge section, each screwed to the wall. The keeper is a block
    in line with each main hinge section, `hinge_height` along the axes,
    so it shows the same bands as the hinges; the arms pass between them.
    The bail bar bears on every block's seat. The front of the base is
    flush with the keeper's, and the two are the same height: the parting
    line is put midway in the `main_gap` between them.

    Base, lever, main hinge pins and bail print in place together,
    standing on end; the bail is loose until its hinge bolt goes in.
    Each arm's `arm_gap` above and below leaves room for the print
    supports; only its bail hinge ring meets the lever's rings, tip to
    tip, as hinge rings do. Base and keeper take a countersunk self-tapping
    screw, `screw_len` long with its head, in every main hinge section's
    band: the head sits `ply_t` - `screw_past` short of `screw_len` +
    `screw_len_tol` in front of the wall, so the screw runs into the
    `ply_t` box wall, its tip `screw_len_tol` short of the far side (with
    `screw_past` 0), and a bore the head's size runs to the front. The
    holes and countersinks are `screw_tol` over size.

    Latch frame: x out from the box wall, y up towards the lid, z along the
    hinge axes; the origin is on the main hinge axis at one end, so the box
    wall is the plane x = -pin_y and the latch spans z = 0 to
    `height`; `pin_y` and `lever_len` follow from `max_depth` and
    `latch_width`. The result is a compound: base, lever, main hinge pins,
    bail (arms, rings and bar), keeper, and the hardware (the bail bar's
    and the bail hinge's bolts and nuts). Print supports for the arms and the
    hinges above them (`{name}_print_support`) are made beside it, outside
    the compound, for printing base, lever and bail in place without the
    keeper. The number of keeper blocks and of the supports standing on
    the arms below is set when the latch is built; rebuild after changing
    `arms`.
    """

    freecad_only = "built on the deprecated hinge's own objects; records when it moves to hinge"

    title = "Latch"
    params, groups = grouped(
        ("Catch", CATCH), ("Main hinges", HINGE_PARAMS), ("Bail", BAIL),
        ("Mounting screws", MOUNT), ("Parts", PARTS))
    derived = (
        ("hinge_height", "(height - arms * (bar_height + 2 * arm_gap)) / (arms + 1)",
         "height of each main hinge section: the height left by the arms and their gaps, shared"),
        ("keeper_height", "hinge_height",
         "each keeper block's height along the axes: in line with a main hinge section"),
        ("pitch", "hinge_height + bar_height + 2 * arm_gap",
         "one main hinge section and the arm band above it"),
        ("z_lo", "hinge_height", "top of everything below the first arm"),
        ("z_arm", "z_lo + arm_gap", "the first arm's bottom"),
        ("z_top", "z_arm + bar_height", "the first arm's top"),
        ("z_up", "z_top + arm_gap", "bottom of everything above the first arm"),
        ("over_centre", "asin(backset / hinge_spacing)",
         "lock angle at the main axis: bail hinge past the main-axis-to-bar line"),
        ("arm_tilt", "asin(backset / bail_length)", "arm to the main-axis-to-bar line"),
        ("bar_r", "sqrt(bail_length ^ 2 - backset ^ 2) - sqrt(hinge_spacing ^ 2 - backset ^ 2)",
         "main axis to bar"),
        ("bar_dir", "asin(bar_offset / bar_r)",
         "main axis to bar, from vertical (+ = out from the wall)"),
        ("bail_lean", "bar_dir + arm_tilt",
         "arm's lean from the box wall, closed (+ = bar out)"),
        ("stretch", "bar_r - (bail_length - hinge_spacing)",
         "how much closer the bar must come while the bail hinge passes centre"),
        ("pivot_x", "-hinge_spacing * sin(bar_dir + over_centre)", "bail hinge axis, closed"),
        ("pivot_y", "-hinge_spacing * cos(bar_dir + over_centre)", "bail hinge axis, closed"),
        ("bar_x", "bar_offset", "bail bar axis, closed"),
        ("bar_y", "bar_r * cos(bar_dir)", "bail bar axis, closed"),
        ("lever_len", "latch_width - bar_y - hinge_diam / 2", "main hinge axis to the lever tip"),
        ("pin_y", "max_depth - hinge_diam / 2", "main hinge axis out from the box wall"),
        ("ring_clr", "bail_diam / 2 + slot_clr", "bail hinge ring's clearance radius in the lever"),
        ("front", "hinge_diam / 2", "lever front face, flush with the hinge rings"),
        ("back", "wall_gap - pin_y", "lever back face"),
        ("taper_top", "pivot_y - bail_diam / 2", "top of the lever back's taper: just under the bail hinge ring"),
        ("wall", "-pin_y", "box wall (and lid wall)"),
        ("base_bot", "hinge_diam / 2 + roll_clearance", "base bottom, clear of the lever's rings"),
        ("parting_y", "(bar_y + base_bot) / 2",
         "lid/body parting line above the main hinge axis: where base and keeper are the same height"),
        ("base_top", "parting_y - main_gap / 2", "base top"),
        ("keeper_bot", "parting_y + main_gap / 2", "keeper bottom"),
        ("recess_h", "bolt_head_h + head_gap", "bolt head recess depth into the bottom end"),
        ("recess_r", "(bolt_head_d + head_clr) / 2", "bolt head recess radius"),
        ("seat_r", "hinge_diam / 2 + seat_clr", "keeper seat radius, round the bail bar"),
        ("keeper_front", "bar_x + seat_r + keeper_lip", "keeper front face"),
        ("trim_y", "bar_y - sqrt(seat_r ^ 2 - (bar_x - wall - keeper_min_wall) ^ 2)",
         "keeper's edge at the wall cut off above this, where it is under keeper_min_wall"),
        ("base_front", "keeper_front", "base front face, flush with the keeper's"),
        ("seat_x", "wall + screw_len + screw_len_tol - (ply_t - screw_past)",
         "countersunk screw heads' top face: the screw through the ply, its tip screw_past beyond"),
        ("sink_depth", "(screw_head_d - screw_diam) / 2 / tan(screw_head_angle / 2)",
         "countersink depth"),
        ("screw_yb", "(base_bot + base_top) / 2", "base screw height"),
        ("screw_yk", "(keeper_bot + bar_y - seat_r) / 2",
         "keeper screw height, between its bottom and the bar seat"),
    )
    section_y = ("pivot_y", "screw_yb")
    intro = ("**Needs updating: built on the deprecated hinge.** The latch's main and bail hinges "
             "are `hinge_deprecated`, the old ring hinge. Its next update must move them to the "
             "library's `hinge` (VerticalHinge3) and print-test them; then `hinge_deprecated` and the "
             "primitives only it uses (`pin`, `sleeve`, `sleeve_clearance`, `plate`, `hole`) can go."
             "\n\nTBD -- the full description is written once the design is finalised.")
    # Third-angle views, dimensioned with the provided (Catch) parameters.
    # Front: along the latch and across the hinges; top: the catch
    # geometry round the three axes, at the latch's top; side: the depth.
    views = (
        ("front", "u", ("0", "-lever_len", "0"), ("0", "bar_y + hinge_diam / 2", "0"), 2,
         "latch_width"),
        ("front", "u", ("0", "base_top", "0"), ("0", "keeper_bot", "0"), 1, "main_gap"),
        ("front", "v", ("0", "-lever_len", "0"), ("0", "-lever_len", "height"), 1, "height"),
        ("front", "v", ("0", "bar_y", "z_lo"), ("0", "bar_y", "z_arm"), -2, "arm_gap"),
        ("front", "v", ("0", "bar_y", "z_arm"), ("0", "bar_y", "z_top"), -1, "bar_height"),
        ("top", "mark", ("0", "0", "height"), None, 0, ""),
        ("top", "mark", ("pivot_x", "pivot_y", "height"), None, 0, ""),
        ("top", "mark", ("bar_x", "bar_y", "height"), None, 0, ""),
        ("top", "line", ("0", "-lever_len", "height"), ("0", "bar_y + hinge_diam / 2", "height"),
         0, ""),
        ("top", "line", ("bar_x * (pivot_x * bar_x + pivot_y * bar_y) / (bar_x ^ 2 + bar_y ^ 2)", "bar_y * (pivot_x * bar_x + pivot_y * bar_y) / (bar_x ^ 2 + bar_y ^ 2)", "height"),
         ("bar_x", "bar_y", "height"), 0, ""),
        ("top", "u", ("0", "-hinge_diam / 2", "height"), ("0", "hinge_diam / 2", "height"), -3,
         "hinge_diam"),
        ("top", "a", ("0", "0", "height"), ("pivot_x", "pivot_y", "height"), 7, "hinge_spacing"),
        ("top", "a", ("pivot_x", "pivot_y", "height"), ("bar_x", "bar_y", "height"), 7.5,
         "bail_length"),
        ("top", "a", ("pivot_x", "pivot_y", "height"),
         ("bar_x * (pivot_x * bar_x + pivot_y * bar_y) / (bar_x ^ 2 + bar_y ^ 2)", "bar_y * (pivot_x * bar_x + pivot_y * bar_y) / (bar_x ^ 2 + bar_y ^ 2)", "height"), -6, "backset"),
        ("top", "v", ("0", "bar_y", "height"), ("bar_x", "bar_y", "height"), -1, "bar_offset"),
        ("side", "u", ("wall", "0", "0"), ("front", "0", "0"), 1, "max_depth"),
    )
    summary = (
        ("over_centre", "over-centre lock angle, deg (target 10 to 20)"),
        ("stretch", "bail stretch through centre, mm (target 0.3 to 0.6)"),
        ("bail_lean", "arm lean from the wall, deg (target about 0)"),
        ("lever_len", "lever length, mm"),
        ("hinge_height", "main hinge section length, mm"),
        ("(bar_height + 2 * arm_gap) - height / (2 * arms + 1)",
         "arm band less the bail hinge ring, mm (must be 0: each arm on its ring)"),
        ("keeper_front - seat_x", "mounting screw heads below the base and keeper fronts, mm"),
        ("height - recess_h - bolt_len", "bolts' tips below the top face, mm (must be 0 or more)"),
        ("recess_h + bolt_len - (height - nut_h)", "bolts' length in the nylocks, mm (nut_h: flush)"))

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        body = make_body_hinge(b)
        lever_hinge = make_lever_hinge(b)
        if None in (body, lever_hinge):
            return None
        base, lever_sides, pins = body
        lever_rings, arm, bail_core = lever_hinge
        lever = make_lever(b, lever_sides, lever_rings, bail_core)
        bar_hw = bolt_and_nut(b, "bar", ("bar_x", "bar_y"), "0 deg")
        bail_hw = bolt_and_nut(b, "bail", ("pivot_x", "pivot_y"), "30 deg")
        if None in (lever, bar_hw, bail_hw):
            return None
        parts = [base, lever, pins, arm, make_keeper(b), *bar_hw, *bail_hw]
        for obj in parts:
            _hide(obj)
        result = b.finish(b.compound(None, parts))
        # Print layout only, so not in the result: they stand where the
        # keeper does.
        if make_print_support(b, [base, lever, pins]) is None:
            return None
        return result


# The latch's full width, and the first arm's band (the others are
# `pitch` apart).
WIDTH = ("0", "height")
GAP = ("z_lo", "z_up")


def screws(b, part, y):
    """Countersunk screw holes along x at height `y`, one in the middle of
    each main hinge section's band, heads to the front: the shank, the
    countersink, and a bore the head's size in front of it."""
    c = (y, "hinge_height / 2")
    hole, head = "(screw_diam + screw_tol) / 2", "(screw_head_d + screw_tol) / 2"
    one = b.fuse(f"{part}_screw", [
        b.cylinder(f"{part}_shank", "x", c, hole, ("wall - 1", "seat_x")),
        b.cone(f"{part}_sink", "x", c, hole, head, ("seat_x - sink_depth", "seat_x")),
        b.cylinder(f"{part}_bore", "x", c, head, ("seat_x", "front + 20"))])
    return [b.array(f"{part}_screws", one, "z", "arms + 1", "0", "pitch")]


def hexagon(b, suffix, at, r, turn, z):
    """A hex prism on z about `at`, `r` to its corners, turned `turn`."""
    x, y = at
    return b.prism(suffix, [
        (f"{x} + {r} * cos({turn} + {k} * 60 deg)", f"{y} + {r} * sin({turn} + {k} * 60 deg)")
        for k in range(6)], "xy", z)


def bolt_tools(b, suffix, at, turn):
    """What a bolt along z at `at` cuts from its part: the recess for its
    button head in the bottom end and the hex pocket for its nut in the top
    end, turned `turn`. Returns [recess, pocket], or None."""
    pocket = hexagon(b, f"{suffix}_nut_pocket", at, "(nut_af + nut_clr) / 2 / cos(30 deg)",
                     turn, ("height - nut_h", "height + 1"))
    if pocket is None:
        return None
    return [b.cylinder(f"{suffix}_head_recess", "z", at, "recess_r", ("-1", "recess_h")), pocket]


def bolt_and_nut(b, suffix, at, turn):
    """A bolt along z at `at`, its head in the recess and its nylock in the
    pocket (see bolt_tools). Returns (bolt, nut), or None."""
    bolt = b.fuse(f"bolt_{suffix}", [
        b.cylinder(f"bolt_{suffix}_shank", "z", at, "bolt_d / 2", ("recess_h", "recess_h + bolt_len")),
        b.cylinder(f"bolt_{suffix}_head", "z", at, "bolt_head_d / 2",
                   ("recess_h - bolt_head_h", "recess_h"))])
    body = hexagon(b, f"nut_{suffix}_body", at, "nut_af / 2 / cos(30 deg)", turn,
                   ("height - nut_h", "height"))
    if body is None:
        return None
    nut = b.cut(f"nut_{suffix}", body, [
        b.cylinder(f"nut_{suffix}_bore", "z", at, "bolt_d / 2", ("height - nut_h - 1", "height + 1"))])
    return bolt, nut


def make_body_hinge(b):
    """The main hinge sections, one at each end and one between each pair
    of arms, and the base on them: a block slotted for each arm in front of
    a web on the wall. Returns (base, the lever's sides of the hinges, the
    pin columns), or None."""
    hinge = HingeDeprecated.build_bound(b.doc, f"{b.name}_hinge", b.sheet, b.env, HINGE)
    if hinge is None:
        return None
    side_a, side_b, pins = hinge.Links
    b.doc.removeObject(hinge.Name)
    pins.Label = f"{b.name}_hinge_pin_column"
    # The first section repeated up the latch, a pitch apart.
    sides_a = b.array("hinges_a", side_a, "z", "arms + 1", "0", "pitch")
    sides_b = b.array("hinges_b", side_b, "z", "arms + 1", "0", "pitch")
    pin_columns = b.array("hinge_pins", pins, "z", "arms + 1", "0", "pitch")
    slots = b.array("base_slots", b.box(
        "base_slot", ("wall - 1", "base_front + 1"), ("base_bot - 1", "base_top + 1"), GAP),
        "z", "arms", "0", "pitch")
    base = b.cut("base", b.fuse("base_body", [sides_a, b.box(
        "base_block", ("wall", "base_front"), ("base_bot", "base_top"), WIDTH)]),
        [slots] + screws(b, "base", "screw_yb"))
    return base, sides_b, pin_columns


def make_lever_hinge(b):
    """The bail hinge on its axis in the lever, and the bail on it: an arm
    in each arm band, a straight bar from the bail hinge, with the hinge's
    ring there, to the bail bar, a cylinder the main hinges' diameter
    the latch's height, bored for its reinforcing bolt. Returns (the
    lever's rings, bail, the rings' bore for the lever), or None. The
    hinge's printed pins are not used: a bolt is its pin."""
    hinge = HingeDeprecated.build_bound(b.doc, f"{b.name}_bail_hinge", b.sheet, b.env, BAIL_HINGE)
    if hinge is None:
        return None
    pin_column = hinge.Links[2]
    rings = {s: b.doc.getObject(f"{b.name}_bail_hinge_rings_{s}") for s in "ab"}
    b.doc.removeObject(hinge.Name)
    b.doc.removeObject(pin_column.Name)

    def at_pivot(suffix, obj):
        """`obj` moved onto the bail hinge axis."""
        return b.bind(b.array(suffix, obj, "x", "1", "pivot_x", "0"),
                      {"Placement.Base.y": "pivot_y"})

    lever_rings = at_pivot("bail_rings_lever", rings["a"])
    arm_rings = at_pivot("bail_rings_arm", rings["b"])
    # A bore the rings' size, through the lever and arms.
    core = b.cylinder("bail_core", "z", ("pivot_x", "pivot_y"), "bail_diam / 2",
                      ("-1", "height + 1"))

    # Each arm the latch's depth, back to front, from the bail hinge axis to
    # the bail bar; the lever is cut clear of its front corner's swing.
    bar = b.box("arm_bar", ("back", "front"), ("pivot_y", "bar_y"), ("z_arm", "z_top"))
    bars = b.array("arm_bars", bar, "z", "arms", "0", "pitch")
    rod = b.cylinder("bail_bar", "z", ("bar_x", "bar_y"), "hinge_diam / 2", WIDTH)
    # The bolt's head recess in the bar's bottom end, the nut's hex pocket
    # in its top end (so it can't turn), and the hole between them, a
    # bridge_skin under the recess's roof left for the bolt to push through.
    tools = bolt_tools(b, "bar", ("bar_x", "bar_y"), "0 deg")
    if tools is None:
        return None
    arm = b.fuse("arm", [b.cut("arm_cut", b.fuse("arm_body", [bars, rod]), [
        core, *tools,
        b.cylinder("bar_hole", "z", ("bar_x", "bar_y"), "bar_hole / 2",
                   ("recess_h + bridge_skin", "height + 1"))]),
        arm_rings])
    return lever_rings, arm, core


def make_lever(b, hinge_sides, bail_rings, bail_core):
    """The lever: a block on the main hinges' `hinge_sides`, its back face
    tapering `lever_taper` in from the bail hinge to the tip, with a lift
    recess and the bail hinge's lever rings, cut right through in each arm
    band from a ring clearance under the bail hinge axis up to the lever's
    top, and deeper ahead of the axis, so the bail can swing 90 deg forward:
    down as far below the axis as the arm's front corner is ahead of it,
    plus `slot_clr`. The bail hinge's bolt has its head recess in the bottom end ring,
    with a bridge_skin across the bore at its roof, and its nut pocket in
    the top end ring, a flat to the back face. Returns it, or None."""
    slots = b.array("lever_slots", b.box(
        "lever_slot", ("back - 1", "front + 1"), ("pivot_y - ring_clr", "-lever_top + 1"), GAP),
        "z", "arms", "0", "pitch")
    # Swung up to 90 deg forward, the arm stays in front of the bail hinge
    # axis and no further below it than its front corner is ahead of it.
    swings = b.array("lever_swings", b.box(
        "lever_swing", ("pivot_x - slot_clr", "front + 1"),
        ("pivot_y - (front - pivot_x) - slot_clr", "pivot_y"), GAP),
        "z", "arms", "0", "pitch")
    # The block, its back face tapering in towards the tip below the bail hinge.
    block = b.prism("lever_block", [
        ("back", "-lever_top"), ("back", "taper_top"), ("back + lever_taper", "-lever_len"),
        ("front", "-lever_len"), ("front", "-lever_top")], "xy", WIDTH)
    tools = bolt_tools(b, "bail", ("pivot_x", "pivot_y"), "30 deg")
    if None in (block, tools):
        return None
    skin = b.cylinder("bail_skin", "z", ("pivot_x", "pivot_y"), "recess_r",
                      ("recess_h", "recess_h + bridge_skin"))
    return b.cut("lever", b.fuse("lever_ringed", [
        b.cut("lever_cut", b.fuse("lever_body", [hinge_sides, block]), [
            b.cylinder("lift", "z", ("back + lift_inset", "-lever_len - lift_r + lift_depth"),
                       "lift_r", ("-1", "height + 1")),
            slots, swings, bail_core]), bail_rings, skin]), tools)


def make_print_support(b, around):
    """Print supports for the arms and the main hinge sections above them,
    for printing base, lever and bail in place without the keeper:
    rectangle supports, each from one face to the next, with their
    interface layers `support_z_gap` off those faces, in every arm band.
    Under the arm, from the main hinge section and base below up to it;
    over the arm, up to the section, its ring and the base above; both the
    latch's depth, like the arm; and under the rest of the arm, out to
    the bail bar: on the bed under
    the first arm, and on the arm below under each of the others.
    Across, they are cut `support_gap` clear of the bail hinge ring, with
    a wall a line wide round that cut to close it, and of the parts
    `around` them. Not part of the latch; left as its own compound,
    `{name}_print_support`. Returns it, or None.

    The supports for the first band are repeated up the latch, so they
    follow `arms`; the supports standing on the arms below are made when
    the latch is built, as many as `arms` is then."""
    g = "support_gap"
    depth = ("back", "front")  # the arm's, back to front
    start = f"pivot_y - ring_clr + {g}"
    free_y = (f"base_top + {g}", f"bar_y - hinge_diam / 2 - {g}")
    # (suffix, x, y, z, bottom gap, copies a pitch apart, first at): each
    # runs face to face in z, and a gap in from the part faces it meets across.
    regions = [
        ("under", depth, (start, "base_top"), ("z_lo", "z_arm"), "support_z_gap",
         "arms", "z_lo"),
        ("over", depth, (start, "base_top"), ("z_top", "z_up"), "support_z_gap",
         "arms", "z_top"),
        ("free", depth, free_y, ("0", "z_arm"), "0", "1", "0")]
    if value(b.sheet, expand("arms", b.env)) > 1:
        # Standing on the arm below.
        regions.append((
            "free_up", depth, free_y, ("z_top", "z_arm + pitch"), "support_z_gap", "arms - 1", "z_top"))
    # Clear across only: the bail hinge ring drawn again
    # `support_gap` bigger, and the parts `around` plus copies shifted that
    # far in x and y, square and diagonal, so corners clear too; cut one at
    # a time (fusing the copies gives an invalid shape; OCC's 3D offset
    # fails on the rings).
    parts = b.fuse("print_parts", around)
    ring_r = f"bail_diam / 2 + {g}"
    ring = b.cylinder("print_clear_ring", "z", ("pivot_x", "pivot_y"), ring_r, ("-1", "height + 1"))
    clear = [parts]
    for i, (dx, dy) in enumerate((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                                 if (dx, dy) != (0, 0)):
        shifted = b.array(f"print_clear_{i}", parts, "x", "1", f"{dx} * {g}", "0")
        clear.append(b.bind(shifted, {"Placement.Base.y": f"{dy} * {g}"}))
    pieces = []
    common = {"line_w": "support_line_w", "layer_h": "support_layer_h", "wall_lines": "1",
              "gap_lines": "support_lines", "interface_density": "support_density",
              "interface_gap": "support_z_gap"}
    for suffix, x, y, z, bottom, copies, z0 in regions:
        rect = SupportRect.build_bound(
            b.doc, f"{b.name}_support_{suffix}", b.sheet, b.env,
            dict(common, length=f"({x[1]}) - ({x[0]})", width=f"({y[1]}) - ({y[0]})",
                 height=f"({z[1]}) - ({z[0]})", bottom_gap=bottom))
        if rect is None:
            return None
        placed = b.bind(b.array(f"support_{suffix}_at", rect, "z", copies, z0, "pitch"),
                        {"Placement.Base.x": x[0], "Placement.Base.y": y[0]})
        if not suffix.startswith("free"):  # the free ones are clear of the ring
            placed = b.cut(f"support_{suffix}_ring", placed, [ring])
            # A wall round the ring's cut, the support's height, inside its
            # rectangle, in each band.
            span = (f"({z[0]}) + ({bottom})", f"({z[1]}) - support_z_gap")
            band = b.cut(f"support_{suffix}_ring_band",
                         b.cylinder(f"support_{suffix}_ring_out", "z", ("pivot_x", "pivot_y"),
                                    f"{ring_r} + support_line_w", span),
                         [b.cylinder(f"support_{suffix}_ring_in", "z", ("pivot_x", "pivot_y"),
                                     ring_r, ("-1", "height + 1"))])
            wall = b.common(f"support_{suffix}_ring_wall",
                            [band, b.box(f"support_{suffix}_area", x, y, ("-1", "height + 1"))])
            walls = b.array(f"support_{suffix}_ring_walls", wall, "z", copies, "0", "pitch")
            placed = b.fuse(f"support_{suffix}_closed", [placed, walls])
        for i, tool in enumerate(clear):
            placed = b.cut(f"support_{suffix}_cut{i}", placed, [tool])
        pieces.append(placed)
    return b.compound("print_support", pieces)


def make_keeper(b):
    """The keeper: a block in line with each main hinge section, each with
    a half-round seat for the bail bar on top (its edge at the wall cut
    back where it is thinner than `keeper_min_wall`) and a screw, the arms passing
    between them. Returns it, a compound of the blocks, `{name}_keeper_0`
    up, one per section as many as `arms` + 1 is when the latch is built."""
    tools = b.fuse("keeper_tools", [
        b.cylinder("seat", "z", ("bar_x", "bar_y"), "seat_r", ("-1", "height + 1")),
        b.box("keeper_trim", ("wall - 1", "wall + keeper_min_wall"), ("trim_y", "bar_y + 1"),
              ("-1", "height + 1"))]
        + screws(b, "keeper", "screw_yk"))
    # Each block its own part, so they can be laid out apart to print.
    blocks = int(value(b.sheet, expand("arms + 1", b.env)))
    keeper = b.compound("keeper", [
        b.cut(f"keeper_{i}", b.box(f"keeper_{i}_block", ("wall", "keeper_front"),
                                   ("keeper_bot", "bar_y"),
                                   (f"{i} * pitch", f"{i} * pitch + keeper_height")), [tools])
        for i in range(blocks)])

    return keeper
