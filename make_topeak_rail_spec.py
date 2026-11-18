"""Generate the Topeak rail's specification, primlib/primitives/topeak_rail_spec.html.

    freecadcmd make_topeak_rail_spec.py

The drawings are slices of the real solids and the verification table is
measured on them, so the page cannot drift from the code. Do not edit the
HTML by hand. The script stops if the working and the solids disagree.
"""

import math
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import primlib  # noqa: E402
from primlib.core import parameter_sheet  # noqa: E402
from make_docs import esc, page, table  # noqa: E402
from make_rail15_spec import (EXTRA_CSS, Drawing, arc_length, end_face, end_radii,  # noqa: E402
                              figure, flank_angle, loops_of, radii, section_edges, slide_overlap,
                              width_at, y_span, z_span)

CLEARANCE = 0.30
TAPER = 0.5
CLEARANCES = ("0.20", "0.30", "0.40", "0.50")
SEAT = 0.15  # mm, how far above a rack's face the rail's root sits


class Numbers:
    """The working by hand, in plain Python, independent of the primitives."""

    def __init__(self, c=CLEARANCE):
        half = math.tan(math.radians(30))
        self.c = c
        self.width, self.depth, self.r_tip, self.r_root = 61.4, 6.35, 0.7, 1.0
        self.offset = 0.2  # the rail's default printer_width_offset
        self.groove, self.g_depth = 19.95, 1.2
        self.base_depth = 2.0
        self.t_tip = self.r_tip / half
        self.t_root = self.r_root / half
        self.run = self.depth / math.tan(math.radians(60))
        self.tip_hw = self.width / 2 + self.t_tip - self.r_tip
        self.root_hw = self.tip_hw - self.run
        self.width_check = 2 * (self.tip_hw - self.t_tip + self.r_tip)
        self.neck = 2 * (self.root_hw + self.t_root - self.r_root)
        self.support = 2 * (self.root_hw + self.t_root)
        self.groove_top = self.groove - 2 * self.g_depth
        self.grow = c / half
        self.floor_hw = self.tip_hw + self.grow
        self.mouth_hw = self.root_hw + self.grow
        self.slot_widest = self.width + 2 * c
        self.mouth = self.neck + 2 * c  # the lip is rounded below a clearance of 1
        self.lip = self.r_root - c
        root2 = math.sqrt(2)
        self.guide_foot = self.groove + 2 * (c - c * root2)
        self.guide_top = self.guide_foot - 2 * self.g_depth


def level_ys(shape, z):
    return [v.Point.y for w in shape.slice(App.Vector(0, 0, 1), z) for v in w.Vertexes]


def slot_outer(shape, z, block=80.0):
    """The slot's width, cut level at z: wall to wall, ignoring the block's sides."""
    ys = [y for y in level_ys(shape, z) if abs(y) < block / 2 - 0.5]
    return max(ys) - min(ys)


def corner_span(shape, x, z, reach=15.0):
    """The width between the section's corners at level z, near the centre line."""
    ys = [v.Point.y for e in section_edges(shape, x) for v in e.Vertexes
          if abs(v.Point.z - z) < 1e-6 and abs(v.Point.y) < reach]
    return max(ys) - min(ys)


def centre_z(shape):
    """The z range of the solid on its centre line."""
    pts = [p for w in shape.slice(App.Vector(0, 1, 0), 0.0) for p in w.discretize(40)]
    return min(p.z for p in pts), max(p.z for p in pts)


def end_loops(shape):
    """The flat end face at x = 0, as loops to draw: slices beside it can come
    back incomplete on a loft."""
    return [[(p.y, p.z) for p in w.discretize(Deflection=0.0005)]
            for w in end_face(shape, 0.0).Wires]


def end_vertices(shape, x):
    return [v.Point for v in end_face(shape, x).Vertexes]


def real_step(foot, high, length, floor):
    """The rack's centre step from the author's notes, 45 degree sides, on a floor at z."""
    pts = [App.Vector(0, -foot / 2, floor), App.Vector(0, foot / 2, floor),
           App.Vector(0, foot / 2 - high, floor + high),
           App.Vector(0, -(foot / 2 - high), floor + high), App.Vector(0, -foot / 2, floor)]
    return Part.Face(Part.makePolygon(pts)).extrude(App.Vector(length, 0, 0))


# ------------------------------------------------------------------ the figures

