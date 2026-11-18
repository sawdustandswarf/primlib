"""Generate doc/pin.html -- retained pin specification (nominal + clearance).

The drawings and every number in the page are derived from PARAMS below, so
editing a value here and re-running keeps text, tables and SVG consistent:

    python3 doc/make_pin_html.py
"""

import math
from pathlib import Path

# Chosen nominal values (match pin_retained.py / pin_sleeve.py)
H = 10.0        # h    overall pin height (mm)
PD = 6.0        # pd   shaft diameter (mm)
RD = 10.0       # rd   retain (flare) diameter (mm)
ANG = 45.0      # p_ang flare flank angle (deg)
CLR = 0.10      # c    clearance, normal to every face (mm)

OUT = Path(__file__).with_name("pin.html")


def num(v, places=3):
    """Trim trailing zeros from a fixed-point number."""
    s = f"{v:.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def grow(h, pd, rd, ang, c):
    """Clearance-grown pin dimensions (same formulas as pin_retained.py)."""
    half = math.radians(ang / 2.0)
    hp = h + 2.0 * c
    pdp = pd + 2.0 * c
    rdp = rd + 2.0 * c / math.tan(half)
    cone = (rdp / 2.0 - pdp / 2.0) * math.tan(math.radians(ang))
    return hp, pdp, rdp, cone


def profile(hp, pdp, rdp, cone):
    """Six (x, z) profile vertices, y = 0."""
    return [
        (0.0, 0.0),
        (rdp / 2.0, 0.0),
        (pdp / 2.0, cone),
        (pdp / 2.0, hp - cone),
        (rdp / 2.0, hp),
        (0.0, hp),
    ]


def path_d(pts):
    return "M " + " L ".join(f"{num(x, 4)},{num(z, 4)}" for x, z in pts) + " Z"


def poly_d(pts, sx, sz, ox, oz):
    """Polygon path in SVG pixels; z grows upwards."""
    return "M " + " L ".join(
        f"{num(ox + x * sx, 2)},{num(oz - z * sz, 2)}" for x, z in pts) + " Z"


NOM_H, NOM_PD, NOM_RD, NOM_CONE = grow(H, PD, RD, ANG, 0.0)
CLR_H, CLR_PD, CLR_RD, CLR_CONE = grow(H, PD, RD, ANG, CLR)
NOM_PTS = profile(NOM_H, NOM_PD, NOM_RD, NOM_CONE)
CLR_PTS = profile(CLR_H, CLR_PD, CLR_RD, CLR_CONE)
SHAFT_LEN = NOM_H - 2.0 * NOM_CONE
APEX = (NOM_RD / 2.0) * math.tan(math.radians(ANG))
COT_HALF = 1.0 / math.tan(math.radians(ANG / 2.0))
RIM_GROWTH = 2.0 * CLR * COT_HALF
JUNCTION_SHIFT = CLR * math.tan(math.radians(45.0 - ANG / 2.0))


