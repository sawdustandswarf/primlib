"""Generate the 15 mm rail's specification, primlib/primitives/rail15_spec.html.

    freecadcmd make_rail15_spec.py

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

import primlib  # noqa: E402
from primlib.core import parameter_sheet  # noqa: E402
from make_docs import esc, page, table  # noqa: E402

CLEARANCE = 0.20
TAPER = 0.5
CLEARANCES = ("0.10", "0.20", "0.30", "0.40", "0.50")
EXTRA_CSS = """<style>
.warn { border-left:4px solid var(--mate-edge); padding:8px 14px; background:var(--panel);
        margin:0 0 14px; }
h3 { font-size:1rem; margin:22px 0 6px; }
figure { margin:0 0 14px; }
.formula { font:0.92em ui-monospace, monospace; background:var(--panel); padding:10px 14px;
           border-radius:6px; overflow-x:auto; white-space:pre; display:block; margin:0 0 12px; }
</style>"""


# ------------------------------------------------------------------ drawing

class Drawing:
    """An SVG of a (y, z) section, z up, with engineering dimensions."""

    def __init__(self, window, scale=36.0, pad=14.0):
        self.y0, self.y1, self.z0, self.z1 = window
        self.scale, self.pad = scale, pad
        self.parts = []

    def xy(self, y, z):
        return (self.pad + (y - self.y0) * self.scale,
                self.pad + (self.z1 - z) * self.scale)

    def outline(self, loops, fill="var(--solid)", stroke="var(--edge)", opacity=0.85, width=1.5):
        path = " ".join("M " + " L ".join("{:.2f},{:.2f}".format(*self.xy(*p)) for p in loop) + " Z"
                        for loop in loops)
        self.parts.append(f'<path d="{path}" fill="{fill}" fill-opacity="{opacity}" '
                          f'fill-rule="evenodd" stroke="{stroke}" stroke-width="{width}" '
                          f'stroke-linejoin="round"/>')

    def line(self, a, b, kind="thin"):
        style = {"thin": 'stroke="var(--muted)" stroke-width="0.7"',
                 "build": 'stroke="var(--axis)" stroke-width="0.9" stroke-dasharray="6 3"',
                 "centre": 'stroke="var(--axis)" stroke-width="0.8"'}[kind]
        (x1, y1), (x2, y2) = self.xy(*a), self.xy(*b)
        self.parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {style}/>')

    def text(self, at, text, anchor="middle", size=12, weight="normal", turn=0, colour="var(--fg)"):
        x, y = self.xy(*at)
        rot = f' transform="rotate({turn} {x:.2f} {y:.2f})"' if turn else ""
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
                          f'font-size="{size}" font-weight="{weight}" fill="{colour}"{rot}>'
                          f'{esc(text)}</text>')

    def _arrow(self, a, b):
        (x1, y1), (x2, y2) = self.xy(*a), self.xy(*b)
        self.parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                          f'stroke="var(--fg)" stroke-width="0.8" '
                          f'marker-start="url(#arw)" marker-end="url(#arw)"/>')

    def across(self, y1, y2, z_from, z_at, text, weight="normal"):
        """A dimension across y at z_at, extension lines from z_from."""
        self.line((y1, z_from), (y1, z_at))
        self.line((y2, z_from), (y2, z_at))
        self._arrow((y1, z_at), (y2, z_at))
        self.text(((y1 + y2) / 2, z_at + 4 / self.scale), text, weight=weight)

    def down(self, z1, z2, y_from, y_at, text):
        """A dimension along z at y_at, extension lines from y_from."""
        self.line((y_from, z1), (y_at, z1))
        self.line((y_from, z2), (y_at, z2))
        self._arrow((y_at, z1), (y_at, z2))
        self.text((y_at - 4 / self.scale, (z1 + z2) / 2), text, turn=-90)

    def mark(self, y, z, r=0.14):
        self.line((y - r, z), (y + r, z), "centre")
        self.line((y, z - r), (y, z + r), "centre")

    def dot(self, y, z, colour="var(--axis)"):
        x, yy = self.xy(y, z)
        self.parts.append(f'<circle cx="{x:.2f}" cy="{yy:.2f}" r="2.6" fill="{colour}"/>')

    def leader(self, tip, label_at, text, anchor="start"):
        self.line(tip, label_at)
        below = anchor == "middle" and label_at[1] < tip[1]
        self.text((label_at[0], label_at[1] + (-13 if below else 4) / self.scale), text, anchor=anchor)

    def arc(self, centre, r, a0, a1):
        steps = 24
        pts = [(centre[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
                centre[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps)))
               for i in range(steps + 1)]
        coords = " ".join("{:.2f},{:.2f}".format(*self.xy(*p)) for p in pts)
        self.parts.append(f'<polyline points="{coords}" fill="none" stroke="var(--fg)" '
                          f'stroke-width="0.8"/>')

    def svg(self, label):
        w = (self.y1 - self.y0) * self.scale + 2 * self.pad
        h = (self.z1 - self.z0) * self.scale + 2 * self.pad
        return (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" role="img" '
                f'aria-label="{esc(label)}"><defs><marker id="arw" viewBox="0 0 10 10" refX="9" '
                f'refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M 0 2 L 10 5 L 0 8 z" fill="var(--fg)"/></marker></defs>'
                + "".join(self.parts) + "</svg>")


def figure(drawing, label, caption):
    return f"<figure>{drawing.svg(label)}<figcaption>{caption}</figcaption></figure>"


# ------------------------------------------------------------------ the numbers

class Numbers:
    """The working by hand, in plain Python, independent of the primitives."""

    def __init__(self, c=CLEARANCE, depth=4.0):
        half = math.tan(math.radians(30))
        self.c, self.depth = c, depth
        self.width, self.r_tip, self.r_root = 15.0, 1.0, 0.2
        self.t_tip = self.r_tip / half
        self.t_root = self.r_root / half
        self.run = depth / math.tan(math.radians(60))
        self.tip_hw = self.width / 2 + self.t_tip - self.r_tip
        self.root_hw = self.tip_hw - self.run
        self.width_check = 2 * (self.tip_hw - self.t_tip + self.r_tip)
        self.neck = 2 * (self.root_hw + self.t_root - self.r_root)
        self.support = 2 * (self.root_hw + self.t_root)
        self.grow = c / half
        self.floor_hw = self.tip_hw + self.grow
        self.mouth_hw = self.root_hw + self.grow
        self.slot_widest = self.width + 2 * c
        self.mouth = (2 * self.mouth_hw if c >= self.r_root
                      else self.neck + 2 * c)
        self.lip = max(self.r_root - c, 0.0)


def loops_of(shape, x):
    wires = shape.slice(App.Vector(1, 0, 0), x)
    return [[(p.y, p.z) for p in w.discretize(Deflection=0.0002)] for w in wires]


def section_edges(shape, x):
    return [e for w in shape.slice(App.Vector(1, 0, 0), x) for e in w.Edges]


def radii(shape, x):
    return sorted({round(e.Curve.Radius, 6) for e in section_edges(shape, x)
                   if hasattr(e.Curve, "Radius")})


def arc_length(shape, x, radius):
    """The length of one arc of `radius` in the section."""
    return next(e.Length for e in section_edges(shape, x) if hasattr(e.Curve, "Radius")
                and abs(e.Curve.Radius - radius) < 1e-6)


def flank_angle(shape, x):
    """The slope of the longest sloping straight in the section, deg from y."""
    best = None
    for e in section_edges(shape, x):
        if hasattr(e.Curve, "Radius"):
            continue
        a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
        dy, dz = abs(a.y - b.y), abs(a.z - b.z)
        if dy > 1e-6 and dz > 1e-6 and (best is None or e.Length > best[0]):
            best = (e.Length, math.degrees(math.atan2(dz, dy)))
    return best[1]


def end_face(shape, x):
    """The flat end face of `shape` at x."""
    return next(f for f in shape.Faces if abs(f.BoundBox.XMin - x) < 1e-6
                and abs(f.BoundBox.XMax - x) < 1e-6)


def end_points(shape, x):
    return [p for w in end_face(shape, x).Wires for p in w.discretize(Deflection=0.0005)]


def y_span(pts):
    return max(p.y for p in pts) - min(p.y for p in pts)


def z_span(pts):
    return max(p.z for p in pts) - min(p.z for p in pts)


def end_radii(shape, x):
    """The radii on the end face at x, each worked out from three points on
    an edge that isn't straight (the loft's edges aren't always circles)."""
    found = set()
    for e in end_face(shape, x).Edges:
        a, b = e.FirstParameter, e.LastParameter
        p, q, r = (e.valueAt(t) for t in (a, (a + b) / 2, b))
        area = (q - p).cross(r - p).Length / 2
        if area > 1e-7:
            found.add(round((q - p).Length * (r - q).Length * (r - p).Length / (4 * area), 4))
    return sorted(found)


