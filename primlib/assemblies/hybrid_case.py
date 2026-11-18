"""HYBRID_CASE -- the hybrid case, the library's worked example, as an
assembly: printed corners and keyed edge runs holding plywood panels, the
part above the split a lid on its hinge line."""

from primlib.recipe import Assembly, Param, Part

# box_edge's and box_corner's section and screws, bound from the case's names.
SECTION = {"panel_t": "panel_t", "skin": "skin", "panel_gap": "panel_gap", "bevel": "bevel",
           "chamfer": "chamfer", "glue": "glue", "glue_ridge": "glue_ridge"}
SCREWS = {"drill_inset": "drill_inset", "screw_r": "screw_r", "head_r": "head_r", "head_h": "head_h",
          "screw_len": "screw_len"}

# The corners: (name, far in x, far in y, far in z, turns). A corner's arms
# run along +x, +y and +z; turned to face into the box from each corner.
CORNERS = [
    ("Corner_Left_Front_Bottom", False, False, False, []),
    ("Corner_Right_Front_Bottom", True, False, False, [("z", "90")]),
    ("Corner_Left_Rear_Bottom", False, True, False, [("z", "-90")]),
    ("Corner_Right_Rear_Bottom", True, True, False, [("z", "180")]),
    ("Corner_Left_Front_Top", False, False, True, [("x", "180"), ("z", "90")]),
    ("Corner_Right_Front_Top", True, False, True, [("y", "180")]),
    ("Corner_Left_Rear_Top", False, True, True, [("x", "180")]),
    ("Corner_Right_Rear_Top", True, True, True, [("x", "180"), ("z", "-90")]),
]

# The edges: (name, run part, start, turns). An edge run lies along its +z
# from its start, its walls towards -x and -y; turned along the box's edges.
EDGES = [
    ("Edge_X_Bottom_Front", "edge_x", ("reach", "0", "0"), [("x", "90"), ("z", "90")]),
    ("Edge_X_Top_Front", "edge_x", ("reach", "0", "height"), [("y", "90")]),
    ("Edge_X_Bottom_Rear", "edge_x", ("reach", "width", "0"), [("x", "180"), ("y", "-90")]),
    ("Edge_X_Top_Rear", "edge_x", ("reach", "width", "height"), [("x", "-90"), ("z", "-90")]),
    ("Edge_Y_Left_Bottom", "edge_y", ("0", "reach", "0"), [("x", "-90"), ("y", "-90")]),
    ("Edge_Y_Left_Top", "edge_y", ("0", "reach", "height"), [("x", "-90")]),
    ("Edge_Y_Right_Bottom", "edge_y", ("length", "reach", "0"), [("x", "90"), ("z", "180")]),
    ("Edge_Y_Right_Top", "edge_y", ("length", "reach", "height"), [("x", "-90"), ("y", "90")]),
] + [
    (f"Edge_Z_{side}_{half}", f"edge_z_{half.lower()}", (x, y, z), turns)
    for half, z in (("Lower", "reach"), ("Upper", "split_height"))
    for side, x, y, turns in (("Front_Left", "0", "0", []), ("Rear_Left", "0", "width", [("z", "-90")]),
                              ("Front_Right", "length", "0", [("z", "90")]),
                              ("Rear_Right", "length", "width", [("z", "180")]))
]

# The panels: (name, part, at, turns). A panel lies flat (length along x,
# width along y, thickness up z) and is turned into its wall: a side panel
# stands with its thickness out along -x, a front or rear one along -y.
SIDE, FRONT = [("y", "-90")], [("x", "90")]
PANELS = [
    ("Panel_Bottom", "panel_floor", ("panel_gap", "panel_gap", "-panel_t"), []),
    ("Panel_Top", "panel_floor", ("panel_gap", "panel_gap", "height"), []),
    ("Panel_Left_Lower", "panel_side_lower", ("0", "panel_gap", "panel_gap"), SIDE),
    ("Panel_Left_Upper", "panel_side_upper", ("0", "panel_gap", "split_height"), SIDE),
    ("Panel_Right_Lower", "panel_side_lower", ("length + panel_t", "panel_gap", "panel_gap"), SIDE),
    ("Panel_Right_Upper", "panel_side_upper", ("length + panel_t", "panel_gap", "split_height"), SIDE),
    ("Panel_Front_Lower", "panel_front_lower", ("panel_gap", "0", "panel_gap"), FRONT),
    ("Panel_Front_Upper", "panel_front_upper", ("panel_gap", "0", "split_height"), FRONT),
    ("Panel_Rear_Lower", "panel_front_lower", ("panel_gap", "width + panel_t", "panel_gap"), FRONT),
    ("Panel_Rear_Upper", "panel_front_upper", ("panel_gap", "width + panel_t", "split_height"), FRONT),
]