# --------------------------------------------------------------------------
# Front view (elevation): grey nominal pin + red clearance envelope
# --------------------------------------------------------------------------
def front_svg():
    S, cx, z0 = 30.0, 300.0, 480.0
    nom = [(x, z) for x, z in NOM_PTS]
    clr = [(x, z - CLR) for x, z in CLR_PTS]  # centred on the nominal pin

    def y(z):
        return z0 - z * S

    def X(x):
        return cx + x * S

    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 600" '
      'width="700" height="600" role="img" aria-label="Retained pin front view, '
      'nominal and clearance envelope">')
    a('<defs><marker id="arw" viewBox="0 0 10 10" refX="10" refY="5" '
      'markerWidth="7" markerHeight="7" orient="auto">'
      '<path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker>'
      '<marker id="arwR" viewBox="0 0 10 10" refX="10" refY="5" '
      'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
      '<path d="M0,0 L10,5 L0,10 z" fill="#666"/></marker></defs>')
    a('<text class="title" x="20" y="30">RETAINED PIN &#8212; FRONT VIEW</text>')
    a(f'<text class="subtitle" x="20" y="52">nominal (grey) + clearance '
      f'envelope (red) &#183; every face +c along its normal &#183; '
      f'c = {CLR:.2f} mm &#183; p_ang = {num(ANG)}&#176; &#183; mm</text>')
    # legend
    a('<path class="ghost" d="M540,74 L570,74"/>')
    a('<text class="legend" x="576" y="78">nominal</text>')
    a('<path class="ovr" d="M540,92 L570,92"/>')
    a('<text class="legend" x="576" y="96">envelope</text>')

    a(f'<path class="center" d="M{cx},{num(y(NOM_H + 1.0))} L{cx},{num(y(-1.0))}"/>')
    # nominal pin (grey ghost)
    a(f'<path class="ghost" d="{poly_d(nom, S, S, cx, z0)}"/>')
    a(f'<path class="ghost" d="M{num(X(NOM_PD / 2))},{num(y(NOM_CONE))} '
      f'L{num(X(-NOM_PD / 2))},{num(y(NOM_CONE))}"/>')
    a(f'<path class="ghost" d="M{num(X(NOM_PD / 2))},{num(y(NOM_H - NOM_CONE))} '
      f'L{num(X(-NOM_PD / 2))},{num(y(NOM_H - NOM_CONE))}"/>')
    # clearance envelope (red)
    a(f'<path class="ovr" d="{poly_d(clr, S, S, cx, z0)}"/>')
    a(f'<path class="ovrj" d="M{num(X(CLR_PD / 2))},{num(y(CLR_CONE - CLR))} '
      f'L{num(X(-CLR_PD / 2))},{num(y(CLR_CONE - CLR))}"/>')
    a(f'<path class="ovrj" d="M{num(X(CLR_PD / 2))},'
      f'{num(y(CLR_H - CLR_CONE - CLR))} '
      f'L{num(X(-CLR_PD / 2))},{num(y(CLR_H - CLR_CONE - CLR))}"/>')

    # overall height h + 2c (left); envelope is centred, so use z = -c .. h+c
    rim = X(CLR_RD / 2.0)
    xl = X(-CLR_RD / 2.0)
    zb, zt = y(-CLR), y(CLR_H - CLR)
    a(f'<path class="ref" d="M{num(xl)},{num(zb)} L60,{num(zb)}"/>')
    a(f'<path class="ref" d="M{num(xl)},{num(zt)} L60,{num(zt)}"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M70,{num(zb)} L70,{num(zt)}"/>')
    a(f'<text class="dimtxt" x="64" y="{num((zb + zt) / 2)}" '
      f'transform="rotate(-90 64 {num((zb + zt) / 2)})">'
      f'h+2c = {num(CLR_H, 2)}</text>')

    # shaft diameter pd + 2c (bottom)
    a(f'<path class="ref" d="M{num(X(CLR_PD / 2))},{num(zb)} '
      f'L{num(X(CLR_PD / 2))},540"/>')
    a(f'<path class="ref" d="M{num(X(-CLR_PD / 2))},{num(zb)} '
      f'L{num(X(-CLR_PD / 2))},540"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(X(-CLR_PD / 2))},532 L{num(X(CLR_PD / 2))},532"/>')
    a(f'<text class="dimtxt" x="{num(cx)}" y="527">&#216;{CLR_PD:.2f} '
      f'&#8212; pd+2c</text>')

    # retain diameter rd + 2c cot(p/2) (bottom)
    a(f'<path class="ref" d="M{num(X(CLR_RD / 2))},{num(zb)} '
      f'L{num(X(CLR_RD / 2))},572"/>')
    a(f'<path class="ref" d="M{num(X(-CLR_RD / 2))},{num(zb)} '
      f'L{num(X(-CLR_RD / 2))},572"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(X(-CLR_RD / 2))},564 L{num(X(CLR_RD / 2))},564"/>')
    a(f'<text class="dimtxt" x="{num(cx)}" y="559">&#216;{CLR_RD:.2f} '
      f'&#8212; rd+2c&#183;cot(p/2)</text>')

    # visible cone height (right, nominal)
    a(f'<path class="ref" d="M{num(X(NOM_RD / 2))},{num(y(0))} L620,{num(y(0))}"/>')
    a(f'<path class="ref" d="M{num(X(NOM_PD / 2))},{num(y(NOM_CONE))} '
      f'L620,{num(y(NOM_CONE))}"/>')
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M610,{num(y(0))} L610,{num(y(NOM_CONE))}"/>')
    a(f'<text class="dimtxt" x="604" y="{num((y(0) + y(NOM_CONE)) / 2)}" '
      f'transform="rotate(-90 604 {num((y(0) + y(NOM_CONE)) / 2)})">'
      f'cone h = {num(NOM_CONE, 2)}</text>')

    # flank angle p_ang at the bottom-right flank (centre = envelope corner)
    r = 62.0
    ex = rim - r * math.cos(math.radians(ANG))
    ey = zb - r * math.sin(math.radians(ANG))
    a(f'<path class="dim" marker-start="url(#arwR)" marker-end="url(#arw)" '
      f'd="M{num(rim - r)},{num(zb)} A{r},{r} 0 0,1 {num(ex)},{num(ey)}"/>')
    a(f'<text class="dimtxt" x="440" y="450">p_ang</text>')

    # clearance callout
    a(f'<path class="lead" d="M{num(rim)},{num(zt)} L516,157"/>')
    a(f'<path d="M{num(rim)},{num(zt)} L{num(rim + 9)},{num(zt - 1)} '
      f'L{num(rim + 6)},{num(zt + 5)} Z" fill="#555"/>')
    a(f'<text class="callout" x="520" y="161">c = {CLR:.2f} mm &#8212; '
      f'normal to each face</text>')
    a(f'<text class="note" x="20" y="590">rim corners extended (sharp); '
      f'cone/cylinder junction shifts by c&#183;tan(45&#176;&#8722;p_ang/2) = '
      f'{num(JUNCTION_SHIFT, 2)} mm</text>')
    a('</svg>')
    return "\n".join(out)