def housing_end_width(shape):
    """The slot's widest point on the housing's end face at x = 0."""
    return y_span([p for p in end_points(shape, 0.0) if abs(p.y) < 12.4 and -5.65 < p.z < -0.21])


def slide_overlap(rail, housing):
    """The worst overlap as the rail slides along x, through the housing."""
    worst = 0.0
    for i in range(20):
        moved = rail.copy()
        moved.translate(App.Vector(-21.0 + i * 42.0 / 19, 0, 0))
        worst = max(worst, moved.common(housing).Volume)
    return worst


def width_at(shape, z):
    """The solid's width across y, cut level at z."""
    pts = [v.Point.y for w in shape.slice(App.Vector(0, 0, 1), z) for v in w.Vertexes]
    return max(pts) - min(pts)


def slot_width(shape, z):
    """The slot's width, cut level at z: from the block's solid on one side
    of the centre line to the other."""
    pts = [v.Point.y for w in shape.slice(App.Vector(0, 0, 1), z) for v in w.Vertexes]
    return min(y for y in pts if y > 0) - max(y for y in pts if y < 0)


# ------------------------------------------------------------------ the figures

def fig_rail(n, loops):
    d = Drawing((-11.0, 13.0, -7.0, 3.3), scale=33.0)
    d.outline(loops)
    d.line((n.root_hw, 0), (n.tip_hw, -n.depth), "build")
    d.line((-n.root_hw, 0), (-n.tip_hw, -n.depth), "build")
    d.line((-n.tip_hw, -n.depth), (n.tip_hw, -n.depth), "build")
    d.mark(n.tip_hw - n.t_tip, n.r_tip - n.depth)
    d.mark(-(n.tip_hw - n.t_tip), n.r_tip - n.depth)
    d.dot(7.5, n.r_tip - n.depth)
    d.dot(-7.5, n.r_tip - n.depth)
    d.across(-7.5, 7.5, n.r_tip - n.depth, -5.3, "width 15.00", weight="700")
    d.down(-n.depth, 0, -n.root_hw, -9.6, "depth 4.00")
    d.down(0, 1, n.support / 2, 8.0, "")
    d.text((8.25, 0.38), "base_depth 1.00", anchor="start")
    d.across(-n.support / 2, n.support / 2, 1, 2.0,
             f"base_width -1: the root including its radius, {n.support:.2f}")
    d.arc((n.tip_hw, -n.depth), 1.9, 120, 180)
    d.text((n.tip_hw - 2.35, -3.75), "angle 60°", anchor="middle")
    d.leader((n.tip_hw - n.t_tip + 0.71, n.r_tip - n.depth - 0.71), (9.3, -5.3), "tip_radius 1.00")
    d.leader((n.root_hw + n.t_root - 0.17, -0.1), (9.3, -1.1), "root_radius 0.20")
    return figure(d, "the rail, dimensioned",
                  "The rail at its defaults, section across its length, tip down as modelled, "
                  "true scale. Blue is a slice of the real part. Red dashes are the sharp corners "
                  "the tip radii cut off. Red dots are the two points the width is measured "
                  "between, 1.00 above the tip face, where the tangent to the radius is vertical. "
                  "Crosses are the radii's centres.")