PLYWOOD = (0.85, 0.72, 0.52)

# With the rail on, each bottom Y edge is these, front to rear: (piece, part,
# start along the left edge from the front). The end piece (rail_end) sits at
# the rail's centre line; the others are box_edge's turned along +y, their -x
# wall down. The right edge is the left turned half round about z.
RAIL_ROW = [
    ("PlainFront", "rail_plain", "reach + gap"),
    ("NotchFront", "rail_notch", "n0 + gap / 2"),
    ("End", "rail_end", None),
    ("NotchRear", "rail_notch", "y0 + rail_w + gap"),
    ("PlainRear", "rail_plain", "width - n0 + gap / 2"),
]
ALONG_Y = [("x", "-90"), ("y", "-90")]     # box_edge's z along +y, its -x wall down, its -y wall out


def _upper(name):
    """Above the split: on the lid."""
    return "Top" in name or "Upper" in name


def _edge_run(run, key, lead_gap, end_gap):
    return dict({"run": run, "key": key, "fallback": "<<F>>", "small": "small", "medium": "medium",
                 "large": "large", "gap": "gap", "min_fit": "min_fit", "lead_gap": lead_gap,
                 "end_gap": end_gap, "size": "edge_size", "nominal_spacing": "nominal_spacing",
                 "min_spacing": "min_spacing"}, **SECTION, **SCREWS)