def fig_rail(n, loops):
    d = Drawing((-38.5, 42.0, -10.5, 7.2), scale=10.5)
    d.outline(loops)
    d.line((n.root_hw, 0), (n.tip_hw, -n.depth), "build")
    d.line((-n.root_hw, 0), (-n.tip_hw, -n.depth), "build")
    d.dot(n.width / 2, n.r_tip - n.depth)
    d.dot(-n.width / 2, n.r_tip - n.depth)
    d.across(-n.width / 2, n.width / 2, n.r_tip - n.depth, -9.6, f"width {n.width:.2f}", weight="700")
    d.across(-n.groove / 2, n.groove / 2, -n.depth, -7.6, "groove_width 19.95")
    d.down(-n.depth, 0, -n.root_hw, -35.6, "depth 6.35")
    d.down(0, n.base_depth, n.support / 2, 32.5, "")
    d.text((33.2, 0.7), "base_depth 2.00", anchor="start")
    d.across(-n.support / 2, n.support / 2, n.base_depth, 4.6,
             f"base_width -1: the root including its radius, {n.support:.2f}")
    d.arc((n.tip_hw, -n.depth), 7.0, 120, 180)
    d.text((n.tip_hw - 9.8, -4.3), "angle 60°")
    d.leader((n.tip_hw - n.t_tip + 0.5, n.r_tip - n.depth - 0.5), (34.5, -8.2), "tip_radius 0.70")
    d.leader((n.root_hw + n.t_root - 0.71, -0.29), (34.0, -2.6), "root_radius 1.00")
    return figure(d, "the rail, dimensioned",
                  "The rail at its defaults, section across its length, tip down as modelled, true "
                  "scale. Blue is a slice of the real part. Red dashes are the flanks carried to the "
                  "sharp corners. Red dots are the two points the width is measured between, 0.70 "
                  "above the tip face, where the tangent to the radius is vertical.")


def fig_groove(n, loops):
    d = Drawing((-14.0, 14.0, -9.2, -2.6), scale=30.0)
    d.outline(loops)
    d.across(-n.groove / 2, n.groove / 2, -n.depth, -7.3, "groove_width 19.95, at the tip face", weight="700")
    d.across(-n.groove_top / 2, n.groove_top / 2, -n.depth + n.g_depth, -8.4,
             f"{n.groove_top:.2f} at its top")
    d.down(-n.depth, -n.depth + n.g_depth, n.groove / 2, 11.6, "groove_depth 1.20")
    d.text((-n.groove / 2 + 0.2, -4.6), "groove_angle 45°", anchor="start")
    return figure(d, "the centre groove",
                  "Detail of the centre groove. It is sized so the rack's centre step clears: the "
                  "step measures 19.05 at its foot and 1 to 1.3 high.")


def fig_root(n, loops):
    cy, cz = n.root_hw + n.t_root, -n.r_root
    d = Drawing((cy - 3.2, cy + 2.8, cz - 2.5, cz + 3.4), scale=85.0)
    d.outline(loops)
    d.mark(cy, cz, r=0.14)
    d.line((cy, cz), (cy - 0.707, cz + 0.707), "centre")
    d.text((cy + 0.25, cz - 0.1), "root_radius 1.00", anchor="start")
    d.across(cy - n.r_root, cy, cz, cz - 1.55, "")
    d.text((cy - 0.5, cz - 2.0), "1.00")
    return figure(d, "detail at the root",
                  f"Detail at the root, base_width -1. The radius turns the full 120° from the flank "
                  f"to the support's underside, and ends exactly at the support's edge, so half the "
                  f"support, {n.support / 2:.3f}, is one radius more than half the neck, "
                  f"{n.neck / 2:.3f}.")


def fig_wide(n, loops):
    d = Drawing((-42.0, 42.0, -8.0, 6.0), scale=10.0)
    d.outline(loops)
    d.across(-40, 40, n.base_depth, 4.4, "base_width 80")
    d.leader((n.root_hw + n.t_root - 0.71, -0.29), (36.0, -3.0), "root_radius 1.00", anchor="middle")
    return figure(d, "base_width 80",
                  "<b>base_width 80.</b> The root radii run into the support's underside, as at the "
                  "default, and the support carries on past them. It must be wider than the root "
                  "including its radius.")


def fig_clearance(n, rail_loops, housing_loops):
    d = Drawing((-42.0, 42.0, -10.8, 4.0), scale=10.0)
    d.outline(housing_loops, stroke="var(--mate-edge)", opacity=0.0, width=1.2)
    d.outline(rail_loops)
    return figure(d, "the clearance around the rail",
                  f"The clearance. The rail (blue, with base_width 80 so the face gap shows) and, in "
                  f"orange, the housing, whose slot is the rail grown {n.c:.2f} normal to every "
                  f"face, at true scale. The next three drawings zoom in.")


def fig_zoom_tip(n, rail, slot):
    cy, cz = n.tip_hw - n.t_tip, n.r_tip - n.depth
    d = Drawing((cy - 1.2, cy + 2.4, cz - 1.5, cz + 1.3), scale=170.0)
    d.outline(slot, stroke="var(--mate-edge)", opacity=0.0, width=1.3)
    d.outline(rail)
    d.mark(cy, cz, r=0.07)
    d.text((cy + 0.12, cz - 0.28), f"{n.r_tip:.2f}", anchor="start", colour="var(--edge)")
    d.text((cy + 0.62, cz - 0.93), f"{n.r_tip + n.c:.2f}", anchor="start", colour="var(--mate-edge)")
    d.across(cy + n.r_tip, cy + n.r_tip + n.c, cz, cz + 1.0, f"{n.c:.2f}", weight="700")
    d.text((cy + n.r_tip + n.c + 0.08, cz - 0.03), "widest", anchor="start")
    return figure(d, "detail at the tip",
                  f"Detail at the tip corner. The rail's radius and the slot's floor radius share a "
                  f"centre: {n.r_tip:.2f} and {n.r_tip + n.c:.2f}. The gap is {n.c:.2f} right round "
                  "the corner.")