def fig_root(n, loops):
    cy, cz = n.root_hw + n.t_root, -n.r_root
    d = Drawing((cy - 1.0, cy + 1.0, cz - 0.8, cz + 0.75), scale=300.0)
    d.outline(loops)
    d.mark(cy, cz, r=0.04)
    d.line((cy, cz), (cy - n.r_root * 0.707, cz + n.r_root * 0.707), "centre")
    d.text((cy + 0.08, cz - 0.03), "root_radius 0.20", anchor="start")
    d.across(cy - n.r_root, cy, cz, cz - 0.55, "")
    d.text((cy - 0.1, cz - 0.67), "0.20")
    return figure(d, "detail at the root",
                  f"Detail at the root, base_width -1, 300 px/mm. The radius turns the full 120° "
                  f"from the flank to the support's underside, and ends exactly at the support's "
                  f"edge, so half the support, {n.support / 2:.3f}, is one radius more than half "
                  f"the neck, {n.neck / 2:.3f}.")


def fig_variant(loops, window, scale, caption, dims):
    d = Drawing(window, scale=scale)
    d.outline(loops)
    dims(d)
    return figure(d, "a variant", caption)


def fig_clearance(n, rail_loops, housing_loops):
    d = Drawing((-13.5, 13.5, -5.8, 2.4), scale=30.0)
    d.outline(housing_loops, stroke="var(--mate-edge)", opacity=0.0, width=1.2)
    d.outline(rail_loops)
    d.leader((n.floor_hw - 2.0, -n.depth - n.c), (8.5, -5.5),
             "the slot: the rail grown by the clearance", anchor="middle")
    d.leader((0, -n.depth), (-3.0, -5.5), "rail", anchor="middle")
    return figure(d, "the clearance around the rail",
                  f"The clearance. The rail (blue, with base_width 25 so the face gap shows) and, "
                  f"in orange, the rail grown {n.c:.2f} normal to every face, which is the slot, "
                  f"at true scale.")


def fig_zoom_tip(n, rail, slot):
    cy, cz = n.tip_hw - n.t_tip, n.r_tip - n.depth
    d = Drawing((cy - 0.3, cy + 2.2, cz - 1.6, cz + 0.95), scale=200.0)
    d.outline(slot, stroke="var(--mate-edge)", opacity=0.0, width=1.3)
    d.outline(rail)
    d.mark(cy, cz, r=0.08)
    d.line((cy, cz), (cy + n.r_tip * 0.707, cz - n.r_tip * 0.707), "centre")
    d.line((cy, cz), (cy + (n.r_tip + n.c) * 0.5, cz - (n.r_tip + n.c) * 0.866), "centre")
    d.text((cy + 0.28, cz - 0.62), "1.00", colour="var(--edge)")
    d.text((cy + 0.82, cz - 1.27), f"{n.r_tip + n.c:.2f}", colour="var(--mate-edge)")
    d.across(cy + n.r_tip, cy + n.r_tip + n.c, cz, cz + 0.42, f"{n.c:.2f}", weight="700")
    d.text((cy + n.r_tip + n.c + 0.06, cz - 0.03), "widest point", anchor="start")
    return figure(d, "detail at the tip",
                  f"Detail at the tip corner, 200 px/mm. The rail's radius and the slot's floor "
                  f"radius share a centre: {n.r_tip:.2f} and {n.r_tip + n.c:.2f}. The gap is "
                  f"{n.c:.2f} right round the corner.")


def fig_zoom_lip(n, rail, slot):
    cy, cz = n.root_hw + n.t_root, -n.r_root
    d = Drawing((cy - 1.0, cy + 1.0, cz - 0.9, cz + 0.6), scale=260.0)
    d.outline(slot, stroke="var(--mate-edge)", opacity=0.0, width=1.3)
    d.outline(rail)
    d.leader((cy - 0.13, cz + 0.15), (cy - 0.85, cz - 0.28), "root_radius 0.20")
    d.leader((cy, cz), (cy + 0.35, cz - 0.42), f"sharp lip, at clearance {n.c:.2f}")
    return figure(d, "detail at the mouth",
                  f"Detail at the root and the mouth, 260 px/mm. The lip's radius would be "
                  f"root_radius - clearance, which is 0 at {n.c:.2f}: a sharp corner, exactly at "
                  f"the centre of the rail's root radius. The gap there is still {n.c:.2f}.")