# --------------------------------------------------------------------------
# Top view (plan)
# --------------------------------------------------------------------------
def top_svg():
    S, cx, cy = 30.0, 340.0, 220.0
    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 450" '
      'width="700" height="450" role="img" aria-label="Retained pin top view, '
      'nominal and clearance envelope">')
    a(f'<circle class="ovr" cx="{cx}" cy="{cy}" r="{num(CLR_RD / 2 * S, 2)}"/>')
    a(f'<circle class="ovrh" cx="{cx}" cy="{cy}" r="{num(CLR_PD / 2 * S, 2)}"/>')
    a(f'<circle class="ghost" cx="{cx}" cy="{cy}" r="{num(NOM_RD / 2 * S, 2)}"/>')
    a(f'<circle class="ghosth" cx="{cx}" cy="{cy}" r="{num(NOM_PD / 2 * S, 2)}"/>')
    a(f'<path class="center" d="M{cx - 190},{cy} L{cx + 190},{cy}"/>')
    a(f'<path class="center" d="M{cx},{cy - 190} L{cx},{cy + 190}"/>')
    # callouts
    px = cx + CLR_RD / 2 * S * math.cos(math.radians(-38))
    py = cy + CLR_RD / 2 * S * math.sin(math.radians(-38))
    a(f'<path class="lead" d="M{num(px)},{num(py)} L540,110"/>')
    a(f'<path d="M{num(px)},{num(py)} L{num(px + 8)},{num(py + 2)} '
      f'L{num(px + 4)},{num(py + 8)} Z" fill="#555"/>')
    a(f'<text class="callout" x="544" y="114">&#216;{num(CLR_RD, 2)} '
      f'&#8212; rd&#8242; (envelope)</text>')
    qx = cx + CLR_PD / 2 * S * math.cos(math.radians(38))
    qy = cy + CLR_PD / 2 * S * math.sin(math.radians(38))
    a(f'<path class="lead" d="M{num(qx)},{num(qy)} L540,330"/>')
    a(f'<path d="M{num(qx)},{num(qy)} L{num(qx + 8)},{num(qy - 3)} '
      f'L{num(qx + 3)},{num(qy - 8)} Z" fill="#555"/>')
    a(f'<text class="callout" x="544" y="334">&#216;{num(CLR_PD, 2)} '
      f'&#8212; pd&#8242; (hidden)</text>')
    a(f'<text class="note" x="20" y="436">grey = nominal pin &#183; '
      f'red = clearance envelope</text>')
    a('</svg>')
    return "\n".join(out)


