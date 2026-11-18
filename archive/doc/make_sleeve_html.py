"""Generate doc/sleeve_spec.html -- sleeve specification (nominal + fit).

Every number and drawing is derived from PARAMS below, so editing a value
here and re-running keeps the text, tables and SVG consistent:

    python3 doc/make_sleeve_html.py

Same format as doc/pin.html, with one addition: the meridian area of
rotation is given as two separate paths -- the OUTER edge (the W-shaped
outer wall) and the INNER edge (the bore), which are revolved as one
closed wire by sleeve_revolved().
"""

import math
from pathlib import Path

OUT = Path(__file__).with_name("sleeve_spec.html")

# Chosen values (match sleeve.py / pin_sleeve.py)
H = 10.0        # h    sleeve / pin height (mm)
PD = 6.0        # pd   pin shaft diameter (mm)
RD = 10.0       # rd   pin retain (flare) diameter (mm)
KD = 13.0       # kd   sleeve outside diameter (mm)
TOL = 0.10      # tol  radial running clearance, pin -> bore (mm)

ANG = 45.0      # exterior end flanks are 45 degrees (fixed by the model)


# --------------------------------------------------------------------------
# Geometry (mirrors sleeve.py derived_geometry / profile_points)
# --------------------------------------------------------------------------
OUTER_RAD = KD / 2.0                 # 6.5
FLARE_RAD = RD / 2.0 + TOL           # 5.1
THROAT_RAD = PD / 2.0 + TOL          # 3.1
RIDGE = (FLARE_RAD + OUTER_RAD) / 2.0   # 5.8  (default a)
RIM_H = OUTER_RAD - RIDGE            # 0.7  (fl)
BORE_FLARE = (RD - PD) / 2.0         # 2.0  (c_b)
VALLEY_Z = RIDGE - THROAT_RAD        # 2.7  valley cone -> throat
WALL = OUTER_RAD - FLARE_RAD         # 1.4  (kt)
PIN_FLARE = RD + 2.0 * TOL           # 10.2 pin flare circle, buried in the valley


def num(v, places=4):
    s = f"{v:.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def f2(v):
    return f"{v:.2f}"


# Two separate meridian paths, both in the XZ half-plane (y = 0), z up.
# OUTER: valley apex -> bottom flank -> outer wall -> top flank -> top apex
OUTER_PATH = [
    ("bottom valley apex (r = a, z = 0)", RIDGE, 0.0),
    ("bottom 45&#176; flank &#8594; outer wall", OUTER_RAD, RIM_H),
    ("outer wall &#8594; top flank", OUTER_RAD, H - RIM_H),
    ("top flank &#8594; top apex (r = a, z = h)", RIDGE, H),
]
# INNER: top valley apex -> top valley cone -> throat -> bottom valley cone
INNER_PATH = [
    ("top valley apex (r = a, z = h)", RIDGE, H),
    ("top valley cone &#8594; throat", THROAT_RAD, H - VALLEY_Z),
    ("throat &#8594; bottom valley cone", THROAT_RAD, VALLEY_Z),
    ("bottom valley cone &#8594; bottom apex (r = a, z = 0)", RIDGE, 0.0),
]
# The closed wire sleeve_revolved() actually sketches (INNER reversed -> OUTER).
WIRE = [
    (RIDGE, 0.0),
    (OUTER_RAD, RIM_H),
    (OUTER_RAD, H - RIM_H),
    (RIDGE, H),
    (THROAT_RAD, H - VALLEY_Z),
    (THROAT_RAD, VALLEY_Z),
]


def path_d(pts):
    return "M " + " L ".join(f"{num(x)},{num(z)}" for x, z in pts) + " Z"


def nice(v):
    """Round to 3 dp so 0.7000000000000002 prints as 0.7."""
    return round(v, 3)


def poly_d(pts, s, ox, oz):
    return "M " + " L ".join(
        f"{num(ox + x * s, 2)},{num(oz - z * s, 2)}" for x, z in pts) + " Z"