def fig_housing(n, loops):
    d = Drawing((-15.0, 15.0, -9.0, 2.0), scale=30.0)
    d.outline(loops)
    top = -n.c
    d.across(-n.mouth_hw, n.mouth_hw, top, 1.0, f"mouth, narrowest {n.mouth:.2f}")
    d.line((-n.mouth_hw, top), (-n.floor_hw, -n.depth - n.c), "build")
    d.line((n.mouth_hw, top), (n.floor_hw, -n.depth - n.c), "build")
    d.line((-n.floor_hw, -n.depth - n.c), (n.floor_hw, -n.depth - n.c), "build")
    d.across(-n.slot_widest / 2, n.slot_widest / 2, n.r_tip - n.depth, -7.15,
             f"slot, widest {n.slot_widest:.2f} (15 + 2 x clearance)", weight="700")
    d.across(-12.5, 12.5, -6 - n.c, -8.2, "block_width 25")
    d.down(-6 - n.c, top, 12.5, 13.8, "block_depth 6")
    d.down(-n.depth - n.c, top, -12.5, -13.4, "depth 4")
    d.leader((n.tip_hw - n.t_tip + 0.85, n.r_tip - n.depth - 0.85), (9.3, -5.75),
             f"floor radius {n.r_tip + n.c:.2f}")
    return figure(d, "the housing, dimensioned",
                  f"The matching part: the housing at clearance {n.c:.2f}, section across its "
                  f"length, its mating face up, as modelled. Blue is a slice of the real part; "
                  f"the widths shown are the slot's, the empty space. Red dashes are the floor's "
                  f"sharp corners.")


def fig_taper_side(n, loops):
    """A slice along the rail's centre line, x across and z up."""
    d = Drawing((-1.3, 6.0, -5.2, 1.5), scale=70.0)
    d.outline(loops)
    d.across(0, TAPER, -n.depth, -4.6, "")
    d.text((TAPER + 0.12, -4.68), f"end_taper {TAPER:.2f}", anchor="start")
    d.down(-n.depth, -n.depth + TAPER, 0, -0.75, f"{TAPER:.2f}")
    d.text((0.62, -3.62), "45°", anchor="start")
    d.text((3.2, -3.3), "tip face, depth 4 from here on")
    d.line((0, 0), (5.0, 0), "build")
    d.text((2.5, 0.4), "the support, unchanged to the very end", colour="var(--edge)", weight="600")
    d.text((2.5, -0.45), "the root, z = 0", colour="var(--edge)")
    return figure(d, "the taper along the rail",
                  f"A slice along the rail's centre line at one end, end_taper {TAPER:.1f}. The rail "
                  "carries on to the right. Its tip face comes in at 45° to the full depth; the "
                  "flanks do the same, shown next.")


def fig_taper_rail(n, full, end):
    d = Drawing((-9.5, 9.5, -5.3, 1.5), scale=36.0)
    d.outline(full)
    d.outline(end, fill="var(--mate)", stroke="var(--mate-edge)", opacity=0.55, width=1.2)
    d.across(-7.5, 7.5, n.r_tip - n.depth, -4.7, "width 15.00, between the lead-ins", weight="700")
    return figure(d, "the rail's end profile",
                  f"The rail's profile at its very end (orange) over its full profile (blue), "
                  f"end_taper {TAPER:.1f}. Every face of the tapered part comes in {TAPER:.2f}, "
                  "normal to itself.")


def fig_taper_slot(n, full, end):
    d = Drawing((-13.0, 13.0, -7.3, 1.2), scale=33.0)
    d.outline(end, fill="var(--mate)", stroke="var(--mate-edge)", opacity=0.55, width=1.2)
    d.outline(full, fill="none", stroke="var(--edge)", opacity=0.0, width=1.5)
    d.across(-n.slot_widest / 2, n.slot_widest / 2, n.r_tip - n.depth, -6.85,
             f"slot, widest {n.slot_widest:.2f}, between the lead-ins", weight="700")
    return figure(d, "the slot's end profile",
                  f"The housing at its very end (orange), and in blue the outline of the slot "
                  f"between the lead-ins, clearance {n.c:.2f}, end_taper {TAPER:.1f}. Each face of "
                  f"the slot is {TAPER:.2f} further out at the end, so the opening meets the rail "
                  "with room to spare.")


def fig_mated(n, rail, housing):
    d = Drawing((-15.0, 15.0, -7.3, 2.5), scale=30.0)
    d.outline(housing, fill="var(--mate)", stroke="var(--mate-edge)")
    d.outline(rail)
    d.leader((0, -n.depth - n.c / 2), (2.5, -5.9), f"floor gap {n.c:.2f}")
    d.leader((-10.5, -n.c / 2), (-10.5, 1.4), f"face gap {n.c:.2f}", anchor="middle")
    d.leader((7.0 + n.c * 0.58, -2.0), (11.5, 1.4), f"flank gap {n.c:.2f}", anchor="middle")
    d.text((0, 0.3), "rail (base_width 25)", colour="var(--edge)", weight="600")
    d.text((-9.0, -3.6), "housing", colour="var(--mate-edge)", weight="600")
    return figure(d, "the pair mated, wide support",
                  "The rail with base_width 25 (blue) in the housing (orange), built at the same "
                  "origin and sliced from the real solids.")