def fig_zoom_lip(n, rail, slot):
    cy, cz = n.root_hw + n.t_root, -n.r_root
    d = Drawing((cy - 2.2, cy + 2.0, cz - 1.5, cz + 2.0), scale=150.0)
    d.outline(slot, stroke="var(--mate-edge)", opacity=0.0, width=1.3)
    d.outline(rail)
    d.mark(cy, cz, r=0.07)
    d.text((cy + 0.1, cz + 0.12), f"lip radius {n.lip:.2f}", anchor="start", colour="var(--mate-edge)")
    d.leader((cy - 0.71, cz + 0.71), (cy - 1.9, cz + 1.65), "root_radius 1.00")
    return figure(d, "detail at the mouth",
                  f"Detail at the root and the mouth. The lip's radius is root_radius - clearance, "
                  f"{n.lip:.2f}, concentric with the rail's root radius, so the gap there is still "
                  f"{n.c:.2f}.")


def fig_zoom_guide(n, rail, slot):
    d = Drawing((-13.0, 13.0, -8.4, -3.8), scale=32.0)
    d.outline(slot, stroke="var(--mate-edge)", opacity=0.0, width=1.3)
    d.outline(rail)
    return figure(d, "the guide in the groove",
                  f"The housing's centre guide (orange) in the rail's groove (blue). The guide is "
                  f"the groove shrunk {n.c:.2f} normal to its faces: {n.guide_foot:.2f} at its foot "
                  f"and {n.g_depth:.2f} high, with the floor {n.c:.2f} below the tip face.")


def fig_housing(n, loops):
    d = Drawing((-44.0, 44.0, -15.4, 3.4), scale=9.8)
    d.outline(loops)
    top = -n.c
    d.across(-n.mouth / 2, n.mouth / 2, -n.r_root, 1.5, f"mouth, narrowest {n.mouth:.2f}")
    d.across(-n.slot_widest / 2, n.slot_widest / 2, n.r_tip - n.depth, -12.3,
             f"slot, widest {n.slot_widest:.2f} (width + 2 x clearance)", weight="700")
    d.across(-40, 40, -10 - n.c, -14.5, "block_width 80")
    d.down(-10 - n.c, top, 40, 42.6, "block_depth 10")
    d.across(-n.guide_foot / 2, n.guide_foot / 2, -n.depth - n.c, -8.6, f"guide foot {n.guide_foot:.2f}")
    return figure(d, "the housing, dimensioned",
                  f"The matching part: the housing at clearance {n.c:.2f}, section across its length, "
                  "its mating face up, as modelled. Blue is a slice of the real part; the widths "
                  "marked mouth and slot are the empty space.")


def fig_taper_side(n, loops):
    """A slice along the rail through the tip face, x across and z up."""
    d = Drawing((-1.4, 6.0, -7.6, 2.5), scale=50.0)
    d.outline(loops)
    d.across(0, TAPER, -n.depth, -7.0, "")
    d.text((TAPER + 0.12, -7.08), f"end_taper {TAPER:.2f}", anchor="start")
    d.down(-n.depth, -n.depth + TAPER, 0, -0.75, f"{TAPER:.2f}")
    d.text((0.62, -5.75), "45°", anchor="start")
    d.text((3.3, -5.5), "tip face, depth 6.35 from here on")
    d.line((0, 0), (5.0, 0), "build")
    d.text((2.5, 0.9), "the support, unchanged to the very end", colour="var(--edge)", weight="600")
    d.text((2.5, -0.45), "the root, z = 0", colour="var(--edge)")
    return figure(d, "the taper along the rail",
                  f"A slice along the rail through its tip face, 15 off the centre line, at one end, "
                  f"end_taper {TAPER:.1f}. The rail carries on to the right. Its tip face comes in at "
                  "45° to the full depth; the flanks and the groove do the same, shown next.")


def fig_taper_rail(n, full, end):
    d = Drawing((5.0, 36.0, -8.0, 3.0), scale=27.0)
    d.outline(full)
    d.outline(end, fill="var(--mate)", stroke="var(--mate-edge)", opacity=0.55, width=1.2)
    d.across(n.groove / 2, n.width / 2, n.r_tip - n.depth, -7.5, "half the width, between the lead-ins")
    return figure(d, "the rail's end profile",
                  f"The right half of the rail's profile at its very end (orange) over its full "
                  f"profile (blue), end_taper {TAPER:.1f}. Every face of the tongue comes in "
                  f"{TAPER:.2f}, normal to itself, and the groove opens by the same. The support "
                  "stays.")


def fig_taper_slot(n, full, end):
    d = Drawing((4.0, 41.0, -11.0, 0.3), scale=23.0)
    d.outline(end, fill="var(--mate)", stroke="var(--mate-edge)", opacity=0.55, width=1.2)
    d.outline(full, fill="none", stroke="var(--edge)", opacity=0.0, width=1.5)
    return figure(d, "the slot's end profile",
                  f"The right half of the housing at its very end (orange), and in blue the outline "
                  f"of the slot between the lead-ins, clearance {n.c:.2f}, end_taper {TAPER:.1f}. "
                  f"Each face of the slot is {TAPER:.2f} further out at the end, and the guide "
                  f"{TAPER:.2f} smaller, so the opening meets the rail with room to spare.")