CSS = """
:root{--ink:#1a1a24;--acc:#2b5b84;--bg:#fff;--soft:#f4f6f9;--mut:#5c6472;--line:#d9dee5}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 color:var(--ink);background:var(--soft);line-height:1.55}
main{max-width:1060px;margin:0 auto;background:var(--bg);padding:40px 52px 90px;
 box-shadow:0 0 24px rgba(0,0,0,.08)}
h1{font-size:1.9em;margin:.2em 0 .1em}
h2{font-size:1.45em;border-bottom:2px solid var(--line);padding-bottom:.25em;
 margin-top:1.7em;color:var(--acc)}
h3{font-size:1.13em;margin:1.3em 0 .2em;color:var(--acc)}
code{background:#eef1f5;border:1px solid var(--line);border-radius:4px;padding:0 .3em;
 font-size:.9em;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
pre{background:#eef1f5;border:1px solid var(--line);border-radius:6px;padding:14px 16px;
 overflow:auto;font-size:.82em;line-height:1.5;margin:.8em 0 1.4em}
pre code{background:none;border:0;padding:0;font-size:1em}
table{border-collapse:collapse;width:100%;margin:.6em 0 1.2em;font-size:.92em}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--soft)}
figure{margin:1.4em 0 2em;padding:14px;border:1px solid var(--line);border-radius:8px;
 background:#fff}
figure svg{width:100%;height:auto;display:block}
figcaption{font-size:.9em;color:var(--mut);margin-top:.55em;text-align:center}
.fig-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}
@media(max-width:860px){main{padding:22px 14px 60px}.fig-grid{grid-template-columns:1fr}}
.foot{margin-top:2.5em;padding-top:1em;border-top:1px solid var(--line);
 color:var(--mut);font-size:.85em}
hr.sheet{border:0;border-top:2px dashed var(--line);margin:3.5em -52px}
.legend{font-size:11px;fill:#5c6472}
.swatch{display:inline-block;width:1.6em;height:0;border-top:2px solid #1a1a24;
 vertical-align:middle;margin:0 .3em}
.swatch.ovr{border-color:#c0392b}
/* inline-SVG classes */
path.geo{fill:none;stroke:#1a1a1a;stroke-width:1.5;stroke-linejoin:round}
path.hidden{fill:none;stroke:#8a8a8a;stroke-width:1.1;stroke-dasharray:6 4}
path.ghost{fill:none;stroke:#b3bac3;stroke-width:1.1}
path.ovr{fill:none;stroke:#c0392b;stroke-width:1.7}
path.center{fill:none;stroke:#c0392b;stroke-width:1.1;stroke-dasharray:10 4 3 4}
path.dim{fill:none;stroke:#666;stroke-width:1.1}
path.ref{fill:none;stroke:#777;stroke-width:1;stroke-dasharray:2 3}
path.lead{fill:none;stroke:#777;stroke-width:1.1}
path.axis{fill:none;stroke:#9aa;stroke-width:1.1}
path.axisline{fill:none;stroke:#c0392b;stroke-width:1.1;stroke-dasharray:10 4 3 4}
path.area{fill:#eef4fa;stroke:#1a1a24;stroke-width:1.6;stroke-linejoin:round}
path.areaout{fill:#eef4fa;stroke:#1a1a24;stroke-width:1.7;stroke-linejoin:round}
path.areain{fill:#fff;stroke:#c0392b;stroke-width:1.5;stroke-linejoin:round}
circle.geo{fill:none;stroke:#1a1a1a;stroke-width:1.5}
circle.hidden{fill:none;stroke:#8a8a8a;stroke-width:1.1;stroke-dasharray:6 4}
circle.ghost{fill:none;stroke:#b3bac3;stroke-width:1.1}
circle.vtx{fill:#1a1a24}
circle.vtxin{fill:#c0392b}
text.title{font-size:19px;font-weight:bold;fill:#111}
text.subtitle{font-size:12px;fill:#555}
text.dimtxt{font-size:12px;fill:#555;text-anchor:middle}
text.callout{font-size:11.5px;fill:#444}
text.note{font-size:11.5px;fill:#666}
text.plbl{font-size:12.5px;font-weight:bold;fill:#0b6fa4}
text.plblin{font-size:12.5px;font-weight:bold;fill:#c0392b}
text.axislbl{font-size:13px;font-style:italic;fill:#666}
"""


