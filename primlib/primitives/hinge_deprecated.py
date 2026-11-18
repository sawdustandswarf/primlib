"""HINGE (DEPRECATED) -- the old print-in-place ring hinge, kept only for the latch.

!!! DEPRECATED: don't use this for new work. The library's hinge is `hinge`
!!! (VerticalHinge3 / 3b). This one stays only because the over-centre `latch`
!!! is built on it; remove it, with pin, sleeve, sleeve_clearance, plate and
!!! hole, once the latch has moved to `hinge`.
"""


from primlib.core import Param, Primitive, _hide, bind_props, grouped
from primlib.primitives.pin import Pin
from primlib.primitives.plate import Plate
from primlib.primitives.sleeve import Sleeve
from primlib.primitives.sleeve_clearance import SleeveClearance

# Inner primitives' params as expressions over the hinge's names. The
# sleeves are built full length; the hinge cuts the gaps between rings.
SLEEVE = {"height": "pitch", "diam": "pin_diam", "diam_end": "flare_diam",
          "angle": "flare_angle", "diam_outer": "barrel_diam",
          "tolerance": "tolerance", "end_gap": "ring_ends == 1 ? end_gap : 0"}
CLEARANCE = dict(SLEEVE, clearance="roll_clearance", end_gap="0")
PIN = {"height": "pitch", "diam": "pin_diam", "diam_end": "flare_diam",
       "angle": "flare_angle", "clearance": "0"}
PLATE = {"length": "plates == 1 ? leaf_length : plate_off",
         "width": "length",
         "thickness": "plates == 1 ? plate_thick : (iface_thick < iface_thick_b ? iface_thick : iface_thick_b)",
         "screws_x": "screws_x", "screws_y": "screws_y",
         "edge_margin": "edge_margin",
         "hole_type": "plates == 1 ? hole_type : 0",
         "screw_diam": "screw_diam", "head_diam": "head_diam",
         "head_angle": "head_angle", "head_height": "head_height",
         "tolerance": "hole_tolerance"}
_SLEEVE = Sleeve.nested(SLEEVE)

MAIN = (
    Param("length", "40", "hinge length along the axis"),
    Param("leaf_length", "25", "side plate length, from the barrel's tangent outward"),
    Param("barrel_diam", "13", "ring outside diameter"),
    Param("pin_offset_a", "=barrel_diam / 2", "axis to side A mounting face"),
    Param("pin_offset_b", "=pin_offset_a", "axis to side B mounting face"),
    Param("angle_min", "0 deg", "least opening: 0 folded back to back"),
    Param("angle_max", "180 deg", "most opening: 180 open flat"),
)
PIN_RINGS = (
    Param("rings", "4", "number of rings (at least 2)"),
    Param("pin_diam", "6", "pin shaft diameter"),
    Param("flare_diam", "10", "pin flare diameter"),
    Param("flare_angle", "45 deg", "pin flare flank angle"),
    Param("tolerance", "0.4", "pin to sleeve clearance, normal to the faces"),
    Param("end_gap", "0.1", "gap between neighbouring rings"),
    Param("ring_ends", "1", "ring ends at the joints: 1 pointed tips, 0 flat lands"),
    Param("roll_clearance", "0.3", "tab and plate to the other side's rings"),
)
TABS_POSE = (
    Param("pose_a", "0 deg", "side A leaf direction as built"),
    Param("pose_b", "180 deg", "side B leaf direction as built (180 deg: open flat)"),
    Param("tab_reach_a", "1", "with plates = 0: side A's tab end beyond the ring's outside"),
    Param("tab_reach_b", "=tab_reach_a", "with plates = 0: side B's tab end beyond the ring's outside"),
    Param("iface_thick", "4", "side A tab thickness behind the mounting face"),
    Param("iface_thick_b", "=iface_thick", "side B tab thickness behind the mounting face"),
)
PLATES_SCREWS = (
    Param("plates", "1", "1 builds a plate on each tab, 0 tabs only"),
    Param("plate_thick", "=iface_thick", "plate thickness"),
    Param("screws_x", "2", "screws along the plate length"),
    Param("screws_y", "3", "screws along the hinge axis"),
    Param("edge_margin", "5", "plate edge to the nearest screw centre"),
    Param("hole_type", "2", "0 none, 1 plain, 2 countersunk, 3 counterbored"),
    Param("screw_diam", "3", "screw shank diameter"),
    Param("head_diam", "6", "screw head diameter"),
    Param("head_angle", "90 deg", "countersink included angle"),
    Param("head_height", "3", "counterbore depth (screw head height)"),
    Param("hole_tolerance", "0.1", "screw hole clearance, normal to the faces"),
)