def fig_mated_default(n, rail, housing):
    d = Drawing((-15.0, 15.0, -7.3, 2.5), scale=30.0)
    d.outline(housing, fill="var(--mate)", stroke="var(--mate-edge)")
    d.outline(rail)
    d.leader((n.support / 2, -n.c / 2), (10.5, 1.4),
             f"edge of the support to the lip {n.c:.2f}", anchor="middle")
    d.text((0, 0.3), "rail (defaults)", colour="var(--edge)", weight="600")
    d.text((-9.0, -3.6), "housing", colour="var(--mate-edge)", weight="600")
    return figure(d, "the pair mated, defaults",
                  f"The default rail in the housing. At clearance {n.c:.2f} the support and the "
                  f"mouth are the same width, {n.support:.2f}, and {n.c:.2f} apart: the support "
                  "doesn't enter the mouth. The gaps are measured on the solids in section 9.")


# ------------------------------------------------------------------ the page

def verify(n):
    """Build everything, compare it with the working. Returns the rows and
    the loops to draw; stops if anything disagrees by more than 0.0005."""
    doc = App.newDocument("Rail15Spec")
    sheet = parameter_sheet(doc)

    def make(key, name, **kw):
        kw.setdefault("length", "20")
        return primlib.make(key, doc, name, sheet=sheet, **kw)

    rail = make("rail15", "Rail")
    wide = make("rail15", "RailWide", base_width="25")
    deep = make("rail15", "RailDeep", depth="6")
    shallow = make("rail15", "RailShallow", depth="2.5")
    offset = make("rail15", "RailOffset", printer_width_offset="0.8")
    offset_h = make("rail15_housing", "HousingOffset", printer_width_offset="0.8")
    offset_neg = make("rail15_housing", "HousingNeg", printer_width_offset="-0.3")
    housings = {c: make("rail15_housing", f"H{c.replace('.', '')}", clearance=c)
                for c in CLEARANCES}
    doc.recompute()
    taper_rail = make("rail15", "RailTaper", end_taper=str(TAPER))
    taper_wide = make("rail15", "RailTaperWide", end_taper=str(TAPER), base_width="25")
    taper_h = make("rail15_housing", "HousingTaper", end_taper=str(TAPER))
    taper_h10 = make("rail15_housing", "HousingTaper10", end_taper=str(TAPER), clearance="0.10")
    doc.recompute()
    housing = housings["0.20"]
    x = 10.0
    bad = []

    def row(what, design, measured, note=""):
        if abs(design - measured) > 0.0005:
            bad.append(f"{what}: {design} / {measured}")
        return (esc(what), f"{design:.3f}", f"{measured:.4f}", esc(note))

    alias = lambda name: float(sheet.get(name))  # noqa: E731
    rows = [
        row("Width, defaults", 15.0, rail.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("Width, base_width 25", 15.0, width_at(wide.Shape, -3.0), "level slice, 1.00 above the tip"),
        row("Width, depth 6", 15.0, deep.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("Width, depth 2.5", 15.0, shallow.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("Fixed on the sheet: width", 15.0, alias("Rail_width"), "Rail_width"),
        row("Fixed on the sheet: angle", 60.0, alias("Rail_angle"), "Rail_angle"),
        row("Fixed on the sheet: tip_radius", 1.0, alias("Rail_tip_radius"), "Rail_tip_radius"),
        row("Fixed on the sheet: root_radius", 0.2, alias("Rail_root_radius"), "Rail_root_radius"),
        row("Angle on the solid", 60.0, flank_angle(rail.Shape, x), "from the flank's end points"),
        row("Root radius on the solid", 0.2, radii(rail.Shape, x)[0], "smallest arc in the slice"),
        row("Root radius, arc length on the solid", 0.2 * math.radians(120), arc_length(rail.Shape, x, 0.2),
            "the full 120° turn, 0.20 x 120° in radians"),
        row("Root radius, arc length, base_width 25", 0.2 * math.radians(120), arc_length(wide.Shape, x, 0.2),
            "the same"),
        row("Support width, defaults", n.support, width_at(rail.Shape, 0.5), "level slice through the support"),
        row("Neck, defaults", n.neck, width_at(rail.Shape, -0.2), "level slice at the root radii's vertical tangent"),
        row("Tip radius on the solid", 1.0, radii(rail.Shape, x)[-1], "largest arc in the slice"),
        row("Depth plus base_depth, defaults", 5.0, rail.Shape.optimalBoundingBox().ZLength, "bounding box"),
        row("Depth plus base_depth, depth 6", 7.0, deep.Shape.optimalBoundingBox().ZLength, "bounding box"),
        row("Slot widest, clearance 0.20", n.slot_widest, slot_width(housing.Shape, -3.0),
            "15 + 2 x 0.20; level slice at the floor radii's vertical tangent"),
        row("Mouth, clearance 0.20", n.mouth, slot_width(housing.Shape, -n.c - 0.0001),
            "level slice just under the mating face"),
        row("Slot depth, mouth to floor", 4.0, -n.c - max(
            p.z for e in section_edges(housing.Shape, x) for p in e.discretize(20)
            if abs(p.y) < 3), "at the centre line"),
    ]
    for c, h in housings.items():
        over = rail.Shape.common(h.Shape).Volume + wide.Shape.common(h.Shape).Volume
        rows.append(row(f"Gap, clearance {c}, base_width 25", float(c),
                        wide.Shape.distToShape(h.Shape)[0], f"closest points; overlap {over:.3f} mm³"))
        rows.append(row(f"Gap, clearance {c}, base_width -1", float(c),
                        rail.Shape.distToShape(h.Shape)[0], "closest points on the solids"))
    rows += [
        row("end_taper 0.5: rail's width between the lead-ins", 15.0,
            taper_rail.Shape.optimalBoundingBox().YLength, "bounding box of the solid"),
        row("end_taper 0.5: rail's width at the very end", 14.0,
            y_span([p for p in end_points(taper_rail.Shape, 0.0) if p.z < -0.5]), "end face, the tapered part"),
        row("end_taper 0.5: rail's depth at the very end", 4.5,
            z_span(end_points(taper_rail.Shape, 0.0)), "end face, tip to support top: 3.5 + 1"),
        row("end_taper 0.5: tip radius at the very end", 0.5, end_radii(taper_rail.Shape, 0.0)[-1],
            "largest arc on the end face"),
        row("end_taper 0.5: root radius at the very end", 0.2, end_radii(taper_rail.Shape, 0.0)[0],
            "smallest arc on the end face"),
        row("end_taper 0.5: support width at the very end, unchanged", n.support,
            width_at(taper_rail.Shape, 0.5), "level slice through the support"),
        row("end_taper 0.5: gap in the housing", 0.2, taper_rail.Shape.distToShape(taper_h.Shape)[0],
            "closest points on the solids"),
        row("end_taper 0.5: gap, clearance 0.10, lip rounded", 0.1,
            taper_rail.Shape.distToShape(taper_h10.Shape)[0], "closest points on the solids"),
        row("end_taper 0.5: gap, base_width 25", 0.2, taper_wide.Shape.distToShape(taper_h.Shape)[0],
            "closest points on the solids"),
        row("end_taper 0.5: slot widest between the lead-ins", n.slot_widest,
            slot_width(taper_h.Shape, -3.0), "level slice, along the length"),
        row("end_taper 0.5: slot widest at the very end", n.slot_widest + 1.0,
            housing_end_width(taper_h.Shape), "end face"),
        row("Slide, rail into housing: worst overlap", 0.0, slide_overlap(taper_rail.Shape, taper_h.Shape),
            "20 positions along x, from clear of one end to clear of the other, mm³"),
        row("Offset 0.8: rail's width in the model", 15.8,
            offset.Shape.optimalBoundingBox().YLength, "15 + 0.8; bounding box"),
        row("Offset 0.8: depth plus base_depth, unchanged", 5.0,
            offset.Shape.optimalBoundingBox().ZLength, "bounding box"),
        row("Offset 0.8: angle, unchanged", 60.0, flank_angle(offset.Shape, x), "from the flank's end points"),
        row("Offset 0.8 on both parts: gap, unchanged", 0.2,
            offset.Shape.distToShape(offset_h.Shape)[0], "closest points on the solids"),
        row("Housing offset -0.3: slot widest", n.slot_widest - 0.3,
            slot_width(offset_neg.Shape, -3.0), "level slice"),
        row("Housing offset -0.3: block width, unchanged", 25.0,
            offset_neg.Shape.optimalBoundingBox().YLength, "bounding box"),
    ]
    if bad:
        raise SystemExit(f"the specification disagrees with the solids: {bad}")
    cuts = {"rail": loops_of(rail.Shape, x), "wide": loops_of(wide.Shape, x),
            "deep": loops_of(deep.Shape, x), "shallow": loops_of(shallow.Shape, x),
            "housing": loops_of(housing.Shape, x),
            "taper_rail": loops_of(taper_rail.Shape, x), "taper_slot": loops_of(taper_h.Shape, x),
            "taper_rail_end": loops_of(taper_rail.Shape, 0.0001),
            "taper_slot_end": loops_of(taper_h.Shape, 0.0001),
            "taper_side": [[(p.x, p.z) for p in w.discretize(Deflection=0.0005)]
                           for w in taper_rail.Shape.slice(App.Vector(0, 1, 0), 0.0)]}
    return rows, cuts


def build_page():
    n = Numbers()
    rows, cuts = verify(n)
    shallow, deep = Numbers(depth=2.5), Numbers(depth=6.0)

    def dim_wide(d):
        d.across(-12.5, 12.5, 1, 2.0, "base_width 25")
        d.down(0, 1, -12.5, -13.2, "")
        d.text((-12.5, 1.25), "base_depth 1", anchor="start")
        d.leader((n.root_hw + 0.1, -0.02), (9.5, -1.6), "root_radius 0.20")

    def dim_depth(m):
        def draw(d):
            d.across(-7.5, 7.5, m.r_tip - m.depth, -m.depth - 0.9, "width 15.00", weight="700")
            d.down(-m.depth, 0, -m.root_hw, -9.2, f"depth {m.depth:g}")
        return draw

    body = [
        "<h1>15 mm rail</h1>",
        '<p class="sub">Specification of <code>rail15</code> and <code>rail15_housing</code> · '
        '<a href="rail15.html">rail page</a> · <a href="rail15_housing.html">housing page</a> · '
        '<a href="../../index.html">all primitives</a></p>',
        '<p class="warn">Four <b>fixed '
        "parameters</b> define the shape. The rail has no tolerance, and its width is "
        "<b>15.00</b> whatever the variable parameters are. All sizes are in mm.</p>",

        "<h2>1. Parameters</h2>",
        "<h3>Fixed parameters</h3>",
        table(("", "name", "value", "what it is"), [
            ("1", "<code>width</code>", "15.00",
             "Outside width: between vertical tangents to the tip radii, what calipers read"),
            ("2", "<code>angle</code>", "60°", "Slope of the sides, flank to the tip face"),
            ("3", "<code>tip_radius</code>", "1.00", "The two tip corners"),
            ("4", "<code>root_radius</code>", "0.20", "The two root corners"),
        ], num_cols=(2,)),
        "<h3>Variable parameters of the rail</h3>",
        table(("name", "default", "what it does"), [
            ("<code>length</code>", "20.00", "Rail length, along x"),
            ("<code>depth</code>", "4.00", "Depth of the tapered part, root to tip"),
            ("<code>base_depth</code>", "1.00", "Depth of the support on the root. Must be more "
                                                "than 0: the root radius needs it"),
            ("<code>base_width</code>", "-1.00", f"Width of the support. -1: as wide as the root including its radius, "
                                                 f"{n.support:.2f} at depth 4"),
            ("<code>end_taper</code>", "0.00",
             "Option: lead-ins at both ends. 0: none. See section 6"),
            ("<code>printer_width_offset</code>", "0.00",
             "Added to the width in the model: see section 7"),
        ], num_cols=(1,)),
        '<p></p><code class="formula">primlib.make("rail15", doc, name, length=20, depth=4, '
        "base_depth=1, base_width=-1)\n"
        "# and optionally end_taper=0, printer_width_offset=0</code>",
        "<p>The sheet shows these ten values and nothing else.</p>",
        "<h3>Variable parameters of the matching part</h3>",
        table(("name", "default", "what it does"), [
            ("<code>clearance</code>", "0.20", "The gap between the printed rail and housing, "
                                               "normal to every face, per side"),
            ("<code>length</code>", "20.00", "Along x"),
            ("<code>depth</code>", "4.00", "Depth of the slot; must match the rail"),
            ("<code>block_width</code>", "25.00", "The block, across"),
            ("<code>block_depth</code>", "6.00", "The block, down from the mating face"),
            ("<code>end_taper</code>", "0.00", "Option: lead-ins at both ends of the slot. 0: none. "
                                               "See section 6"),
            ("<code>printer_width_offset</code>", "0.00", "Added to the slot's width in the model; "
                                                          "the housing's own value"),
        ], num_cols=(1,)),

        "<h2>2. The rail</h2>",
        fig_rail(n, cuts["rail"]),
        fig_root(n, cuts["rail"]),

        "<h2>3. Why the width is exactly 15.00</h2>",
        "<p>A radius tangent to the tip face and the flank has its centre <code>t</code> in from "
        "the sharp corner, along the tip face, set by half the 60° angle. Its vertical tangent is "
        "one radius outside its centre. So half the width is the sharp corner, less <code>t</code>, "
        "plus the radius. The primitive turns that round to get the sharp corner from 15:</p>",
        f"""<code class="formula">t      = tip_radius / tan(angle / 2)      = 1 / tan 30°             = {n.t_tip:.6f}
tip_hw = width / 2 + t - tip_radius       = 7.5 + {n.t_tip:.6f} - 1     = {n.tip_hw:.6f}

check, worked back from the sharp corner:
2 x (tip_hw - t + tip_radius) = 2 x ({n.tip_hw:.6f} - {n.t_tip:.6f} + 1) = {n.width_check:.6f}</code>""",
        "<p>Substituting, <code>t</code> and <code>tip_radius</code> cancel, leaving "
        "<code>width</code>. So it's exactly 15, and neither <code>depth</code> nor the root enters "
        "it. The primitive refuses to build if the check differs from 15 by a millionth of a mm, "
        "and the print test script measures the finished solid and stops if it isn't 15.000000.</p>",

        "<h2>4. The variable parameters, drawn</h2>",
        fig_variant(cuts["wide"], (-14.5, 14.5, -5.0, 3.2), 28.0,
                    "<b>base_width 25.</b> The root radii run into the support's underside, as at "
                    "the default, and the support carries on past them. It must be wider than "
                    "the root including its radius.", dim_wide),
        '<div class="row">',
        fig_variant(cuts["shallow"], (-10.5, 10.5, -4.1, 2.0), 19.0,
                    "<b>depth 2.5.</b> The width stays 15.00; the root gets wider.", dim_depth(shallow)),
        fig_variant(cuts["deep"], (-10.5, 10.5, -7.6, 2.0), 19.0,
                    "<b>depth 6.</b> The width stays 15.00; the root gets narrower.", dim_depth(deep)),
        "</div>",

        "<h2>5. The clearance and the matching part</h2>",
        f"<p><code>clearance</code> (default {n.c:.2f}) is the gap between the printed parts. It's "
        "normal to every face and per side, so a width across the slot grows by twice it. The "
        "slot is the rail grown by it. The tip's radius keeps its centre and grows to 1 + "
        "clearance. The mouth's lip keeps the root radius's centre, with radius 0.20 - clearance. "
        "That can't go below 0, so from 0.20 up the lip is a sharp corner.</p>",
        fig_clearance(n, cuts["wide"], cuts["housing"]),
        fig_zoom_tip(n, cuts["wide"], cuts["housing"]),
        fig_zoom_lip(n, cuts["wide"], cuts["housing"]),
        "<h3>The matching part</h3>",
        fig_housing(n, cuts["housing"]),
        "<h3>The two parts together</h3>",
        fig_mated_default(n, cuts["rail"], cuts["housing"]),
        fig_mated(n, cuts["wide"], cuts["housing"]),
        "<h3>The slot at other clearances, depth 4</h3>",
        table(("clearance", "slot, widest", "mouth, narrowest", "lip radius"),
              [(c, f"{m.slot_widest:.2f}", f"{m.mouth:.2f}", f"{m.lip:.2f}" if m.lip else "sharp")
               for c, m in ((c, Numbers(float(c))) for c in CLEARANCES)],
              num_cols=(0, 1, 2, 3)),

        "<h2>6. Tapered ends</h2>",
        "<p><code>end_taper</code> is an option on both parts, off by default: lead-ins, so the rail "
        "finds its way into the slot rather than catching on the end of it. It's the same size on "
        "both ends of a part. Over the last <code>end_taper</code> of the length, the rail's tapered "
        "part shrinks by <code>end_taper</code> normal to its faces, and the slot grows by it. The "
        "change is the same as the distance along x, so the lead-in is at 45°. The print test uses "
        f"{TAPER:.1f}.</p>",
        "<p>The rail's support doesn't change, nor does the housing's mating face. Between the "
        "lead-ins, both parts have exactly the profile shown above, so the width and the mouth are "
        "measured there. At the very end the rail's tip radius is 1 - <code>end_taper</code> and "
        "the slot's floor radius is 1 + clearance + <code>end_taper</code>, each concentric with "
        "the full radius, and the root radius and the lip stay as they are. So "
        "<code>end_taper</code> must be less than 1.</p>",
        fig_taper_side(n, cuts["taper_side"]),
        fig_taper_rail(n, cuts["taper_rail"], cuts["taper_rail_end"]),
        fig_taper_slot(n, cuts["taper_slot"], cuts["taper_slot_end"]),
        table(("at the very end, end_taper 0.5", "rail", "slot, clearance 0.20"), [
            ("Width", f"{15 - 2 * TAPER:.2f}, measured", f"{n.slot_widest + 2 * TAPER:.2f}, at its widest"),
            ("Depth of the profile", f"{n.depth - TAPER:.2f}", f"{n.depth + TAPER:.2f}"),
            ("Tip or floor radius", f"{n.r_tip - TAPER:.2f}", f"{n.r_tip + n.c + TAPER:.2f}"),
        ], num_cols=(1, 2)),

        "<h2>7. The printer width offset</h2>",
        "<p>This keeps the printer out of the fit. <code>clearance</code> is only ever the gap "
        "between the printed parts; whatever the printer does to a part's width is corrected "
        "separately, on that part. Every size in this document is the design size, what the print "
        "should measure.</p>",
        '<code class="formula">width in the model = design width + printer_width_offset</code>',
        "<p>Half goes to each side, across y only: each half of the section moves sideways, "
        "unchanged, so the depth, the angle and the radii stay exact, and only the flat tip face "
        "and flat floor get wider. Each part has its own value, because a printer needn't move a "
        "slot's walls as it moves a rail's. The block's outside doesn't change.</p>",
        f'<code class="formula">rail:    printer_width_offset = 15.00 - (width measured at 0)\n'
        f"housing: printer_width_offset = (design mouth, section 5) - (mouth measured at 0)\n\n"
        "examples, for illustration:\n"
        "rail measured 14.60    ->  offset  0.40,  model 15.40, should print 15.00\n"
        f"clearance {n.c:.2f}, mouth measured 13.00  ->  offset {n.mouth - 13.0:.2f},  model {2 * n.mouth - 13.0:.2f}, "
        f"should print {n.mouth:.2f}</code>",
        "<p>A negative offset is allowed. If the two offsets differ, the two models won't show the "
        "printed gap, and may even overlap as models. That's expected: it's the printed parts that "
        "have the clearance.</p>",

        "<h2>8. Printing and measuring the test part</h2>",
        "<p><code>rail15_print_test.stl</code> in the <code>claude</code> project: one rail "
        "(defaults, 30 long, no label) and five housings (25 x 6 x 15) at clearances 0.10, 0.20, "
        "0.30, 0.40 and 0.50, each with its clearance in hundredths standing 0.4 proud of its "
        f"mating face (\"10\" to \"50\"), all at offset 0 with end_taper {TAPER:.1f}. None needs "
        "supports. The rail has no "
        "label because raised text on its tip face would jam against the slot floor. Positions "
        "are measured up from the bed.</p>",
        table(("part", "measure", "design", "how"), [
            ("Rail", "<b>Width</b>", "<b>15.00</b>",
             "Calipers across the tip radii, 4.00 up, away from the lead-ins. Sets the rail's offset"),
            ("Rail", "Depth plus base_depth", "5.00", "Bed to tip face"),
            ("Rail", "Support width", f"{n.support:.2f}",
             "Across the support's sides, above the first layer"),
            ("Each housing", "<b>Mouth, narrowest</b>", "<b>see section 5</b>",
             "Inside jaws, at the mating face in the middle of the length (just below it at 0.10, "
             "whose lip is rounded), against the table for its clearance. Sets the housing's offset"),
            ("Each housing", "Block width", "25.00", "Across the block"),
            ("Each housing", "block_depth", "6.00", "Bed to mating face, away from the raised label"),
            ("Each housing", "Fit", "slides", "Slide the rail through, from each end; note where it catches, and any rattle"),
        ]),
        "<p></p><p>The slot's widest point can't be reached with calipers, so the slide is what "
        "tests it.</p>",

        "<h2>9. Verification</h2>",
        "<p>Each row compares the working above with a measurement of the actual solid, made when "
        "this page was generated. The script stops rather than write the page if any differ by "
        "more than 0.0005.</p>",
        table(("what", "design", "on the solid", "how"), rows, num_cols=(1, 2)),
    ]
    return page("15 mm rail specification", EXTRA_CSS + "".join(body))


if __name__ == "__main__" or (len(sys.argv) > 1 and sys.argv[1].endswith("make_rail15_spec.py")):
    path = os.path.join(ROOT, "primlib", "primitives", "rail15_spec.html")
    html_text = build_page()
    with open(path, "w") as fh:
        fh.write(html_text)
    print(f"wrote {path}")
    sys.stdout.flush()
    os._exit(0)