def front_svg():
    S, cx, z0 = 30.0, 300.0, 400.0

    def X(x):
        return cx + x * S

    def Y(z):
        return z0 - z * S

    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 560" width="700" '
      'height="560" role="img" aria-label="Sleeve front view">')
    a('<defs><marker id="arw" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
      'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker>'
      '<marker id="arwR" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
      'markerHeight="7" orient="auto-start-reverse">'
      '<path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker></defs>')
    a('<text class="title" x="20" y="30">SLEEVE &#8212; FRONT VIEW</text>')
    a(f'<text class="subtitle" x="20" y="52">elevation &#183; solid of revolution '
      f'&#183; {ANG:.0f}&#176; W / inverted-W end faces &#183; kd = {f2(KD)} mm '
      f'&#183; tol = {f2(TOL)} mm &#183; mm</text>')
    a('<path class="ghost" d="M556,70 L586,70"/>')
    a('<text class="legend" x="592" y="74">pin (nominal)</text>')
    a('<path class="ovr" d="M556,88 L586,88"/>')
    a('<text class="legend" x="592" y="92">sleeve</text>')

    a(f'<path class="center" d="M{cx},{num(Y(H + 1.2))} L{cx},{num(Y(-1.2))}"/>')
    # nominal pin (grey hint, same scale)
    pin_pts = [(0, 0), (RD / 2, 0), (PD / 2, BORE_FLARE),
               (PD / 2, H - BORE_FLARE), (RD / 2, H), (0, H)]
    a(f'<path class="ghost" d="{poly_d(pin_pts, S, cx, z0)}"/>')
    # sleeve outline
    a(f'<path class="ovr" d="{poly_d(WIRE, S, cx, z0)}"/>')
    # bore (hidden): valley cones + throat cylinder
    a(f'<path class="hidden" d="M{num(X(RIDGE))},{num(Y(0))} '
      f'L{num(X(THROAT_RAD))},{num(Y(VALLEY_Z))} '
      f'L{num(X(THROAT_RAD))},{num(Y(H - VALLEY_Z))} '
      f'L{num(X(RIDGE))},{num(Y(H))}"/>')
    a(f'<path class="hidden" d="M{num(X(-RIDGE))},{num(Y(0))} '
      f'L{num(X(-THROAT_RAD))},{num(Y(VALLEY_Z))} '
      f'L{num(X(-THROAT_RAD))},{num(Y(H - VALLEY_Z))} '
      f'L{num(X(-RIDGE))},{num(Y(H))}"/>')

    # overall height (left)
    a(f'<path class="ref" d="M{num(X(-OUTER_RAD))},{num(Y(0))} L60,{num(Y(0))}"/>')
    a(f'<path class="ref" d="M{num(X(-OUTER_RAD))},{num(Y(H))} L60,{num(Y(H))}"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M70,{num(Y(0))} L70,{num(Y(H))}"/>')
    a(f'<text class="dimtxt" x="64" y="{num((Y(0) + Y(H)) / 2)}" '
      f'transform="rotate(-90 64 {num((Y(0) + Y(H)) / 2)})">h = {num(H)}</text>')

    # outside diameter (bottom)
    a(f'<path class="ref" d="M{num(X(OUTER_RAD))},{num(Y(0))} '
      f'L{num(X(OUTER_RAD))},510"/>')
    a(f'<path class="ref" d="M{num(X(-OUTER_RAD))},{num(Y(0))} '
      f'L{num(X(-OUTER_RAD))},510"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(X(-OUTER_RAD))},502 L{num(X(OUTER_RAD))},502"/>')
    a(f'<text class="dimtxt" x="{num(cx)}" y="497">&#216;{num(KD,1)} &#8212; kd</text>')

    # ridge / valley ring radius (bottom, right of centre)
    a(f'<path class="ref" d="M{num(X(RIDGE))},{num(Y(0))} L{num(X(RIDGE))},542"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(cx)},534 L{num(X(RIDGE))},534"/>')
    a(f'<text class="dimtxt" x="{num((cx + X(RIDGE)) / 2)}" y="529">'
      f'a = {num(RIDGE,1)}</text>')

    # wall thickness (top)
    a(f'<path class="ref" d="M{num(X(FLARE_RAD))},{num(Y(H))} '
      f'L{num(X(FLARE_RAD))},100"/>')
    a(f'<path class="ref" d="M{num(X(OUTER_RAD))},{num(Y(H))} '
      f'L{num(X(OUTER_RAD))},100"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(X(FLARE_RAD))},108 L{num(X(OUTER_RAD))},108"/>')
    a(f'<text class="dimtxt" x="{num((X(FLARE_RAD) + X(OUTER_RAD)) / 2)}" y="103">'
      f'kt = {num(WALL,1)}</text>')

    # 45 degree flank callouts
    a(f'<path class="lead" d="M{num(X(OUTER_RAD))},{num(Y(RIM_H))} L560,130"/>')
    a(f'<text class="callout" x="564" y="134">fl = {num(RIM_H,1)} &#8212; '
      f'{ANG:.0f}&#176; end flanks</text>')
    a(f'<path class="lead" d="M{num(X(THROAT_RAD))},{num(Y(VALLEY_Z))} L560,300"/>')
    a(f'<text class="callout" x="556" y="304">bore throat '
      f'&#216;{f2(2*THROAT_RAD)}</text>')
    a(f'<path class="lead" d="M{num(X(RIDGE))},{num(Y(0))} L560,470"/>')
    a(f'<text class="callout" x="564" y="474">valley ring r = a (z = 0)</text>')
    a(f'<path class="lead" d="M{num(X(RIDGE))},{num(Y(H))} L516,170"/>')
    a(f'<text class="callout" x="520" y="174">ridge ring r = a (z = h)</text>')
    a(f'<text class="note" x="20" y="550">sleeve (black) rides the pin (grey); '
      f'bore (dashed) = valley cones + throat &#183; stacked sleeves kiss on the '
      f'ridge ring</text>')
    a('</svg>')
    return "\n".join(out)