# --------------------------------------------------------------------------
# Meridian profile diagram (area of rotation in the XZ half-plane)
# --------------------------------------------------------------------------
def profile_svg(pts, label, clearance=False):
    S, ox, oz = 26.0, 70.0, 400.0
    max_x = max(x for x, _ in pts) * S
    max_z = max(z for _, z in pts) * S
    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 460" '
      'width="360" height="460" role="img" aria-label="' + label + '">')
    # axes
    a(f'<path class="axis" d="M{ox},{oz} L{num(ox + max_x + 44)},{oz}"/>')
    a(f'<path class="axis" d="M{ox},{oz} L{ox},{num(oz - max_z - 34)}"/>')
    a(f'<text class="axislbl" x="{num(ox + max_x + 50)}" y="{num(oz + 4)}">x</text>')
    a(f'<text class="axislbl" x="{num(ox - 26)}" y="{num(oz - max_z - 40)}">z</text>')
    # area of rotation (filled) + outline
    a(f'<path class="{"areaovr" if clearance else "area"}" '
      f'd="{poly_d(pts, S, S, ox, oz)}"/>')
    # vertex labels
    offs = [(-26, 20), (16, 20), (14, 4), (14, -6), (16, -10), (-26, -10)]
    for i, (x, z) in enumerate(pts):
        px, py = ox + x * S, oz - z * S
        dx, dy = offs[i]
        a(f'<circle class="vtx" cx="{num(px)}" cy="{num(py)}" r="2.6"/>')
        a(f'<text class="plbl" x="{num(px + dx)}" y="{num(py + dy)}">P{i}</text>')
    a('</svg>')
    return "\n".join(out)


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------
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
.legend{font-size:11px;fill:var(--mut)}
.swatch{display:inline-block;width:1.6em;height:0;border-top:2px solid #b3bac3;
 vertical-align:middle;margin:0 .3em}