def fig_mated(n, rail, housing, label, caption):
    d = Drawing((-42.0, 42.0, -10.8, 4.2), scale=10.0)
    d.outline(housing, fill="var(--mate)", stroke="var(--mate-edge)")
    d.outline(rail)
    d.text((0, 0.5), label, colour="var(--edge)", weight="600")
    d.text((-37.0, -6.0), "housing", colour="var(--mate-edge)", weight="600")
    return figure(d, label, caption)


# ------------------------------------------------------------------ the page

def verify(n):
    """Build everything, compare it with the working. Returns the rows and
    the loops to draw; stops if anything disagrees by more than 0.0005."""
    doc = App.newDocument("TopeakRailSpec")
    sheet = parameter_sheet(doc)

    def make(key, name, **kw):
        kw.setdefault("length", "20")
        if key == "topeak_rail":  # the design size, unless a row says otherwise
            kw.setdefault("printer_width_offset", "0")
        part = primlib.make(key, doc, name, sheet=sheet, **kw)
        if part is None:
            raise SystemExit(f"{name} failed its checks")
        return part

    rail = make("topeak_rail", "Rail")
    wide = make("topeak_rail", "RailWide", base_width="80")
    offset = make("topeak_rail", "RailOffset", printer_width_offset="0.8")
    offset_h = make("topeak_rail_housing", "HousingOffset", printer_width_offset="0.8")
    offset_neg = make("topeak_rail_housing", "HousingNeg", printer_width_offset="-0.3")
    housings = {c: make("topeak_rail_housing", f"H{c.replace('.', '')}", clearance=c)
                for c in CLEARANCES}
    doc.recompute()
    taper_rail = make("topeak_rail", "RailTaper", end_taper=str(TAPER))
    taper_wide = make("topeak_rail", "RailTaperWide", end_taper=str(TAPER), base_width="80")
    taper_h = make("topeak_rail_housing", "HousingTaper", end_taper=str(TAPER))
    default = primlib.make("topeak_rail", doc, "RailDefault", sheet=sheet, length="20")
    doc.recompute()
    housing = housings["0.30"]
    x = 10.0
    bad = []

    def row(what, design, measured, note=""):
        if abs(design - measured) > 0.0005:
            bad.append(f"{what}: {design} / {measured}")
        return (esc(what), f"{design:.3f}", f"{measured:.4f}", esc(note))

    alias = lambda name: float(sheet.get(name))  # noqa: E731
    tip = -n.depth
    level = n.r_tip - n.depth
    rows = [
        row("Width, offset 0", n.width, rail.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("Model width at the default offset", n.width + n.offset,
            default.Shape.optimalBoundingBox().YLength, "61.40 + 0.20; bounding box of the solid"),
        row("Default offset on the sheet", n.offset, alias("RailDefault_printer_width_offset"),
            "RailDefault_printer_width_offset"),
        row("Width, base_width 80", n.width, width_at(wide.Shape, level), "level slice, 0.70 above the tip"),
        row("Fixed on the sheet: width", n.width, alias("Rail_width"), "Rail_width"),
        row("Fixed on the sheet: angle", 60.0, alias("Rail_angle"), "Rail_angle"),
        row("Fixed on the sheet: depth", n.depth, alias("Rail_depth"), "Rail_depth"),
        row("Fixed on the sheet: tip_radius", n.r_tip, alias("Rail_tip_radius"), "Rail_tip_radius"),
        row("Fixed on the sheet: root_radius", n.r_root, alias("Rail_root_radius"), "Rail_root_radius"),
        row("Fixed on the sheet: groove_width", n.groove, alias("Rail_groove_width"), "Rail_groove_width"),
        row("Fixed on the sheet: groove_depth", n.g_depth, alias("Rail_groove_depth"), "Rail_groove_depth"),
        row("Fixed on the sheet: groove_angle", 45.0, alias("Rail_groove_angle"), "Rail_groove_angle"),
        row("Angle on the solid", 60.0, flank_angle(rail.Shape, x), "from the flank's end points"),
        row("Tip radius on the solid", n.r_tip, radii(rail.Shape, x)[0], "smallest arc in the slice"),
        row("Root radius on the solid", n.r_root, radii(rail.Shape, x)[-1], "largest arc in the slice"),
        row("Root radius, arc length on the solid", math.radians(120), arc_length(rail.Shape, x, n.r_root),
            "the full 120° turn, 1.00 x 120° in radians"),
        row("Root radius, arc length, base_width 80", math.radians(120), arc_length(wide.Shape, x, n.r_root),
            "the same"),
        row("Support width, defaults", n.support, width_at(rail.Shape, 1.0), "level slice through the support"),
        row("Neck, defaults", n.neck, width_at(rail.Shape, -n.r_root), "level slice at the root radii's vertical tangent"),
        row("Depth plus base_depth", n.depth + n.base_depth, rail.Shape.optimalBoundingBox().ZLength, "bounding box"),
        row("Groove width at the tip face", n.groove, corner_span(rail.Shape, x, tip), "its two corners in the section"),
        row("Groove width at its top", n.groove_top, corner_span(rail.Shape, x, tip + n.g_depth),
            "its two corners in the section"),
        row("Groove depth", n.g_depth, centre_z(rail.Shape)[0] - tip, "on the centre line"),
        row("Slot widest, clearance 0.30", n.slot_widest, slot_outer(housing.Shape, level),
            "width + 2 x 0.30; level slice at the floor radii's vertical tangent"),
        row("Mouth, narrowest, clearance 0.30", n.mouth, slot_outer(housing.Shape, -n.r_root),
            "level slice at the lip radii's vertical tangent"),
        row("Guide at its foot, clearance 0.30", n.guide_foot, corner_span(housing.Shape, x, tip - n.c),
            "its two corners in the section"),
        row("Guide at its top, clearance 0.30", n.guide_top,
            corner_span(housing.Shape, x, tip - n.c + n.g_depth), "its two corners in the section"),
        row("Guide height, clearance 0.30", n.g_depth, centre_z(housing.Shape)[1] - (tip - n.c), "on the centre line"),
    ]
    for c, h in housings.items():
        over = rail.Shape.common(h.Shape).Volume + wide.Shape.common(h.Shape).Volume
        rows.append(row(f"Gap, clearance {c}, base_width 80", float(c),
                        wide.Shape.distToShape(h.Shape)[0], f"closest points; overlap {over:.3f} mm³"))
        rows.append(row(f"Gap, clearance {c}, base_width -1", float(c),
                        rail.Shape.distToShape(h.Shape)[0], "closest points on the solids"))
    tip_e = tip + TAPER
    end_rail = end_vertices(taper_rail.Shape, 0.0)
    end_h = end_vertices(taper_h.Shape, 0.0)
    rows += [
        row("end_taper 0.5: rail's width between the lead-ins", n.width,
            taper_rail.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("end_taper 0.5: rail's width at the very end", n.width - 2 * TAPER,
            y_span([p for w in end_face(taper_rail.Shape, 0.0).Wires
                    for p in w.discretize(Deflection=0.0005) if p.z < -1.0]), "end face, the tongue"),
        row("end_taper 0.5: rail's depth at the very end", n.depth - TAPER + n.base_depth,
            z_span(end_rail), "end face, tip to support top"),
        row("end_taper 0.5: tip radius at the very end", n.r_tip - TAPER,
            end_radii(taper_rail.Shape, 0.0)[0], "smallest arc on the end face"),
        row("end_taper 0.5: root radius at the very end", n.r_root,
            end_radii(taper_rail.Shape, 0.0)[-1], "largest arc on the end face"),
        row("end_taper 0.5: groove at the very end", n.groove + 2 * TAPER * (math.sqrt(2) - 1),
            y_span([p for p in end_rail if abs(p.y) < 15 and abs(p.z - tip_e) < 1e-6]),
            "end face, at the tip; each side opens 0.5 normal to it"),
        row("end_taper 0.5: support width, unchanged", n.support, width_at(taper_rail.Shape, 1.0),
            "level slice through the support"),
        row("end_taper 0.5: gap in the housing", n.c, taper_rail.Shape.distToShape(taper_h.Shape)[0],
            "closest points on the solids"),
        row("end_taper 0.5: gap, base_width 80", n.c, taper_wide.Shape.distToShape(taper_h.Shape)[0],
            "closest points on the solids"),
        row("end_taper 0.5: slot widest between the lead-ins", n.slot_widest,
            y_span([p for e in section_edges(taper_h.Shape, x) for p in e.discretize(60)
                    if abs(p.y) < 39.5 and tip - n.c - 0.01 < p.z < -n.c - 0.01]), "section halfway along"),
        row("end_taper 0.5: slot widest at the very end", n.slot_widest + 2 * TAPER,
            y_span([p for w in end_face(taper_h.Shape, 0.0).Wires for p in w.discretize(Deflection=0.0005)
                    if abs(p.y) < 39.5 and p.z < -n.c - 0.01]), "end face"),
        row("end_taper 0.5: mating face, unchanged", -n.c, max(p.z for p in end_h), "end face, top"),
        row("Slide, rail into housing: worst overlap", 0.0, slide_overlap(taper_rail.Shape, taper_h.Shape),
            "20 positions along x, from clear of one end to clear of the other, mm³"),
        row("Offset 0.8: rail's width in the model", n.width + 0.8,
            offset.Shape.optimalBoundingBox().YLength, "width + 0.8; bounding box"),
        row("Offset 0.8: groove, unchanged", n.groove, corner_span(offset.Shape, x, tip), "its two corners in the section"),
        row("Offset 0.8: depth plus base_depth, unchanged", n.depth + n.base_depth,
            offset.Shape.optimalBoundingBox().ZLength, "bounding box"),
        row("Offset 0.8: angle, unchanged", 60.0, flank_angle(offset.Shape, x), "from the flank's end points"),
        row("Offset 0.8 on both parts: gap, unchanged", n.c,
            offset.Shape.distToShape(offset_h.Shape)[0], "closest points on the solids"),
        row("Housing offset -0.3: slot widest", n.slot_widest - 0.3,
            slot_outer(offset_neg.Shape, level), "level slice"),
        row("Housing offset -0.3: guide, unchanged", n.guide_foot,
            corner_span(offset_neg.Shape, x, tip - n.c), "its two corners in the section"),
        row("Housing offset -0.3: block width, unchanged", 80.0,
            offset_neg.Shape.optimalBoundingBox().YLength, "bounding box"),
    ]
    seated = rail.Shape.copy()
    seated.translate(App.Vector(0, 0, SEAT))
    for high in (1.0, 1.3):
        step = real_step(19.05, high, 20.0, -6.35)
        over = seated.common(step).Volume
        rows.append(row(f"Against the measured step, 19.05 x {high}: overlap", 0.0, over,
                        f"closest {seated.distToShape(step)[0]:.3f}"))
    if bad:
        raise SystemExit(f"the specification disagrees with the solids: {bad}")
    cuts = {"rail": loops_of(rail.Shape, x), "wide": loops_of(wide.Shape, x),
            "housing": loops_of(housing.Shape, x),
            "taper_rail": loops_of(taper_rail.Shape, x), "taper_slot": loops_of(taper_h.Shape, x),
            "taper_rail_end": end_loops(taper_rail.Shape),
            "taper_slot_end": end_loops(taper_h.Shape),
            "taper_side": [[(p.x, p.z) for p in w.discretize(Deflection=0.0005)]
                           for w in taper_rail.Shape.slice(App.Vector(0, 1, 0), 15.0)]}
    return rows, cuts


def build_page():
    n = Numbers()
    rows, cuts = verify(n)
    body = [
        "<h1>Topeak rail</h1>",
        '<p class="sub">Specification of <code>topeak_rail</code> and <code>topeak_rail_housing</code> · '
        '<a href="topeak_rail.html">rail page</a> · <a href="topeak_rail_housing.html">housing page</a> · '
        '<a href="../../index.html">all primitives</a></p>',
        '<p class="warn"><b>The width is 61.40, what the print should measure.</b> A PETG piece '
        "modelled at 61.6 printed at 61.4 and fits a real rack, a whisker tight, so the rail's "
        "default <code>printer_width_offset</code> is 0.20. Sizes and drawings on this page are the "
        "design size, offset 0, unless a row says otherwise. Eight "
        "<b>fixed parameters</b> define the shape, and the rail has no tolerance. All sizes are in "
        "mm.</p>",

        "<h2>1. Parameters</h2>",
        "<h3>Fixed parameters</h3>",
        table(("", "name", "value", "what it is"), [
            ("1", "<code>width</code>", f"{n.width:.2f}", "Outside width: between vertical tangents to "
                                                         "the tip radii, what calipers read on the print"),
            ("2", "<code>angle</code>", "60°", "Slope of the sides, flank to the tip face"),
            ("3", "<code>depth</code>", "6.35", "Depth of the tongue, root to tip: 1/4\", set by the rack"),
            ("4", "<code>tip_radius</code>", "0.70", "The two tip corners"),
            ("5", "<code>root_radius</code>", "1.00", "The two root corners"),
            ("6", "<code>groove_width</code>", "19.95", "The centre groove, at the tip face"),
            ("7", "<code>groove_depth</code>", "1.20", "The centre groove, up from the tip face"),
            ("8", "<code>groove_angle</code>", "45°", "Slope of the groove's sides to the tip face"),
        ], num_cols=(2,)),
        "<h3>Variable parameters of the rail</h3>",
        table(("name", "default", "what it does"), [
            ("<code>length</code>", "20.00", "Rail length, along x"),
            ("<code>base_depth</code>", "2.00", "Depth of the support on the root. Must be more "
                                                "than 0: the root radius needs it"),
            ("<code>base_width</code>", "-1.00", "Width of the support. -1: as wide as the root "
                                                 f"including its radius, {n.support:.2f}"),
            ("<code>end_taper</code>", "0.00", "Option: lead-ins at both ends. 0: none. See section 6"),
            ("<code>printer_width_offset</code>", "0.20", "Added to the width in the model: see section 7"),
        ], num_cols=(1,)),
        '<p></p><code class="formula">primlib.make("topeak_rail", doc, name, length=20, base_depth=2, '
        "base_width=-1)\n# and optionally end_taper=0, printer_width_offset=0.2</code>",
        "<p>The sheet shows these thirteen values and nothing else.</p>",
        "<h3>Variable parameters of the matching part</h3>",
        table(("name", "default", "what it does"), [
            ("<code>clearance</code>", "0.30", "The gap between the printed rail and housing, "
                                               "normal to every face, per side"),
            ("<code>length</code>", "20.00", "Along x"),
            ("<code>block_width</code>", "80.00", "The block, across"),
            ("<code>block_depth</code>", "10.00", "The block, down from the mating face"),
            ("<code>end_taper</code>", "0.00", "Option: lead-ins at both ends of the slot. 0: none. See section 6"),
            ("<code>printer_width_offset</code>", "0.00", "Added to the slot's width in the model; "
                                                          "the housing's own value"),
        ], num_cols=(1,)),
        f"<p></p><p><code>base_width</code> -1 means the full root radius, as on <code>rail15</code>, "
        f"so the top is {n.support:.2f} wide.</p>",

        "<h2>2. The rail</h2>",
        fig_rail(n, cuts["rail"]),
        fig_groove(n, cuts["rail"]),
        fig_root(n, cuts["rail"]),

        f"<h2>3. Why the width is exactly {n.width:.2f}</h2>",
        "<p>A radius tangent to the tip face and the flank has its centre <code>t</code> in from "
        "the sharp corner, along the tip face, set by half the 60° angle. Its vertical tangent is "
        "one radius outside its centre. So half the width is the sharp corner, less <code>t</code>, "
        "plus the radius. The primitive turns that round to get the sharp corner from the width:</p>",
        f"""<code class="formula">t      = tip_radius / tan(angle / 2)      = 0.7 / tan 30°            = {n.t_tip:.6f}
tip_hw = width / 2 + t - tip_radius       = {n.width / 2:.2f} + {n.t_tip:.6f} - 0.7  = {n.tip_hw:.6f}

check, worked back from the sharp corner:
2 x (tip_hw - t + tip_radius) = 2 x ({n.tip_hw:.6f} - {n.t_tip:.6f} + 0.7) = {n.width_check:.6f}</code>""",
        "<p>Substituting, <code>t</code> and <code>tip_radius</code> cancel, leaving "
        "<code>width</code>. Neither <code>depth</code>, the root nor the groove enters it. The "
        "primitive refuses to build if the check differs from the width by a millionth of a mm.</p>",

        "<h2>4. The support, drawn</h2>",
        fig_wide(n, cuts["wide"]),

        "<h2>5. The clearance and the matching part</h2>",
        f"<p><code>clearance</code> (default {n.c:.2f}) is the gap between the printed parts. It's "
        "normal to every face and per side, so a width across the slot grows by twice it. The slot "
        "is the rail grown by it and the guide is the groove shrunk by it. The tip's radius keeps "
        "its centre and grows to 0.70 + clearance. The mouth's lip keeps the root radius's centre, "
        "with radius 1.00 - clearance.</p>",
        "<p><b>A real rack isn't made to these numbers.</b> This housing is the printed mate, for "
        "testing and for parts of our own. The rail's fit on a real rack is found by trying it: see "
        "section 8.</p>",
        fig_clearance(n, cuts["wide"], cuts["housing"]),
        fig_zoom_tip(n, cuts["wide"], cuts["housing"]),
        fig_zoom_lip(n, cuts["wide"], cuts["housing"]),
        fig_zoom_guide(n, cuts["wide"], cuts["housing"]),
        "<h3>The matching part</h3>",
        fig_housing(n, cuts["housing"]),
        "<h3>The two parts together</h3>",
        fig_mated(n, cuts["rail"], cuts["housing"], "rail (defaults)",
                  f"The default rail in the housing. The support, {n.support:.2f} wide, is wider than "
                  f"the mouth, {n.mouth:.2f}, and stands {n.c:.2f} above the mating face."),
        fig_mated(n, cuts["wide"], cuts["housing"], "rail (base_width 80)",
                  "The rail with base_width 80 (blue) in the housing (orange), built at the same "
                  "origin and sliced from the real solids."),
        "<h3>The slot at other clearances</h3>",
        table(("clearance", "slot, widest", "mouth, narrowest", "lip radius", "guide foot"),
              [(c, f"{m.slot_widest:.2f}", f"{m.mouth:.2f}", f"{m.lip:.2f}", f"{m.guide_foot:.2f}")
               for c, m in ((c, Numbers(float(c))) for c in CLEARANCES)],
              num_cols=(0, 1, 2, 3, 4)),

        "<h2>6. Tapered ends</h2>",
        "<p><code>end_taper</code> is an option on both parts, off by default: lead-ins, so the rail "
        "finds its way in rather than catching on the end. It's the same size on both ends of a "
        "part. Over the last <code>end_taper</code> of the length, the tongue shrinks by "
        "<code>end_taper</code> normal to its faces, its groove opening by the same, and the "
        "housing's slot grows by it, its guide shrinking. The change is the same as the distance "
        "along x, so the lead-in is at 45°.</p>",
        "<p>The rail's support doesn't change, nor does the housing's mating face. Between the "
        "lead-ins, both parts have exactly the profile shown above, so the width and the mouth are "
        "measured there. At the very end the rail's tip radius is 0.70 - <code>end_taper</code> and "
        "the slot's floor radius is 0.70 + clearance + <code>end_taper</code>, each concentric with "
        "the full radius, and the root radius and the lip stay as they are. So "
        "<code>end_taper</code> must be less than 0.70.</p>",
        fig_taper_side(n, cuts["taper_side"]),
        fig_taper_rail(n, cuts["taper_rail"], cuts["taper_rail_end"]),
        fig_taper_slot(n, cuts["taper_slot"], cuts["taper_slot_end"]),
        table(("at the very end, end_taper 0.5", "rail", f"slot, clearance {n.c:.2f}"), [
            ("Width", f"{n.width - 2 * TAPER:.2f}, measured", f"{n.slot_widest + 2 * TAPER:.2f}, at its widest"),
            ("Depth of the profile", f"{n.depth - TAPER:.2f}", f"{n.depth + TAPER:.2f}"),
            ("Tip or floor radius", f"{n.r_tip - TAPER:.2f}", f"{n.r_tip + n.c + TAPER:.2f}"),
        ], num_cols=(1, 2)),

        "<h2>7. The printer width offset</h2>",
        "<p>This keeps the printer out of the fit. <code>clearance</code> is only ever the gap "
        "between the printed parts; whatever the printer does to a part's width is corrected "
        "separately, on that part. Every size in this document is the design size, what the print "
        "should measure.</p>",
        '<code class="formula">width in the model = design width + printer_width_offset</code>',
        "<p>Half goes to each side, across y only: the flanks move sideways, unchanged, so the "
        "depth, the angle and the radii stay exact. The groove and the guide stay at their design "
        "size and the flat tip face and floor take up the difference. Each part has its own value, "
        "and the block's outside doesn't change.</p>",
        f'<code class="formula">rail:    printer_width_offset = {n.width:.2f} - (width measured at 0)\n'
        f"housing: printer_width_offset = (design mouth, section 5) - (mouth measured at 0)\n\n"
        "this rail, PETG, standing on end:\n"
        f"at model 61.60, measured 61.40  ->  0.20 under, so offset {n.offset:.2f}\n"
        f"model = {n.width:.2f} + {n.offset:.2f} = {n.width + n.offset:.2f}, should print {n.width:.2f}</code>",
        "<p>The rail's default offset is that 0.20. The housing's default stays 0: no slot has been "
        "printed and measured yet. For another printer or filament, print the rail at offset 0 "
        "and use the formula above.</p>",
        "<p>A negative offset is allowed. If the two offsets differ, the two models won't show the "
        "printed gap, and may even overlap as models. That's expected: it's the printed parts that "
        "have the clearance.</p>",

        "<h2>8. Where the width came from, and measuring a print</h2>",
        "<p><code>topeak_rail_print_test.stl</code> in the <code>claude</code> project has seven "
        "pieces at model widths 60.4 to 62.2 in 0.3 steps. In PETG, standing on end, the one "
        "modelled at <b>61.6</b> fitted a real rack best, a whisker tight, and measured <b>61.4</b>. "
        "That print is the design width. The working below ties it back to the rack by the "
        "1 : √3 : 2 triangle: a caliper reading at a rounded corner of radius r is 0.732 r per side "
        "from the sharp corner, and the flank runs 6.35 / √3 = 3.666 per side over the depth.</p>",
        '<code class="formula">rack, sharp mouth = mouth reading - 2 x 0.732 x mouth radius\n'
        "rack, sharp floor = sharp mouth + 2 x 3.666\n"
        "rack, widest      = sharp floor - 2 x 0.732 x floor radius\n\n"
        "with the mean mouth reading 57.19, and one radius r at the mouth and floor:\n"
        "rack, widest = 57.19 + 7.33 - 2.93 r\n"
        "a rack of about 61.5, just over the print, gives r = 1.03</code>",
        "<p>That radius is plausible, but it's a consistency check, not a measurement of the rack.</p>",
        table(("part", "measure", "design", "how"), [
            ("Rail", "<b>Width</b>", f"<b>{n.width:.2f}</b>",
             "Calipers across the tip radii, 0.70 up from the tip face, away from any lead-ins"),
            ("Rail", "Neck", f"{n.neck:.2f}", "Inside the root radii, 1.00 below the support"),
            ("Rail", "Support width", f"{n.support:.2f}", "Across the support's sides, at base_width -1"),
            ("Rail", "Groove", f"{n.groove:.2f}", "Across the groove at the tip face"),
            ("Rail", "Depth plus base_depth", f"{n.depth + n.base_depth:.2f}", "Tip face to the support's top"),
        ]),
        "<h3>Against a real rack</h3>",
        "<p>A real rack isn't modelled here; the test is the slide. A modelled rack at the mouth "
        "widths measured on real rails (56.8, 57.2, 58.4), checked on 2026-11-05 before that model "
        "was removed, gave no overlap and 0.150 clearance at each. The measured step is checked in "
        "section 9.</p>",

        "<h2>9. Verification</h2>",
        "<p>Each row compares the working above with a measurement of the actual solid, made when "
        "this page was generated. The script stops rather than write the page if any differ by "
        "more than 0.0005.</p>",
        table(("what", "design", "on the solid", "how"), rows, num_cols=(1, 2)),
    ]
    return page("Topeak rail specification", EXTRA_CSS + "".join(body))


if __name__ == "__main__" or (len(sys.argv) > 1 and sys.argv[1].endswith("make_topeak_rail_spec.py")):
    path = os.path.join(ROOT, "primlib", "primitives", "topeak_rail_spec.html")
    html_text = build_page()
    with open(path, "w") as fh:
        fh.write(html_text)
    print(f"wrote {path}")
    sys.stdout.flush()
    os._exit(0)