def top_svg():
    S, cx, cy = 30.0, 340.0, 230.0
    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 470" width="700" '
      'height="470" role="img" aria-label="Sleeve top view">')
    a(f'<circle class="ovr" cx="{cx}" cy="{cy}" r="{num(OUTER_RAD*S,2)}"/>')
    a(f'<circle class="geo" cx="{cx}" cy="{cy}" r="{num(RIDGE*S,2)}"/>')
    a(f'<circle class="hidden" cx="{cx}" cy="{cy}" r="{num(THROAT_RAD*S,2)}"/>')
    a(f'<circle class="ghost" cx="{cx}" cy="{cy}" r="{num(RD/2*S,2)}"/>')
    a(f'<path class="center" d="M{cx-200},{cy} L{cx+200},{cy}"/>')
    a(f'<path class="center" d="M{cx},{cy-200} L{cx},{cy+200}"/>')

    def lead(r, deg, tx, ty, label):
        px = cx + r * S * math.cos(math.radians(deg))
        py = cy + r * S * math.sin(math.radians(deg))
        a(f'<path class="lead" d="M{num(px)},{num(py)} L{tx},{num(ty)}"/>')
        a(f'<text class="callout" x="{tx+4}" y="{num(ty+4)}">{label}</text>')

    lead(OUTER_RAD, -50, 560, 90, f'&#216;{num(KD,1)} &#8212; kd (outer)')
    lead(RIDGE, -30, 556, 130, f'&#216;{num(2*RIDGE,2)} &#8212; ridge (2a)')
    lead(THROAT_RAD, 35, 560, 350, f'&#216;{f2(2*THROAT_RAD)} &#8212; throat (pd + 2&#183;tol)')
    lead(RD/2, 90, 560, 395, f'&#216;{num(RD,1)} &#8212; pin flare (grey)')
    a(f'<text class="note" x="20" y="452">outer, ridge / bore-mouth and pin flare '
      f'circles visible &#183; throat circle hidden</text>')
    a('</svg>')
    return "\n".join(out)