.swatch.ovr{border-color:#c0392b}
/* inline-SVG classes */
path.ghost{fill:none;stroke:#b3bac3;stroke-width:1.1}
path.ovr{fill:none;stroke:#c0392b;stroke-width:1.7}
path.ovrj{fill:none;stroke:#c0392b;stroke-width:1.2}
path.center{fill:none;stroke:#c0392b;stroke-width:1.1;stroke-dasharray:10 4 3 4}
path.dim{fill:none;stroke:#666;stroke-width:1.1}
path.ref{fill:none;stroke:#777;stroke-width:1;stroke-dasharray:2 3}
path.lead{fill:none;stroke:#777;stroke-width:1.1}
path.axis{fill:none;stroke:#9aa;stroke-width:1.1}
path.area{fill:#eef4fa;stroke:#1a1a24;stroke-width:1.6;stroke-linejoin:round}
path.areaovr{fill:#fdf0ef;stroke:#c0392b;stroke-width:1.7;stroke-linejoin:round}
circle.ovr{fill:none;stroke:#c0392b;stroke-width:1.7}
circle.ovrh{fill:none;stroke:#c0392b;stroke-width:1.1;stroke-dasharray:6 4}
circle.ghost{fill:none;stroke:#b3bac3;stroke-width:1.1}
circle.ghosth{fill:none;stroke:#b3bac3;stroke-width:1.1;stroke-dasharray:6 4}
circle.vtx{fill:#1a1a24}
text.title{font-size:19px;font-weight:bold;fill:#111}
text.subtitle{font-size:12px;fill:#555}
text.dimtxt{font-size:12px;fill:#555;text-anchor:middle}
text.callout{font-size:11.5px;fill:#444}
text.note{font-size:11.5px;fill:#666}
text.plbl{font-size:13px;font-weight:bold;fill:#0b6fa4}
text.axislbl{font-size:13px;font-style:italic;fill:#666}
"""


def eq(s):
    return f"<code>{s}</code>"


def row(*cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


nom_rows = "".join(row(f"P{i}", eq(x), eq(z), note) for i, (x, z, note) in enumerate(zip(
    ["0", "rd/2", "pd/2", "pd/2", "rd/2", "0"],
    ["0", "0", "cone", "h &#8722; cone", "h", "h"],
    ["axis, bottom", "bottom end face &#8594; flare rim", "flare flank &#8594; shaft",
     "shaft &#8594; top flare", "flare flank &#8594; top rim", "top end face &#8594; axis"],
)))
clr_rows = "".join(row(f"P{i}", eq(x), eq(z), note) for i, (x, z, note) in enumerate(zip(
    ["0", "rd&#8242;/2", "pd&#8242;/2", "pd&#8242;/2", "rd&#8242;/2", "0"],
    ["0", "0", "cone&#8242;", "h&#8242; &#8722; cone&#8242;", "h&#8242;", "h&#8242;"],
    ["axis, bottom", "bottom end face &#8594; flare rim", "flare flank &#8594; shaft",
     "shaft &#8594; top flare", "flare flank &#8594; top rim", "top end face &#8594; axis"],
)))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retained Pin &#8212; Specification</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Retained pin</h1>
<p>
The retained pin is a cylindrical shaft with a splayed <b>flare</b> (cone) at
each end that traps a mating collar axially. The pin is a
<b>solid of revolution</b>, so an elevation and a plan describe it fully.
All numbers below are generated from the chosen nominal set in
<code>doc/make_pin_html.py</code>.
</p>

<h2>Parameters</h2>
<table>
<tr><th>symbol</th><th>name</th><th>value</th><th>note</th></tr>
{row(eq("pd"), "pin (shaft) diameter", f"{PD:.1f}&nbsp;mm", "straight central shaft")}
{row(eq("rd"), "retain (flare) diameter", f"{RD:.1f}&nbsp;mm", "outer diameter at each end face")}
{row(eq("h"), "overall pin height", f"{H:.1f}&nbsp;mm", "end face to end face (chosen nominal)")}
{row(eq("p_ang"), "flare flank angle (" + eq("angle") + ")", f"{num(ANG)}&#176;", "flare flank angle to the end face")}
{row(eq("c"), "clearance (" + eq("clearance") + ")", f"{CLR:.2f}&nbsp;mm", "optional; pushes every face out along its own normal")}
</table>

<h3>Derived geometry</h3>
<table>
<tr><th>symbol</th><th>meaning</th><th>expression</th><th>value</th></tr>
{row(eq("cone"), "visible cone (frustum) height", eq("(rd/2 &#8722; pd/2)&#183;tan(p_ang)"), f"{NOM_CONE:.2f}&nbsp;mm")}
{row(eq("ls"), "straight shaft length", eq("h &#8722; 2&#183;cone"), f"{SHAFT_LEN:.2f}&nbsp;mm")}
{row(eq("ca"), "complete-cone height (end face &#8594; apex)", eq("(rd/2)&#183;tan(p_ang)"), f"{APEX:.2f}&nbsp;mm")}
</table>
<p>
Valid range: <code>0 &lt; p_ang &lt; 90</code>, <code>rd &gt; pd</code>,
<code>h &gt; 2&#183;cone</code>. With <code>h = {num(H)}</code> the two
complete-cone apexes coincide, since <code>h = 2&#183;ca</code>.
</p>

<h2>Views</h2>
<figure>
{front_svg()}
<figcaption>Front view (elevation) &#183; nominal pin (grey) and clearance
envelope (red), <code>c = {CLR:.2f} mm</code>.</figcaption>
</figure>

<figure>
{top_svg()}
<figcaption>Top view (plan) &#183; looking down the pin axis.</figcaption>
</figure>

<h2>Clearance envelope</h2>
<p>
Starting from the nominal geometry, every surface is pushed out along its own
outward normal by <code>c = {num(CLR, 2)}&nbsp;mm</code>; where two offset faces
meet at the end rims they are extended to a sharp corner. The result is again a
retained pin of the same flank angle, with
<code>h&#8242; = h + 2c</code>, <code>pd&#8242; = pd + 2c</code> and
<code>rd&#8242; = rd + 2c&#183;cot(p_ang/2)</code>.
</p>
<table>
<tr><th>feature</th><th>growth</th><th>expression</th><th>value</th></tr>
{row("end (retain) &#216;", "rim, radial", eq("2c&#183;cot(p_ang/2)"), f"+{RIM_GROWTH:.2f}&nbsp;mm &#8594; &#216;{CLR_RD:.2f}")}
{row("waist (shaft) &#216;", "radial", eq("2c"), f"+{2 * CLR:.2f}&nbsp;mm &#8594; &#216;{CLR_PD:.2f}")}
{row("overall height", "axial (each face)", eq("2c"), f"+{2 * CLR:.2f}&nbsp;mm &#8594; {CLR_H:.2f}")}
{row("cone/cylinder junction", "axial shift", eq("c&#183;tan(45&#176; &#8722; p_ang/2)"), f"+{JUNCTION_SHIFT:.2f}&nbsp;mm")}
</table>

<h2>Area of rotation</h2>
<p>
The pin is swept by revolving the closed meridian profile about the <i>z</i>
axis. The profile lies in the XZ half-plane (<code>y = 0</code>): <i>x</i> is
the distance from the axis and <i>z</i> the height. The closing segment
P5&nbsp;&#8594;&nbsp;P0 lies on the axis, so a 360&#176; revolution makes a
closed solid. Every point is shown as an equation below.
</p>

<h3>Nominal pin</h3>
<p>with <code>cone = (rd/2 &#8722; pd/2)&#183;tan(p_ang)</code>:</p>
<div class="fig-grid">
<figure>
{profile_svg(NOM_PTS, "Nominal rotation profile")}
<figcaption>Nominal profile &#183; revolve about <i>z</i>.</figcaption>
</figure>
<div>
<table>
<tr><th>point</th><th>x</th><th>z</th><th>between</th></tr>
{nom_rows}
</table>
</div>
</div>
<p>Path in <code>x,z</code> (numeric, from the chosen values):</p>
<pre><code>{path_d(NOM_PTS)}</code></pre>

<h3>Clearance version</h3>
<p>
Same six-point form with the clearance-grown values
<code>h&#8242; = h + 2c</code>, <code>pd&#8242; = pd + 2c</code>,
<code>rd&#8242; = rd + 2c/tan(p_ang/2)</code> and
<code>cone&#8242; = (rd&#8242;/2 &#8722; pd&#8242;/2)&#183;tan(p_ang)</code>:
</p>
<div class="fig-grid">
<figure>
{profile_svg(CLR_PTS, "Clearance rotation profile", clearance=True)}
<figcaption>Clearance profile &#183; same flank angle.</figcaption>
</figure>
<div>
<table>
<tr><th>point</th><th>x</th><th>z</th><th>between</th></tr>
{clr_rows}
</table>
</div>
</div>
<p>Path in <code>x,z</code> (numeric, <code>c = {CLR:.2f}</code>):</p>
<pre><code>{path_d(CLR_PTS)}</code></pre>
<p>
The envelope is built from <code>z = 0</code> like any pin. To centre it on the
nominal pin, as in the drawing, shift it by <code>&#8722;c</code>
(<code>z &#8594; z &#8722; c</code>), so it spans
<code>z = &#8722;{CLR:.2f} &#8230; {CLR_H - CLR:.2f}</code>.
</p>

<h2>Module</h2>
<p>
The part is built by <code>pin_retained()</code> in
<code>pin_retained.py</code>; the same call with
<code>clearance={CLR:.2f}</code> gives the envelope.
</p>
<pre><code>from pin_retained import pin_retained

pin = pin_retained(doc, "Pin", height={H:.1f}, diam={PD:.1f},
                   diam_end={RD:.1f}, angle={ANG:.0f})
env = pin_retained(doc, "Envelope", height={H:.1f}, diam={PD:.1f},
                   diam_end={RD:.1f}, angle={ANG:.0f},
                   clearance={CLR:.2f})</code></pre>

<p class="foot">
Values: <code>pd = {PD:.1f}</code>, <code>rd = {RD:.1f}</code>,
<code>h = {H:.1f}</code>, <code>p_ang = {ANG:.0f}</code>,
<code>c = {CLR:.2f}</code>. Generated by <code>doc/make_pin_html.py</code>;
regenerate after changing a parameter.
</p>
</main>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({len(html)} bytes)")