def _on_plates(expr):
    """A check that only applies when the hinge has plates."""
    return f"plates == 1 ? ({expr}) : 1"


def _plate_clear(offset):
    """How far the plate's near corner clears the other side's ring, less
    roll_clearance."""
    return (f"sqrt((barrel_diam / 2) ^ 2 + ({offset} - plate_thick) ^ 2)"
            " - barrel_diam / 2 - roll_clearance")


class HingeDeprecated(Primitive):
    """**Deprecated: used only by `latch`.** Don't use it for new work: the
    library's hinge is `hinge` (VerticalHinge3). This is the old ring hinge,
    kept until the latch moves to `hinge`.

    A ring hinge along the z axis, printable in place. Five main
    specifications set its size and movement:

    - **Length** (`length`): along the axis.
    - **Leaf Length** (`leaf_length`): the side plate. It starts on the
      barrel's tangent, barrel_diam / 2 from the axis, and runs at right angles
      to the axis, so a leaf ends barrel_diam / 2 + leaf_length from the axis.
    - **Barrel Diameter** (`barrel_diam`): the rings' outside diameter.
    - **Pin Offsets** (`pin_offset_a`, `pin_offset_b`): the axis to each
      leaf's mounting face. Equal offsets put both faces in one plane when the
      hinge is open flat; B follows A until edited.
    - **Angle Range** (`angle_min`, `angle_max`): the opening between the
      leaves, 0 folded back to back and 180 open flat. These are checked
      against what the leaves allow (`angle_limit`) but nothing printed stops
      the hinge yet, so it can still be turned past them. Where the other
      side's ring tapers to its tip, at each joint and hinge end, its clearance
      cut narrows to `finger_r`, leaving a thin finger of tab along the mounting
      face, and those fingers touch first. With the face outside `finger_r`
      they run almost to `tab_u`, so the limit is just past flat: 182.6 deg at
      the defaults. Moving the face inside `finger_r` opens it up quickly:
      about 224 deg at offset 5.5 and 245 at offset 5, with a 13 mm barrel.

    A column of `rings` retained pins, one per ring, each rides in a sleeve.
    The rings alternate between side A (the bottom one) and side B. The pin
    column is captive -- its flares cannot pass the sleeve throats -- and
    spins freely in both sides.

    Neighbouring rings stand `end_gap` apart at the joint. With
    `ring_ends` = 1 (pointed, the default) each ring is the sleeve
    shortened by end_gap / 2 at both ends, so its ends stay sharp ridges
    and two rings meet tip to tip `end_gap` apart; the hinge's own ends
    are end_gap / 2 in from z = 0 and `length`. With `ring_ends` = 0 the
    rings run the full length and a slab `end_gap` thick is cut out at each
    joint, leaving each ring end a flat land `end_gap` wide. Either way the
    bore is the pin's envelope, so the pin keeps its `tolerance` everywhere.

    Each side has an interface: a rectangular tab, the hinge's length,
    joined to that side's rings and cut clear of the other side's rings by
    the sleeve clearance primitive -- the ring grown by `roll_clearance`
    normal to every face -- so the hinge turns. A tab runs from
    roll_clearance / 2 off the axis along the leaf direction `pose_a` /
    `pose_b`. Across the leaf, its mounting face lies `pin_offset` from the
    axis and the tab is `iface_thick` (`iface_thick_b` on side B) thick, behind
    that face; a tab may run past the axis, as it is cut clear of the pins and
    of the other side's rings. Side B is mirrored. `pose_b` = 180 deg builds
    it open flat, and an opening of X is `pose_b` = 360 deg - X.

    With `plates` = 1 each tab ends on the tangent and carries a plate: the
    plate primitive, continuing the tab outward, flush with the mounting face,
    the hinge's length wide, screw heads away from the mounting face. With
    `plates` = 0 the plate shrinks into its tab and the hinge is tabs only,
    each ending `tab_reach` beyond the ring's outside; it is a spreadsheet
    cell, so change it and recompute.

    The result is a compound of three solids: side A, side B and the pins.
    """

    freecad_only = "deprecated, goes when latch moves to hinge"

    title = "Hinge (deprecated)"
    params, groups = grouped(("Main specification", MAIN),
                             ("Pin and rings", PIN_RINGS),
                             ("Tabs and pose", TABS_POSE),
                             ("Plates and screws", PLATES_SCREWS))
    derived = (
        ("pitch", "length / rings", "one ring: pin segment and sleeve"),
        ("count_a", "ceil(rings / 2)", "rings on side A"),
        ("count_b", "floor(rings / 2)", "rings on side B"),
        ("tab_u", "roll_clearance / 2",
         "tabs start this far out, a roll_clearance apart when open flat"),
        ("ridge_r", _SLEEVE["ridge_r"],
         "tabs are cut back to this radius, clear of the pins"),
        ("tab_end_a", "plates == 1 ? barrel_diam / 2 : barrel_diam / 2 + tab_reach_a",
         "axis to the end of side A's tab"),
        ("tab_end_b", "plates == 1 ? barrel_diam / 2 : barrel_diam / 2 + tab_reach_b",
         "axis to the end of side B's tab"),
        ("plate_off", "((tab_reach_a < tab_reach_b ? tab_reach_a : tab_reach_b) - roll_clearance) / 2",
         "plate length with plates = 0: tucked inside the tab end"),
        ("plate_u_a", "plates == 1 ? tab_end_a : tab_end_a - plate_off",
         "side A plate start"),
        ("plate_u_b", "plates == 1 ? tab_end_b : tab_end_b - plate_off",
         "side B plate start"),
        ("offset_max", "pin_offset_a > pin_offset_b ? pin_offset_a : pin_offset_b",
         "the larger pin offset"),
        ("finger_r", "ridge_r + roll_clearance * (1 + tan(22.5 deg))",
         "radius of the clearance cut at a joint, where the rings taper to their tips"),
        ("angle_limit", "360 deg - 2 * (offset_max >= finger_r ? atan2(offset_max; tab_u) "
                        ": asin(offset_max / finger_r))",
         "most the leaves open before their tabs touch at the mounting faces"),
    )
    checks = (
        ("rings - 1.5", "rings must be at least 2"),
        ("plates == 0 ? 1 : (plates == 1 ? 1 : 0)", "plates must be 0 or 1"),
        ("end_gap", "end_gap must be positive"),
        ("ring_ends == 0 ? 1 : (ring_ends == 1 ? 1 : 0)", "ring_ends must be 0 or 1"),
        (f"{_SLEEVE['rim_h']} - end_gap / 2",
         "end_gap is too large for the ring ends"),
        ("roll_clearance", "roll_clearance must be positive"),
        ("iface_thick", "iface_thick must be positive"),
        ("iface_thick_b", "iface_thick_b must be positive"),
        ("barrel_diam / 2 - (pin_offset_a - iface_thick)",
         "pin_offset_a puts side A's tab clear of the rings"),
        ("barrel_diam / 2 - (pin_offset_b - iface_thick_b)",
         "pin_offset_b puts side B's tab clear of the rings"),
        ("pin_offset_a + barrel_diam / 2", "pin_offset_a puts side A's tab clear of the rings"),
        ("pin_offset_b + barrel_diam / 2", "pin_offset_b puts side B's tab clear of the rings"),
        ("plates == 1 ? 1 : tab_reach_a - roll_clearance",
         "tab_reach_a must exceed roll_clearance"),
        ("plates == 1 ? 1 : tab_reach_b - roll_clearance",
         "tab_reach_b must exceed roll_clearance"),
        (_on_plates("angle_min >= 0 deg ? 1 : 0"), "angle_min must not be negative"),
        (_on_plates("angle_max >= angle_min ? 1 : 0"),
         "angle_max must not be less than angle_min"),
        (_on_plates("angle_max <= angle_limit ? 1 : 0"),
         "angle_max is past angle_limit, where the leaves meet"),
        (_on_plates("pin_offset_a >= plate_thick ? 1 : 0"),
         "pin_offset_a must be at least plate_thick, so side A can fold to 0"),
        (_on_plates("pin_offset_b >= plate_thick ? 1 : 0"),
         "pin_offset_b must be at least plate_thick, so side B can fold to 0"),
        (_on_plates(f"{_plate_clear('pin_offset_a')} >= 0 ? 1 : 0"),
         "side A's plate is closer than roll_clearance to side B's rings"),
        (_on_plates(f"{_plate_clear('pin_offset_b')} >= 0 ? 1 : 0"),
         "side B's plate is closer than roll_clearance to side A's rings"),
    ) + Sleeve.nested_checks(SLEEVE) + SleeveClearance.nested_checks(CLEARANCE) \
      + Plate.nested_checks(PLATE, guard="plates == 1")
    section_y = ("0", "pin_offset_a - iface_thick / 2")

    @classmethod
    def build(cls, doc, name, sheet, env):
        import FreeCAD as App

        import Draft

        def column(base, count, start, step, label):
            """Draft array of `base` along z, bound to the sheet."""
            arr = Draft.make_ortho_array(base, App.Vector(1, 0, 0), App.Vector(0, 1, 0),
                                         App.Vector(0, 0, 1), 1, 1, 1, use_link=False)
            arr.Label = f"{name}_{label}"
            arr.Fuse = True
            bind_props(arr, sheet, {"NumberZ": count, "IntervalZ.z": step,
                                    "Placement.Base.z": start})
            return arr

        pin = Pin.build_bound(doc, f"{name}_pin", sheet, env, PIN)
        sleeve = Sleeve.build_bound(doc, f"{name}_sleeve", sheet, env, SLEEVE)
        keep = SleeveClearance.build_bound(doc, f"{name}_ring_clear", sheet, env,
                                           CLEARANCE)
        if None in (pin, sleeve, keep):
            return None
        e = env
        slab = doc.addObject("Part::Cylinder", f"{name}_gap")
        bind_props(slab, sheet, {"Radius": f"({e['barrel_diam']}) / 2 + 1",
                                 "Height": e["end_gap"]})
        doc.recompute()

        two_pitch = f"2 * ({e['pitch']})"
        half_gap = f"({e['end_gap']}) / 2"
        pins = column(pin, e["rings"], "0", e["pitch"], "pins")
        # One slab at each joint between two rings, none at the hinge ends;
        # moved clear of the hinge when the ring ends are pointed.
        gaps = column(slab, f"({e['rings']}) - 1",
                      f"+({e['ring_ends']}) == 1 ? -2 * ({e['length']}) - 10 : "
                      f"({e['pitch']}) - {half_gap}", e["pitch"], "gaps")
        sleeves = {}
        for side, count, start in (("a", e["count_a"], "0"),
                                   ("b", e["count_b"], e["pitch"])):
            full = column(sleeve, count, start, two_pitch, f"sleeves_{side}_full")
            cut = doc.addObject("Part::Cut", f"{name}_rings_{side}")
            cut.Base, cut.Tool = full, gaps
            sleeves[side] = cut
        # The other side's rings, each grown by roll_clearance: the tab cut.
        clears = {"a": column(keep, e["count_a"], "0", two_pitch, "ring_clear_a"),
                  "b": column(keep, e["count_b"], e["pitch"], two_pitch,
                              "ring_clear_b")}

        core = doc.addObject("Part::Cylinder", f"{name}_core")
        bind_props(core, sheet, {"Radius": e["ridge_r"], "Height": e["length"]})

        helpers = [pin, sleeve, keep, slab, pins, gaps, core,
                   *(s.Base for s in sleeves.values()), *sleeves.values(),
                   *clears.values()]
        sides = []
        for side, other in (("a", "b"), ("b", "a")):
            ang, off = f"({e['pose_' + side]})", f"({e['pin_offset_' + side]})"
            thick = f"({e['iface_thick' if side == 'a' else 'iface_thick_b']})"
            z0 = "0" if side == "a" else e["length"]
            # Leaf frame: u along the leaf, v across it (mirrored on side B).
            sign = "" if side == "a" else "-"
            ux, uy = f"cos({ang})", f"sin({ang})"
            vx, vy = f"{sign}(-sin({ang}))", f"{sign}cos({ang})"
            flip = "" if side == "a" else " * rotation(vector(1; 0; 0); 180 deg)"
            tilt = "90 deg" if side == "a" else "-90 deg"

            def at(u, v):
                return (f"vector(({u}) * {ux} + ({v}) * {vx}; "
                        f"({u}) * {uy} + ({v}) * {vy}; {z0})")

            tab = doc.addObject("Part::Box", f"{name}_tab_{side}")
            bind_props(tab, sheet, {
                "Length": f"({e['tab_end_' + side]}) - ({e['tab_u']})", "Width": thick,
                "Height": e["length"],
                "Placement": f"placement({at(e['tab_u'], f'{off} - {thick}')}; "
                             f"rotation(vector(0; 0; 1); {ang}){flip})"})
            cored = doc.addObject("Part::Cut", f"{name}_tab_{side}_cored")
            cored.Base, cored.Tool = tab, core
            rolled = doc.addObject("Part::Cut", f"{name}_tab_{side}_clear")
            rolled.Base, rolled.Tool = cored, clears[other]

            plate = Plate.build_bound(doc, f"{name}_plate_{side}", sheet, env, PLATE)
            if plate is None:
                return None
            bind_props(plate, sheet, {
                "Placement": f"placement({at(e['plate_u_' + side], off)}; "
                             f"rotation(vector(0; 0; 1); {ang}) * "
                             f"rotation(vector(1; 0; 0); {tilt}))"})

            fused = doc.addObject("Part::MultiFuse", f"{name}_side_{side}")
            fused.Shapes = [sleeves[side], rolled, plate]
            fused.Refine = True
            sides.append(fused)
            helpers += [tab, cored, rolled, plate]

        hinge = doc.addObject("Part::Compound", name)
        hinge.Links = sides + [pins]
        for obj in helpers + sides + [pins]:
            _hide(obj)
        return hinge