def profile_svg():
    """Meridian diagram: outer edge (black) and inner edge (red) as two paths."""
    S, ox, oz = 30.0, 90.0, 400.0
    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 470" width="400" '
      'height="470" role="img" aria-label="Sleeve meridian: outer and inner edge">')
    max_x, max_z = OUTER_RAD * S, H * S
    a(f'<path class="axis" d="M{ox},{oz} L{num(ox+max_x+46)},{oz}"/>')
    a(f'<path class="axis" d="M{ox},{oz} L{ox},{num(oz-max_z-38)}"/>')
    a(f'<text class="axislbl" x="{num(ox+max_x+52)}" y="{num(oz+4)}">x</text>')
    a(f'<text class="axislbl" x="{num(ox-26)}" y="{num(oz-max_z-44)}">z</text>')
    # outer body between the two edges (to scale), then the edges themselves
    a(f'<path class="area" d="{poly_d(WIRE, S, ox, oz)}"/>')
    a(f'<path class="areaout" d="{poly_d([(x,z) for _,x,z in OUTER_PATH], S, ox, oz)}"/>')
    a(f'<path class="areain" d="{poly_d([(x,z) for _,x,z in INNER_PATH], S, ox, oz)}"/>')
    for i, (_, x, z) in enumerate(OUTER_PATH):
        a(f'<circle class="vtx" cx="{num(ox+x*S)}" cy="{num(oz-z*S)}" r="2.8"/>')
    for i, (_, x, z) in enumerate(INNER_PATH):
        a(f'<circle class="vtxin" cx="{num(ox+x*S)}" cy="{num(oz-z*S)}" r="2.8"/>')
    # bigger labels, offset to avoid the outline
    for txt, x, z, dx, dy, cls in (
            ("P0", RIDGE, 0.0, -34, 18, "plbl"),
            ("P1", OUTER_RAD, RIM_H, 8, 20, "plbl"),
            ("P2", OUTER_RAD, H - RIM_H, 8, -10, "plbl"),
            ("P3", RIDGE, H, -34, -10, "plbl"),
            ("M3", RIDGE, H, 22, 20, "plblin"),
            ("M4", THROAT_RAD, H - VALLEY_Z, 22, 12, "plblin"),
            ("M5", THROAT_RAD, VALLEY_Z, 22, -8, "plblin"),
            ("M0", RIDGE, 0.0, 22, -10, "plblin")):
        a(f'<text class="{cls}" x="{num(ox+x*S+dx)}" y="{num(oz-z*S+dy)}">{txt}</text>')
    a('</svg>')
    return "\n".join(out)