class HybridCase(Assembly):
    """The hybrid case: a box `length` by `width` by `height` inside, of
    plywood panels `panel_t` thick held by eight printed corners
    (box_corner) and sixteen keyed edge runs (edge_run, box_edge pieces),
    split at `split_height` into the base and a lid that opens by
    `open_angle` about the hinge line along the rear.

    Each edge type has its key (`key_x`, `key_y`, `key_z_lower`,
    `key_z_upper`): S, M and L pieces of fixed length, and F fit pieces
    sharing what's left; a key whose fit piece would be under `min_fit`
    falls back to F. The X and Y runs have a joint gap at both corners; the
    Z runs end flush at the split. The panels stop `panel_gap` short of the
    inside corners.

    **The rail** (`rail_on`): a Topeak rail under the bottom panel, centred,
    its middle sections keyed (`key_rail`, rail_run) between two end pieces
    (rail_end) that are one with the bottom Y edges above them. With it on,
    each bottom Y edge is a plain piece from the corner, a piece notched
    `notch_width` wide to clear the rack, the end piece, and the same again
    to the rear. A box too narrow for the notch drops the rail: its support
    deepens until the rack passes `notch_clear` under the edges, which
    aren't cut, and the notched pieces go. Too narrow even for that, the
    rail is left off.

    **The hinge row** (`key_hinge`, hinge_run) runs between the rear Z
    edges at the split, its axis the lid's: S, M, L and fit hinges, and T,
    the little corner hinge, whose leaves shorten only to clear a corner.
    Each hinge's lid half turns with the lid. **Two rotary latches** sit on
    the front across the split, `latch_spacing` apart: base, knob and cap on
    the body, the lid plate on the lid.

    As the original case model builds it, its first order sizes the
    same: every part shown (P2.2c-e)."""

    title = "Hybrid case"
    params = (
        Param("length", "350", "inside, along x"),
        Param("width", "260", "inside, along y"),
        Param("height", "180", "inside, along z"),
        Param("split_height", "110", "where the lid splits off, from the inside floor"),
        Param("open_angle", "0", "how far the lid is open, degrees; 0 shut"),
        Param("panel_t", "6.5", "the plywood's thickness"),
        Param("corner_size", "40", "a corner across each wall, from the outside face"),
        Param("skin", "5", "the wall over the panels' outsides"),
        Param("panel_gap", "3", "how far the panels stop short of the inside corner"),
        Param("bevel", "15", "the 45 degree bevel across each outside edge"),
        Param("chamfer", "0.5", "on the outward square edges"),
        Param("glue", "0", "pockets this deep behind the ridges; 0 for none (plywood)"),
        Param("glue_ridge", "0.6", "the ridges the panels sit on"),
        Param("drill_rows", "2", "a corner's rows of holes each way, on each face"),
        Param("drill_spacing", "12", "between a corner's holes, each way"),
        Param("drill_inset", "6", "the first hole from the inside corner, past the panel gap"),
        Param("screw_r", "1.4", "the screw hole"),
        Param("head_r", "2.75", "the countersink at the outside face"),
        Param("head_h", "2.7", "the countersink's depth"),
        Param("screw_len", "20", "the hole's length from the outside face"),
        Param("edge_size", "27", "an edge across its section, from the outside face"),
        Param("gap", "0.2", "between edge pieces, and between a piece and a corner"),
        Param("min_fit", "10", "the shortest fit piece"),
        Param("nominal_spacing", "30", "the longest screw pitch along an edge"),
        Param("min_spacing", "7", "under this between an edge's end holes, one middle hole"),
        Param("small", "20", "an S edge piece"),
        Param("medium", "35", "an M edge piece"),
        Param("large", "50", "an L edge piece"),
        Param("key_x", "'F", "the X edges' pieces (along the length), from the left corner"),
        Param("key_y", "'F", "the Y edges' pieces (along the width), from the front corner"),
        Param("key_z_lower", "'F", "the Z edges' pieces below the split, from the bottom corner"),
        Param("key_z_upper", "'F", "the Z edges' pieces above the split, from the split"),
        Param("rail_on", "1", "1 shows the rail, 0 leaves it off"),
        Param("key_rail", "'F", "the rail's middle sections, from the left end piece"),
        Param("notch_width", "125", "across the bottom Y edges, centred, to clear the rack"),
        Param("rack_gap", "0.15", "the rack's top face below the rail's root, seated"),
        Param("notch_clear", "1", "the notch's face above the rack's top face"),
        Param("drop_on", "15", "at each end, after the bevel: the tongue cut back to a key that drops into the rack"),
        Param("taper", "10", "after the drop-on: the tongue widens back to full size"),
        Param("drop_clear", "0.5", "the key inside the tongue's neck, each side"),
        Param("drop_chamfer", "1", "45 degrees on the key's tip edges"),
        Param("rail_screws", "1", "1: two rows of screws up through the rail into the bottom panel; 0 none"),
        Param("key_hinge", "'TFT", "the hinge row, from the left rear Z edge: S, M, L, F, and T the little one"),
        Param("hinge_pitch", "10", "the hinges' ring pitch; rings: the length over it, at least 2"),
        Param("hinge_side", "18", "each hinge leaf beyond its tab"),
        Param("hinge_little", "13", "the T hinge's length"),
        Param("hinge_pitch_little", "6.5", "the T hinge's ring pitch"),
        Param("latch_spacing", "=length / 3", "between the two latch knobs' axes, centred"),
    )
    groups = (
        ("Box", ("length", "width", "height", "split_height", "open_angle", "panel_t")),
        ("Corners", ("corner_size", "skin", "panel_gap", "bevel", "chamfer", "glue", "glue_ridge")),
        ("Screws", ("drill_rows", "drill_spacing", "drill_inset", "screw_r", "head_r", "head_h", "screw_len")),
        ("Edges", ("edge_size", "gap", "min_fit", "nominal_spacing", "min_spacing", "small", "medium", "large",
                   "key_x", "key_y", "key_z_lower", "key_z_upper")),
        ("Rail", ("rail_on", "key_rail", "notch_width", "rack_gap", "notch_clear", "drop_on", "taper", "drop_clear",
                  "drop_chamfer", "rail_screws")),
        ("Hinges and latches", ("key_hinge", "hinge_pitch", "hinge_side", "hinge_little", "hinge_pitch_little",
                                "latch_spacing")),
    )
    fixed = (("hinge_face", "7.5", "the hinge's axis to its mounting faces (pin_d / 2 + pin_gap + ring_wall "
                                   "+ backset): the lid's hinge line behind the rear panels"),
             ("rail_w", "61.6", "topeak_rail's modelled width (61.4 printed, its printer_width_offset 0.2)"),
             ("rail_depth", "6.35", "topeak_rail's tongue, root to tip"),
             ("hinge_half", "7", "a hinge's axis to its leaf's side plate (plate / 2)"),
             ("latch_plate", "80", "rotary_latch's plate width"),
             ("latch_joint", "7.6", "rotary_latch's joint_y: its split line above its origin"),
             ("rail_key_hw", "61.4 / 2 + 0.7 / tan(30) - 0.7 - 6.35 / tan(60) + 1 / tan(30) - 1",
              "topeak_rail's root half-width with its radius: the drop-on key's at the neck"))
    derived = (
        ("reach", "corner_size - (panel_t + skin)", "how far a corner reaches along an edge from the inside face"),
        ("panel_l", "length - 2 * panel_gap", "the bottom, top, front and rear panels' length"),
        ("panel_w", "width - 2 * panel_gap", "the bottom, top, left and right panels' width"),
        ("lower_h", "split_height - panel_gap", "the side panels' height below the split"),
        ("upper_h", "height - split_height - panel_gap", "the side panels' height above the split"),
        ("hinge_y", "width + panel_t + hinge_face", "the hinge line, front to back"),
        ("rail_dropped", "(width - notch_width) / 2 - reach - 1.5 * gap < min_fit ? 1 : 0",
         "1: too narrow for the notch; the rail drops below the edges, which aren't cut"),
        ("rail_base", "rail_dropped > 0 ? max(2; skin - rack_gap + notch_clear) : 2",
         "the rail's support: dropped, deep enough that the rack passes notch_clear under the edges"),
        ("rail_span", "rail_dropped > 0 ? rail_w + gap : notch_width",
         "the notch; dropped, no notch pieces: plain pieces from the corners to the end piece"),
        ("rail_plain", "(width - rail_span) / 2 - reach - 1.5 * gap", "a plain piece, from the corner to the notch"),
        ("rail_show", "rail_on > 0 ? (rail_plain < min_fit - 0.001 ? 0 : 1) : 0",
         "rail_on, unless the box is too narrow for even the dropped rail's pieces"),
        ("rail_notch", "(rail_span - rail_w) / 2 - 1.5 * gap", "a notched piece, from the notch's end to the end piece"),
        ("notch_depth", "rail_dropped > 0 ? 0 : skin - rail_base - rack_gap + notch_clear",
         "cut from the bottom Y edges' underside"),
        ("end_length", "max(corner_size; bevel * cos(45) + rail_base + rail_depth - skin + drop_on + taper + 1)",
         "an end piece's tongue, from the outside face"),
        ("rail_run", "length + 2 * (panel_t + skin) - 2 * end_length", "between the end pieces"),
        ("rail_screw_y", "(19.95 / 2 + rail_key_hw - drop_clear - drop_chamfer) / 2",
         "each screw row off the centre line: midway between the groove and the drop-on key's side"),
        ("edge_reach", "edge_size - (panel_t + skin)", "how far an edge reaches along a wall from the inside face"),
        ("hinge_run", "length - 2 * edge_reach", "the hinge row, between the rear Z edges"),
        ("hinge_a_little", "min(hinge_side; height - split_height - reach - gap - hinge_half)",
         "the T hinge's lid leaf: as the others, or short of the top corner by the gap"),
        ("hinge_b_little", "min(hinge_side; split_height - reach - gap - hinge_half)",
         "the T hinge's base leaf: as the others, or short of the bottom corner by the gap"),
        ("n0", "(width - rail_span) / 2", "the notch's front end"),
        ("y0", "(width - rail_w) / 2", "the end piece's front side"),
    )
    checks = (
        ("split_height - reach", "the split is inside the bottom corners: raise split_height"),
        ("height - split_height - reach", "the split is inside the top corners: lower split_height"),
        ("height - split_height - edge_reach - hinge_half - hinge_side >= 0 ? 1 : 0",
         "the lid is too short for the hinge leaves: lower split_height or hinge_side"),
        ("split_height - edge_reach - hinge_half - hinge_side >= 0 ? 1 : 0",
         "the base is too short for the hinge leaves: raise split_height or lower hinge_side"),
        ("hinge_a_little >= 0 ? 1 : 0", "the lid is too short for the T hinge"),
        ("hinge_b_little >= 0 ? 1 : 0", "the base is too short for the T hinge"),
        ("latch_spacing >= latch_plate + gap ? 1 : 0", "the latches overlap: raise latch_spacing"),
        ("(length - latch_spacing - latch_plate) / 2 >= edge_reach ? 1 : 0",
         "a latch reaches a front Z edge: lower latch_spacing"),
    )
    parts = (
        Part("corner", "box_corner", dict({"size": "corner_size", "drill_rows": "drill_rows",
                                           "drill_spacing": "drill_spacing"}, **SECTION, **SCREWS),
             colour=(0.25, 0.30, 0.38), to_print=True),
        Part("edge_x", "edge_run", _edge_run("length - 2 * reach", "key_x", "1", "1"), to_print=True),
        Part("edge_y", "edge_run", _edge_run("width - 2 * reach", "key_y", "1", "1"), to_print=True),
        Part("edge_z_lower", "edge_run", _edge_run("split_height - reach", "key_z_lower", "1", "0"), to_print=True),
        Part("edge_z_upper", "edge_run", _edge_run("height - split_height - reach", "key_z_upper", "0", "1"),
             to_print=True),
        Part("rail_end", "rail_end", dict({"size": "edge_size", "notch": "notch_depth", "corner_size": "corner_size",
                                           "nominal_spacing": "nominal_spacing", "min_spacing": "min_spacing",
                                           "screws": "rail_screws", "base_depth": "rail_base", "drop_on": "drop_on",
                                           "taper": "taper", "drop_clear": "drop_clear",
                                           "drop_chamfer": "drop_chamfer"}, **SECTION, **SCREWS), to_print=True),
        Part("rail_plain", "box_edge", dict({"length": "max(rail_plain; min_fit)", "size": "edge_size",
                                             "nominal_spacing": "nominal_spacing", "min_spacing": "min_spacing"},
                                            **SECTION, **SCREWS), colour=(0.80, 0.80, 0.78), to_print=True),
        Part("rail_notch", "box_edge", dict({"length": "max(rail_notch; min_fit)", "size": "edge_size",
                                             "relief": "notch_depth", "holes_x": "0",
                                             "nominal_spacing": "nominal_spacing", "min_spacing": "min_spacing"},
                                            **SECTION, **SCREWS), colour=(0.80, 0.80, 0.78), to_print=True),
        Part("sections", "rail_run", {"run": "rail_run", "key": "key_rail", "fallback": "<<F>>", "small": "small",
                                  "medium": "medium", "large": "large", "gap": "gap", "min_fit": "min_fit",
                                  "base_depth": "rail_base", "screws": "rail_screws", "screw_y": "rail_screw_y",
                                  "drill_inset": "drill_inset", "nominal_spacing": "nominal_spacing",
                                  "min_spacing": "min_spacing", "screw_r": "screw_r", "head_r": "head_r",
                                  "head_h": "head_h"}, to_print=True),
        Part("hinges", "hinge_run", {"run": "hinge_run", "key": "key_hinge", "fallback": "<<TFT>>",
                                     "small": "small", "medium": "medium", "large": "large", "little": "hinge_little",
                                     "gap": "gap", "min_fit": "min_fit", "pitch": "hinge_pitch",
                                     "pitch_little": "hinge_pitch_little", "side": "hinge_side",
                                     "side_a_little": "hinge_a_little", "side_b_little": "hinge_b_little",
                                     "open_angle": "-open_angle"}),
        Part("latch_base", "rotary_latch", {}, pieces=("base",), to_print=True),
        Part("latch_knob", "rotary_latch", {}, pieces=("knob",), colour=(0.93, 0.66, 0.18), to_print=True),
        Part("latch_cap", "rotary_latch", {}, pieces=("cap",), to_print=True),
        Part("latch_lid", "rotary_latch", {}, pieces=("lid",), to_print=True),
        Part("panel_floor", "panel", {"length": "panel_l", "width": "panel_w", "thickness": "panel_t"},
             colour=PLYWOOD),
        Part("panel_side_lower", "panel", {"length": "lower_h", "width": "panel_w", "thickness": "panel_t"},
             colour=PLYWOOD),
        Part("panel_side_upper", "panel", {"length": "upper_h", "width": "panel_w", "thickness": "panel_t"},
             colour=PLYWOOD),
        Part("panel_front_lower", "panel", {"length": "panel_l", "width": "lower_h", "thickness": "panel_t"},
             colour=PLYWOOD),
        Part("panel_front_upper", "panel", {"length": "panel_l", "width": "upper_h", "thickness": "panel_t"},
             colour=PLYWOOD),
    )

    @classmethod
    def place(cls, r):
        base, lid = [], []
        for name, fx, fy, fz, turns in CORNERS:
            at = ("length" if fx else "0", "width" if fy else "0", "height" if fz else "0")
            (lid if fz else base).append(r.instance(name, "corner", at=at, turn=turns))
        bottom_y = []
        for name, part, at, turns in PANELS + EDGES:
            placed = r.instance(name, part, at=at, turn=turns)
            if name.startswith("Edge_Y_") and name.endswith("_Bottom"):
                bottom_y.append(placed)
            else:
                (lid if _upper(name) else base).append(placed)
        rail = [r.instance("Rail", "sections", at=("end_length - (panel_t + skin)", "width / 2", "-panel_t - rail_base"))]
        for side in ("Left", "Right"):
            notched = []
            for piece, part, start in RAIL_ROW:
                if side == "Right":
                    piece = piece.replace("Front", "R_").replace("Rear", "Front").replace("R_", "Rear")
                if part == "rail_end":
                    at, turns = ("0", "width / 2", "0"), []
                else:
                    at, turns = ("0", start, "0"), list(ALONG_Y)
                if side == "Right":
                    at = ("length", "width / 2" if start is None else f"width - ({start})", "0")
                    turns = turns + [("z", "180")]
                placed = r.instance(f"Rail_{side}_{piece}", part, at=at, turn=turns)
                (notched if part == "rail_notch" else rail).append(placed)
            # Dropped, the notched pieces go: the plain pieces reach the end piece.
            rail.append(r.choose("1 - rail_dropped", r.group(f"notched_{side.lower()}", notched)))
        base.append(r.choose("rail_show", r.group("rail", rail), r.group("bottom_y", bottom_y)))
        # The hinge row on the hinge line; its lid halves turn on its own joint, as the lid's.
        base.append(r.instance("Hinge", "hinges", at=("edge_reach", "hinge_y", "split_height")))
        for side, sign in (("Left", "-"), ("Right", "+")):
            at = (f"length / 2 {sign} latch_spacing / 2", "-panel_t", "split_height - latch_joint")
            for piece in ("base", "knob", "cap", "lid"):
                placed = r.instance(f"Latch_{side}_{piece}", f"latch_{piece}", at=at, turn=[("x", "90")])
                (lid if piece == "lid" else base).append(placed)
        shut = r.group("lid", lid)
        return r.group("case", base + [r.joint("open", shut, ("0", "hinge_y", "split_height"), "x",
                                              "-open_angle")])