def fit_svg():
    """Meridian fit section: sleeve wall + nominal pin."""
    S, cx, z0 = 30.0, 330.0, 430.0

    def X(x):
        return cx + x * S

    def Y(z):
        return z0 - z * S

    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 560" width="700" '
      'height="560" role="img" aria-label="Sleeve fit section">')
    a('<defs><marker id="arw" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
      'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker>'
      '<marker id="arwR" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
      'markerHeight="7" orient="auto-start-reverse">'
      '<path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker></defs>')
    a('<text class="title" x="20" y="30">SLEEVE ON THE PIN &#8212; FIT SECTION</text>')
    a(f'<text class="subtitle" x="20" y="52">meridian section &#183; sleeve (black) '
      f'+ retained pin (grey) &#183; tol = {f2(TOL)} mm radial &#183; mm</text>')
    a('<path class="ghost" d="M556,70 L586,70"/>')
    a('<text class="legend" x="592" y="74">retained pin</text>')
    a('<path class="ovr" d="M556,88 L586,88"/>')
    a('<text class="legend" x="592" y="92">sleeve</text>')
    a(f'<path class="center" d="M{cx},{num(Y(H+1.2))} L{cx},{num(Y(-1.2))}"/>')
    pin_pts = [(0, 0), (RD / 2, 0), (PD / 2, BORE_FLARE),
               (PD / 2, H - BORE_FLARE), (RD / 2, H), (0, H)]
    a(f'<path class="ghost" d="{poly_d(pin_pts, S, cx, z0)}"/>')
    a(f'<path class="ovr" d="{poly_d(WIRE, S, cx, z0)}"/>')
    # wall hatched by two tone bands: keep it simple, show the sections
    a(f'<path class="hidden" d="M{num(X(RIDGE))},{num(Y(0))} '
      f'L{num(X(THROAT_RAD))},{num(Y(VALLEY_Z))} '
      f'L{num(X(THROAT_RAD))},{num(Y(H-VALLEY_Z))} '
      f'L{num(X(RIDGE))},{num(Y(H))}"/>')
    a(f'<path class="ref" d="M{num(X(-OUTER_RAD))},{num(Y(0))} L60,{num(Y(0))}"/>')
    a(f'<path class="ref" d="M{num(X(-OUTER_RAD))},{num(Y(H))} L60,{num(Y(H))}"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M70,{num(Y(0))} L70,{num(Y(H))}"/>')
    a(f'<text class="dimtxt" x="64" y="{num((Y(0)+Y(H))/2)}" '
      f'transform="rotate(-90 64 {num((Y(0)+Y(H))/2)})">h = {num(H)}</text>')
    a(f'<path class="ref" d="M{num(X(THROAT_RAD))},{num(Y(VALLEY_Z))} '
      f'L{num(X(THROAT_RAD))},520"/>')
    a(f'<path class="ref" d="M{num(X(-THROAT_RAD))},{num(Y(VALLEY_Z))} '
      f'L{num(X(-THROAT_RAD))},520"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(X(-THROAT_RAD))},512 L{num(X(THROAT_RAD))},512"/>')
    a(f'<text class="dimtxt" x="{num(cx)}" y="507">&#216;{f2(2*THROAT_RAD)} '
      f'&#8212; throat (pd + 2&#183;tol)</text>')
    a(f'<path class="lead" d="M{num(X(RIDGE))},{num(Y(H))} L560,140"/>')
    a(f'<text class="callout" x="564" y="144">ridge ring &#216;{num(2*RIDGE,2)} (2a)</text>')
    a(f'<path class="lead" d="M{num(X(OUTER_RAD))},{num(Y(H/2))} L560,300"/>')
    a(f'<text class="callout" x="564" y="304">kt = {num(WALL,1)} &#8212; wall over '
      f'rd/2</text>')
    a(f'<path class="lead" d="M{num(X(THROAT_RAD))},{num(Y(VALLEY_Z))} L556,420"/>')
    a(f'<text class="callout" x="556" y="424">tol = {f2(TOL)} &#8212; '
      f'pin&#8596;bore</text>')
    a(f'<path class="lead" d="M{num(X(RD/2))},{num(Y(0))} L556,205"/>')
    a(f'<text class="callout" x="400" y="222">pin flare &#216;{num(PIN_FLARE,1)} '
      f'rides in the valley</text>')
    a(f'<text class="note" x="20" y="548">bore = valley cones + toleranced throat '
      f'&#183; pin flares ride free in the valleys &#183; retention is flare vs '
      f'throat</text>')
    a('</svg>')
    return "\n".join(out)


def row(*cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def eq(s):
    return f"<code>{s}</code>"


def edge_rows(items, cls):
    return "".join(
        row(f'<span style="color:{"#c0392b" if cls == "in" else "#0b6fa4"}">'
            f'{"M" if cls == "in" else "P"}{i}</span>', eq(f"{x:g}"),
            eq(f"{z:g}"), note)
        for i, (note, x, z) in enumerate(items))


html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sleeve &#8212; Specification</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Sleeve</h1>
<p>
The sleeve is the hollow barrel that rides a <b>retained pin</b>. Its exterior
is a cylinder capped by {ANG:.0f}&#176; cone flanks meeting at a sharp
<b>ridge ring</b>; its bore is the retained pin grown by a running clearance.
Two stacked sleeves touch only along the ridge ring, so a column closes
cleanly. It is a <b>solid of revolution</b>, so an elevation, a plan and a fit
section describe it fully. All numbers below are generated from the chosen set
in <code>doc/make_sleeve_html.py</code>.
</p>

<h2>Parameters</h2>
<table>
<tr><th>symbol</th><th>name</th><th>value</th><th>note</th></tr>
{row(eq("pd"), "pin shaft diameter (" + eq("diam") + ")", f"{PD:.1f}&nbsp;mm", "the shaft of the pin the sleeve rides")}
{row(eq("rd"), "pin retain diameter (" + eq("diam_end") + ")", f"{RD:.1f}&nbsp;mm", "the widest part of the pin")}
{row(eq("h"), "sleeve height (" + eq("height") + ")", f"{H:.1f}&nbsp;mm", "one pin segment, " + eq("z = 0 .. h"))}
{row(eq("kd"), "sleeve outside diameter (" + eq("diam_outer") + ")", f"{KD:.1f}&nbsp;mm", "sets " + eq("outer_rad = kd/2") + "; the wall is derived, not a parameter")}
{row(eq("tol"), "running clearance (" + eq("tolerance") + ")", f"{TOL:.2f}&nbsp;mm", "bore minus pin, radial, on every face")}
{row(eq("a"), "contact ring radius (" + eq("ridge_radius") + ")", f"{RIDGE:.1f}&nbsp;mm", "defaults to " + eq("(flare_rad + outer_rad)/2"))}
</table>

<h3>Derived geometry</h3>
<table>
<tr><th>symbol</th><th>meaning</th><th>expression</th><th>value</th></tr>
{row(eq("outer_rad"), "sleeve outside radius", eq("kd/2"), f"{f2(OUTER_RAD)}&nbsp;mm")}
{row(eq("flare_rad"), "bore radius at the end faces", eq("rd/2 + tol"), f"{f2(FLARE_RAD)}&nbsp;mm")}
{row(eq("throat_rad"), "bore radius at the waist", eq("pd/2 + tol"), f"{f2(THROAT_RAD)}&nbsp;mm")}
{row(eq("a"), "contact ring radius (default)", eq("(flare_rad + outer_rad)/2"), f"{f2(RIDGE)}&nbsp;mm")}
{row(eq("fl"), "45&#176; end-flank (rim) height", eq("outer_rad &#8722; a"), f"{f2(RIM_H)}&nbsp;mm")}
{row(eq("c_b"), "bore cone height (end face &#8594; waist)", eq("(rd &#8722; pd)/2"), f"{f2(BORE_FLARE)}&nbsp;mm")}
{row(eq("valley_z"), "valley cone &#8594; throat height", eq("a &#8722; throat_rad"), f"{f2(VALLEY_Z)}&nbsp;mm")}
</table>
<p>
The wall is derived, not a parameter:
<code>kt = kd/2 &#8722; (rd/2 + tol) = {f2(WALL)}&nbsp;mm</code>. Note
<code>2a = {f2(2*RIDGE)}&nbsp;mm &gt; h = {num(H)}&nbsp;mm</code>: the two
valley cones overlap through the middle of the part, which is why the bore
flanks read off the cut tools near the ends, not the pin void.
</p>

<h2>Views</h2>
<figure>
{front_svg()}
<figcaption>Front view (elevation) &#183; the W bottom face, the inverted-W top
face and the cylindrical wall; bore dashed.</figcaption>
</figure>

<figure>
{top_svg()}
<figcaption>Top view (plan) &#183; looking down the pin axis.</figcaption>
</figure>

<h2>Area of rotation</h2>
<p>
The sleeve is the region between two meridian paths, revolved about the
<i>z</i> axis. Both lie in the XZ half-plane (<code>y = 0</code>): <i>x</i> is
the distance from the axis, <i>z</i> the height. Nothing touches the axis, so
the revolved solid is hollow.
</p>
<div class="fig-grid">
<figure>
{profile_svg()}
<figcaption>Meridian: <b>outer edge</b> (black) and <b>inner edge</b> (red),
both revolved as one closed wire.</figcaption>
</figure>
<div>
<table>
<tr><th>edge</th><th>path</th><th>closes</th></tr>
{row("<b>outer</b> (black)", "P0 &#8594; P1 &#8594; P2 &#8594; P3", "no &#8212; pairs with the inner edge")}
{row("<b>inner</b> (red)", "M3 &#8594; M4 &#8594; M5 &#8594; M0", "no &#8212; pairs with the outer edge")}
</table>
<p>
<code>sleeve_revolved()</code> sketches the closed wire
<code>P0&#8594;P1&#8594;P2&#8594;P3&#8594;M4&#8594;M5&#8594;P0</code>
(M3 is P3 and M0 is P0), so the two paths share their end points.
</p>
</div>
</div>

<h3>Outer edge &#8212; the W-shaped wall</h3>
<p>
with <code>fl = outer_rad &#8722; a</code>:
</p>
<table>
<tr><th>point</th><th>x</th><th>z</th><th>feature</th></tr>
{edge_rows(OUTER_PATH, "out")}
</table>
<p>Path in <code>x,z</code>:</p>
<pre><code>{path_d([(x, z) for _, x, z in OUTER_PATH])}</code></pre>

<h3>Inner edge &#8212; the bore</h3>
<p>
with <code>valley_z = a &#8722; throat_rad</code>; the two 45&#176; valley cones
<code>r = a &#8722; z</code> (bottom) and <code>r = a &#8722; (h &#8722; z)</code>
(top) opening into the throat cylinder:
</p>
<table>
<tr><th>point</th><th>x</th><th>z</th><th>feature</th></tr>
{edge_rows(INNER_PATH, "in")}
</table>
<p>Path in <code>x,z</code>:</p>
<pre><code>{path_d([(x, z) for _, x, z in INNER_PATH])}</code></pre>

<h3>The closed revolve wire</h3>
<p>Path in <code>x,z</code> (as sketched):</p>
<pre><code>{path_d(WIRE)}</code></pre>

<h2>Clearance and retention</h2>
<table>
<tr><th>feature</th><th>expression</th><th>value</th><th>note</th></tr>
{row("bore throat &#216;", eq("pd + 2&#183;tol"), f"{f2(2*THROAT_RAD)}&nbsp;mm", "the pin's flare cannot pass this")}
{row("bore mouth &#216;", eq("2a"), f"{f2(2*RIDGE)}&nbsp;mm", "the valley ring &#8212; the same circle as the ridge")}
{row("radial clearance", eq("tol"), f"{TOL:.2f}&nbsp;mm", "pin &#8596; bore, at the throat")}
{row("valley/flank gap", eq("fl = outer_rad &#8722; a"), f"{f2(RIM_H)}&nbsp;mm", "pin flares ride free in the valleys")}
{row("pin flare &#216;", eq("rd + 2&#183;tol"), f"{f2(PIN_FLARE)}&nbsp;mm", "widest part of the pin, buried in the valleys")}
{row("wall thickness", eq("outer_rad &#8722; (rd/2 + tol)"), f"{f2(WALL)}&nbsp;mm", "derived, not a parameter")}
</table>

<h2>Fit section</h2>
<figure>
{fit_svg()}
<figcaption>Meridian section &#183; sleeve (black) around the nominal retained
pin (grey). Only the throat actually meets the bore wall.</figcaption>
</figure>

<h2>Module</h2>
<p>
The part is built by <code>sleeve()</code> in <code>sleeve.py</code>, which
imports <code>pin_retained()</code> from the same library to cut the bore.
</p>
<pre><code>def sleeve(doc, name, height, diam, diam_end,
           diam_outer=13.0, tolerance=0.1, ridge_radius=None):

from sleeve import sleeve

slv = sleeve(doc, "Sleeve", height={H:.1f}, diam={PD:.1f}, diam_end={RD:.1f},
             diam_outer={KD:.1f}, tolerance={TOL:.2f})</code></pre>
<p>
The solid-of-revolution route mirrors the pin's:
<code>profile_points()</code> returns the six wire vertices,
<code>profile_sketch()</code> builds the sketch and
<code>sleeve_revolved()</code> revolves it. The internal void is exactly
<code>pin_retained(doc, ..., h, pd + 2&#183;tol, rd + 2&#183;tol)</code>.
</p>

<p class="foot">
Values: <code>pd = {PD:.1f}</code>, <code>rd = {RD:.1f}</code>,
<code>h = {H:.1f}</code>, <code>kd = {KD:.1f}</code>,
<code>tol = {TOL:.2f}</code>. Generated by
<code>doc/make_sleeve_html.py</code>; regenerate after changing a parameter.
</p>
</main>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({len(html)} bytes)")
