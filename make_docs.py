"""Regenerate the HTML page of every primitive, plus index.html.

    freecadcmd make_docs.py

Each primlib/primitives/<key>.py gets primlib/primitives/<key>.html rendered
from the class declarations (docstring, params, derived, checks, walls),
with the section drawing and every number evaluated at the defaults --
so the page cannot drift from the code. Do not edit the HTML by hand.
"""

import html
import inspect
import itertools
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

from primlib import available  # noqa: E402
from primlib.core import Revolved, expand, parameter_sheet, value  # noqa: E402

CSS = """
:root { --bg:#fff; --fg:#1d1d1f; --muted:#6e6e73; --line:#d2d2d7;
        --panel:#f5f5f7; --solid:#9fb8d8; --edge:#2b5d9b; --axis:#c0392b;
        --mate:#f0c48f; --mate-edge:#b35f12; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#161618; --fg:#ececf0; --muted:#9a9aa2; --line:#3a3a40;
          --panel:#202024; --solid:#2f4a6e; --edge:#8db4e8; --axis:#e57368;
          --mate:#7a4f22; --mate-edge:#f0b071; } }
body { background:var(--bg); color:var(--fg); margin:0;
       font:15px/1.55 system-ui, sans-serif; }
main { max-width:860px; margin:0 auto; padding:32px 16px 64px; }
h1 { font-size:1.7rem; margin:0 0 4px; } h2 { font-size:1.15rem; margin:36px 0 8px; }
.sub { color:var(--muted); margin:0 0 24px; }
p { margin:0 0 12px; } code { font:0.9em ui-monospace, monospace; }
pre { background:var(--panel); padding:12px 14px; border-radius:6px; overflow-x:auto; }
.wrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:0.92rem; }
th, td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--line);
         vertical-align:top; }
th { color:var(--muted); font-weight:600; }
td.num { font-variant-numeric:tabular-nums; white-space:nowrap; }
figure { margin:0; background:var(--panel); border-radius:6px; padding:16px; }
figcaption { color:var(--muted); font-size:0.88rem; margin-top:8px; }
.row { display:flex; flex-wrap:wrap; gap:12px; }
.row figure { flex:1 1 200px; }
svg { display:block; max-width:100%; height:auto; margin:0 auto; }
a { color:var(--edge); }
"""


def esc(text):
    return html.escape(str(text))


def num(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def prose(text):
    """One docstring paragraph as HTML, `name` spans set as code,
    **text** bold."""
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(" ".join(text.split())))
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)


def page(title, body):
    return (f"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{esc(title)}</title><style>{CSS}</style></head>"
            f"<body><main>{body}</main></body></html>\n")


def table(head, rows, num_cols=()):
    out = ["<div class=\"wrap\"><table><tr>"]
    out += [f"<th>{esc(h)}</th>" for h in head]
    out.append("</tr>")
    for row in rows:
        out.append("<tr>" + "".join(
            f"<td class=\"num\">{c}</td>" if i in num_cols else f"<td>{c}</td>"
            for i, c in enumerate(row)) + "</tr>")
    out.append("</table></div>")
    return "".join(out)


LAYER = {"self": ("var(--solid)", "var(--edge)"),
         "mate": ("var(--mate)", "var(--mate-edge)")}


_CLIPS = itertools.count()     # one clip path id per drawing on a page


def section_svg(layers, window=None, gap=None, mirror=True):
    """Meridian section through the axis, profiles mirrored about it.

    `layers` is a list of (points, style, label prefix) drawn in order,
    style a LAYER key. `window` (r0, r1, z0, z1) zooms onto a region of
    the right half instead of fitting everything. `gap` (p, q, text)
    draws a dimension between two (r, z) points. With `mirror` False the
    points are a whole section, (y, z), drawn as they are, without the
    axis or vertex numbers (a label prefix of None also leaves a layer's
    numbers off).
    """
    if window:
        r_lo, r_hi, z_lo, z_hi = window
        scale = 360.0 / max(r_hi - r_lo, z_hi - z_lo)
    else:
        r_hi = max(r for pts, _, _ in layers for r, _ in pts)
        r_lo = -r_hi if mirror else min(r for pts, _, _ in layers for r, _ in pts)
        z_lo = min(z for pts, _, _ in layers for _, z in pts)
        z_hi = max(z for pts, _, _ in layers for _, z in pts)
        scale = (300.0 if mirror else 600.0) / max(r_hi - r_lo, z_hi - z_lo)
    pad = 44.0
    w = (r_hi - r_lo) * scale + 2 * pad
    hgt = (z_hi - z_lo) * scale + 2 * pad

    def xy(r, z):
        return pad + (r - r_lo) * scale, pad + (z_hi - z) * scale

    def poly(pts, sign):
        return " ".join("{:.2f},{:.2f}".format(*xy(sign * r, z)) for r, z in pts)

    cx = xy(0.0, 0.0)[0]
    clip = f"clip{next(_CLIPS)}"
    parts = [f'<svg viewBox="0 0 {w:.0f} {hgt:.0f}" width="{w:.0f}" '
             f'role="img" aria-label="section through the axis">'
             f'<clipPath id="{clip}"><rect x="{pad / 2}" y="{pad / 2}" '
             f'width="{w - pad:.2f}" height="{hgt - pad:.2f}"/></clipPath>'
             f'<g clip-path="url(#{clip})">']
    for pts, style, _ in layers:
        fill, stroke = LAYER[style]
        for sign in ((1, -1) if mirror else (1,)):
            parts.append(f'<polygon points="{poly(pts, sign)}" fill="{fill}" '
                         f'fill-opacity="0.85" stroke="{stroke}" '
                         f'stroke-width="1.5" stroke-linejoin="round"/>')
    if mirror:
        parts.append(f'<line x1="{cx:.2f}" y1="0" x2="{cx:.2f}" y2="{hgt:.2f}" '
                     f'stroke="var(--axis)" stroke-dasharray="8 4 2 4"/>')
    for pts, style, prefix in layers:
        if not mirror or prefix is None:
            continue
        for i, (r, z) in enumerate(pts):
            x, y = xy(r, z)
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" '
                         f'fill="{LAYER[style][1]}"/><text x="{x + 6:.2f}" '
                         f'y="{y - 5:.2f}" font-size="11" '
                         f'fill="{LAYER[style][1]}">{prefix}{i}</text>')
    if gap:
        (pr, pz), (qr, qz), text = gap
        (x1, y1), (x2, y2) = xy(pr, pz), xy(qr, qz)
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" '
                     f'y2="{y2:.2f}" stroke="var(--fg)" stroke-width="1.5"/>'
                     f'<text x="{max(x1, x2) + 8:.2f}" y="{(y1 + y2) / 2 + 4:.2f}" '
                     f'font-size="13" fill="var(--fg)">{esc(text)}</text>')
    parts.append("</g></svg>")
    return "".join(parts)


def _face(pts):
    """Planar face of a closed (r, z) profile, z mapped to global y."""
    vs = [App.Vector(r, z, 0.0) for r, z in pts]
    return Part.Face(Part.makePolygon(vs + vs[:1]))


def _boundary(pts):
    """The profile's real faces as edges: the closing run along the axis is left out."""
    edges = [Part.makeLine(App.Vector(p[0], p[1], 0), App.Vector(q[0], q[1], 0))
             for p, q in zip(pts, pts[1:] + pts[:1])
             if not (abs(p[0]) < 1e-9 and abs(q[0]) < 1e-9)]
    return Part.Compound(edges)


def fit_section(cls, env, sheet, pts, mate, prims):
    """HTML for one Mate: the pair in section and the clearance per face."""
    mcls = prims[mate.key]
    menv = mcls.bind(sheet, prefix=f"{mate.key}_",
                     bind={k: expand(v, env) for k, v in mate.bind.items()})
    sheet.Document.recompute()
    mpts = [(value(sheet, r), value(sheet, z)) for r, z in mcls.profile(menv)]

    body_face, mate_face = _face(pts), _face(mpts)
    boundary = _boundary(pts)
    if mate.fit == "inside":      # this part is an envelope around the mate
        overlap = mate_face.cut(body_face).Area
    else:                         # the mate sits in a cavity of this part
        overlap = body_face.common(mate_face).Area
    rows, closest = [], None
    for i, (p, q) in enumerate(zip(mpts, mpts[1:] + mpts[:1])):
        if abs(p[0]) < 1e-9 and abs(q[0]) < 1e-9:
            continue                      # on the axis: not a real face
        edge = Part.makeLine(App.Vector(p[0], p[1], 0), App.Vector(q[0], q[1], 0))
        dist, pairs, _ = edge.distToShape(boundary)
        a, b = pairs[0]
        rows.append((f"p{i}–p{(i + 1) % len(mpts)}",
                     f"{num(a.x)}, {num(a.y)}", f"{num(b.x)}, {num(b.y)}",
                     num(dist)))
        if closest is None or dist < closest[0]:
            closest = (dist, (a.x, a.y), (b.x, b.y), rows[-1][0])

    bound = "".join(f"<tr><td><code>{esc(k)}</code></td><td><code>{esc(v)}"
                    f"</code></td></tr>" for k, v in mate.bind.items())
    out = [f"<h2>Fit with {esc(mcls.title)}</h2>",
           f"<p>{esc(mate.note).capitalize()}. Its parameters follow this "
           f"part's; the rest keep the <a href=\"{mate.key}.html\">"
           f"{esc(mcls.title.lower())}</a> defaults.</p>",
           f"<div class=\"wrap\"><table><tr><th>{esc(mate.key)} param</th>"
           f"<th>bound to</th></tr>{bound}</table></div>",
           "<p></p><figure>",
           section_svg([(pts, "self", ""), (mpts, "mate", "p")]),
           f"<figcaption>{esc(cls.title)} (blue) with {esc(mcls.title.lower())} "
           f"(orange) at the defaults. Mate vertices are numbered "
           f"p0, p1, …</figcaption></figure>"]

    if mate.fit == "inside":
        verdict = ("the mate lies wholly inside this part" if overlap < 1e-9 else
                   f"<b>{num(overlap)} mm² of the mate's section sticks out</b>")
    else:
        verdict = ("no interference" if overlap < 1e-9 else
                   f"<b>interference: {num(overlap)} mm² of the section overlaps</b>")
    out.append(f"<p></p><p>Check of the two sections: {verdict}. Minimum "
               f"clearance <b>{num(closest[0])} mm</b>, at {closest[3]}.</p>")
    out.append(table(("mate face", "closest point on mate (r, z)",
                      "closest point on this part (r, z)", "clearance (mm)"),
                     rows, num_cols=(1, 2, 3)))

    layers = [(pts, "self", ""), (mpts, "mate", "p")]
    dist, a, b, where = closest
    out.append(detail_figure(layers, dist, a, b,
                             f"Detail at the minimum clearance ({where})"))
    for index, label in mate.details:
        v = mpts[index]
        dist, pairs, _ = Part.Vertex(App.Vector(v[0], v[1], 0)).distToShape(boundary)
        q = pairs[0][1]
        out.append(detail_figure(layers, dist, v, (q.x, q.y),
                                 f"Detail at p{index}, {esc(label)}: "
                                 f"clearance {num(dist)} mm"))
    return "".join(out)


def detail_figure(layers, dist, a, b, caption, mirror=True):
    """Enlarged section around the gap a -> b, dimensioned."""
    half = max(0.6, 6.0 * dist)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    window = (mid[0] - half, mid[0] + half, mid[1] - half, mid[1] + half)
    return ("<p></p><figure>" + section_svg(layers, window=window, mirror=mirror,
                                            gap=(a, b, f"{num(dist)} mm")) +
            f"<figcaption>{caption}, {num(2 * half)} mm square."
            f"</figcaption></figure>")


def _cross_section(shape, x):
    """`shape` cut across at x: (face, its wires, its outline as (y, z) loops)."""
    wires = shape.slice(App.Vector(1, 0, 0), x)
    face = Part.makeFace(wires, "Part::FaceMakerBullseye")
    loops = [[(p.y, p.z) for p in w.discretize(Deflection=0.002)] for w in wires]
    return face, wires, loops


def slide_fit_section(cls, env, sheet, shape, key, note, prims):
    """HTML for one of `fits`: the mate built with this part's values at
    the same origin, the pair cut across halfway along, and the clearance
    of each of the mate's faces near this part."""
    mcls = prims[key]
    shared = [p.name for p in mcls.params if p.name in env]
    menv = mcls.bind(sheet, prefix=f"{key}_",
                     bind={n: expand(n, env) for n in shared})
    sheet.Document.recompute()
    mate = mcls.build(sheet.Document, "Mate", sheet, menv)
    sheet.Document.recompute()
    x = value(sheet, expand("length", env)) / 2
    face, wires, loops = _cross_section(shape, x)
    mface, mwires, mloops = _cross_section(mate.Shape, x)
    boundary = Part.Compound(wires)

    rows, closest, near = [], None, 1.0
    for i, edge in enumerate(e for w in mwires for e in w.Edges):
        dist, pairs, _ = edge.distToShape(boundary)
        a, b = pairs[0]
        if closest is None or dist < closest[0]:
            closest = (dist, (a.y, a.z), (b.y, b.z), f"e{i}")
        if dist >= near:
            continue
        p, q = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
        kind = (f"arc r {num(edge.Curve.Radius)}" if hasattr(edge.Curve, "Radius")
                else "line")
        rows.append((f"e{i}", kind, f"{num(p.y)}, {num(p.z)} → {num(q.y)}, {num(q.z)}",
                     f"{num(a.y)}, {num(a.z)}", num(dist)))
    overlap = face.common(mface).Area
    verdict = ("no interference" if overlap < 1e-9 else
               f"<b>interference: {num(overlap)} mm² of the section overlaps</b>")
    layers = [(p, "self", None) for p in loops] + [(p, "mate", None) for p in mloops]
    dist, a, b, where = closest
    return "".join([
        f"<h2>Fit with {esc(mcls.title)}</h2>",
        f"<p>{esc(note).capitalize()}: the <a href=\"{key}.html\">"
        f"{esc(mcls.title.lower())}</a> takes this part's values of "
        f"{', '.join(f'<code>{esc(n)}</code>' for n in shared)}; its own "
        f"parameters keep their defaults. Both are cut across at x = {num(x)}, "
        f"halfway along.</p><figure>",
        section_svg(layers, mirror=False),
        f"<figcaption>{esc(cls.title)} (blue) with {esc(mcls.title.lower())} "
        f"(orange) at the defaults, looking along -x (y across, z up)."
        f"</figcaption></figure>",
        f"<p></p><p>Check of the two sections: {verdict}. Minimum clearance "
        f"<b>{num(dist)} mm</b>, at {where}.</p>",
        f"<p>The mate's faces within {num(near)} mm of this part, numbered "
        f"e0, e1, … round the mate's section:</p>",
        table(("mate face", "kind", "from → to (y, z)",
               "closest point on mate (y, z)", "clearance (mm)"),
              rows, num_cols=(2, 3, 4)),
        detail_figure(layers, dist, a, b,
                      f"Detail at the minimum clearance ({where})", mirror=False)])


def check_expr(expr, limit=70):
    """A check expression as code; long ones (expanded from a primitive
    used inside this one) folded away behind a disclosure."""
    if len(expr) <= limit:
        return f"<code>{esc(expr)}</code>"
    return (f"<details><summary>expression</summary><code>{esc(expr)}</code>"
            f"</details>")


def numeric_profile(cls, sheet, env):
    return [(value(sheet, r), value(sheet, z)) for r, z in cls.profile(env)]


def profile_section(cls, env, sheet):
    """Revolved: the profile, its vertex table, variants and mates."""
    pts = numeric_profile(cls, sheet, env)
    out = ["<h2>Profile</h2>",
           f"<figure>{section_svg([(pts, 'self', '')])}<figcaption>Section "
           f"through the axis at the defaults. The half-profile on the right "
           f"is the sketch; vertex numbers match the table.</figcaption></figure>",
           table(("vertex", "r", "z", "r, z at defaults"),
                 [(str(i), f"<code>{esc(r)}</code>", f"<code>{esc(z)}</code>",
                   f"{num(pts[i][0])}, {num(pts[i][1])}")
                  for i, (r, z) in enumerate(cls.symbolic_profile())],
                 num_cols=(3,))]
    if cls.variants:
        out.append("<h2>Variants</h2><p>The same sketch at other parameter "
                   "values; all other parameters at their defaults.</p>"
                   "<div class=\"row\">")
        for i, (label, values) in enumerate(cls.variants):
            vsheet = parameter_sheet(sheet.Document, f"Variant{i}")
            venv = cls.bind(vsheet, **values)
            sheet.Document.recompute()
            setting = ", ".join(f"{k} = {v}" for k, v in values.items())
            out.append(f"<figure>{section_svg([(numeric_profile(cls, vsheet, venv), 'self', '')])}"
                       f"<figcaption><b>{esc(label)}</b> ({esc(setting)})"
                       f"</figcaption></figure>")
        out.append("</div>")
    for mate in cls.mates:
        out.append(fit_section(cls, env, sheet, pts, mate, available()))
    return "".join(out)


def _polyline(edge):
    return [(v.x, v.y, v.z) for v in edge.discretize(Deflection=0.01)]


def shape_svg(groups, lines, width=640.0, max_height=420.0, hidden=(), dims=()):
    """Filled groups of closed loops (each group one even-odd path) plus thin
    lines and dashed `hidden` lines, (u, v) with v up. `dims` are dimension
    lines: ("u", a, b, at, base) runs along u from a to b at v = `at`, with
    extension lines from v = `base`; ("v", ...) the same along v."""
    every = [p for group in groups for pts in group for p in pts] + \
        [p for pts in list(lines) + list(hidden) for p in pts]
    for kind, a, b, at, _ in dims:
        every += [(a, at), (b, at)] if kind == "u" else [(at, a), (at, b)]
    u_lo, u_hi = min(p[0] for p in every), max(p[0] for p in every)
    v_lo, v_hi = min(p[1] for p in every), max(p[1] for p in every)
    scale = min(width / max(u_hi - u_lo, 1e-9), max_height / max(v_hi - v_lo, 1e-9))
    pad = 28.0 if dims else 16.0
    w = (u_hi - u_lo) * scale + 2 * pad
    h = (v_hi - v_lo) * scale + 2 * pad

    def xy(p):
        return f"{pad + (p[0] - u_lo) * scale:.2f},{pad + (v_hi - p[1]) * scale:.2f}"

    out = [f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" role="img">']
    if dims:
        out.append('<defs><marker id="dim" viewBox="0 0 10 10" refX="5" refY="5" '
                   'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                   '<path d="M 0 2 L 10 5 L 0 8 z" fill="var(--muted)"/></marker></defs>')
    for group in groups:
        fill = " ".join("M " + " L ".join(xy(p) for p in pts) + " Z" for pts in group)
        out.append(f'<path d="{fill}" fill="var(--solid)" fill-rule="evenodd" '
                   f'stroke="var(--edge)" stroke-width="1.5" stroke-linejoin="round"/>')
    for pts in hidden:
        out.append(f'<polyline points="{" ".join(xy(p) for p in pts)}" '
                   f'fill="none" stroke="var(--edge)" stroke-width="0.6" '
                   f'stroke-dasharray="3 2" opacity="0.45"/>')
    for pts in lines:
        out.append(f'<polyline points="{" ".join(xy(p) for p in pts)}" '
                   f'fill="none" stroke="var(--edge)" stroke-width="0.8"/>')
    for kind, a, b, at, base in dims:
        ends = [(a, at), (b, at)] if kind == "u" else [(at, a), (at, b)]
        roots = [(a, base), (b, base)] if kind == "u" else [(base, a), (base, b)]
        line = 'stroke="var(--muted)" stroke-width="0.7" fill="none"'
        for root, end in zip(roots, ends):
            out.append(f'<polyline points="{xy(root)} {xy(end)}" {line}/>')
        out.append(f'<polyline points="{xy(ends[0])} {xy(ends[1])}" {line} '
                   f'marker-start="url(#dim)" marker-end="url(#dim)"/>')
        mid = [float(c) for c in xy(((a + b) / 2, at) if kind == "u" else (at, (a + b) / 2)).split(",")]
        turn = "" if kind == "u" else f' transform="rotate(-90 {mid[0]:.2f} {mid[1]:.2f})"'
        out.append(f'<text x="{mid[0]:.2f}" y="{mid[1] - 3:.2f}" text-anchor="middle" '
                   f'font-size="11" fill="var(--fg)"{turn}>{num(abs(b - a))}</text>')
    out.append("</svg>")
    return "".join(out)


def front_svg(shape, dims=()):
    """Hidden-line view of `shape` from +x, y across and z up: visible
    edges solid, hidden ones dashed. `dims` are (axis, lo, hi, row) in
    model coordinates, axis "y" (drawn below) or "z" (drawn on the left),
    row 1 nearest the drawing."""
    import TechDraw

    views = TechDraw.projectEx(shape, App.Vector(1, 0, 0))

    def edges(indices):
        # projectEx lays the view out with u = z and v = -y; turn it so
        # y runs across and z up.
        return [[(-y, x) for x, y, _ in _polyline(e)]
                for i in indices if views[i] and not views[i].isNull()
                for e in views[i].Edges]

    seen, hidden = edges((0, 3)), edges((5, 8))
    pts = [p for e in seen + hidden for p in e]
    u_lo = min(p[0] for p in pts)
    v_lo = min(p[1] for p in pts)
    step = 0.07 * max(max(p[0] for p in pts) - u_lo, max(p[1] for p in pts) - v_lo)
    placed = [("u", lo, hi, v_lo - row * step, v_lo) if axis == "y"
              else ("v", lo, hi, u_lo - row * step, u_lo)
              for axis, lo, hi, row in dims]
    return shape_svg([], seen, hidden=hidden, dims=placed)


# Third-angle views: (u, v) axes in model coordinates, the view looking
# along -(u x v); the top view goes above the front, the side to its right.
VIEW_AXES = {"front": ((0, 1, 0), (0, 0, 1)),
             "top": ((0, 1, 0), (-1, 0, 0)),
             "side": ((-1, 0, 0), (0, 0, 1))}
VIEW_TITLES = {"front": "Front", "top": "Top", "side": "Right side"}


def _uv(view, p):
    u, v = VIEW_AXES[view]
    return (sum(a * b for a, b in zip(u, p)), sum(a * b for a, b in zip(v, p)))


def view_edges(shape, view):
    """(visible, hidden) polylines of `shape` in `view`'s (u, v)."""
    import TechDraw

    u, v = VIEW_AXES[view]
    w = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    m = App.Matrix(*u, 0, *v, 0, *w, 0, 0, 0, 0, 1)
    turned = shape.copy()
    turned.transformShape(m)
    out = TechDraw.projectEx(turned, App.Vector(0, 0, 1))

    def edges(indices):
        return [[(x, y) for x, y, _ in _polyline(e)]
                for i in indices if out[i] and not out[i].isNull() for e in out[i].Edges]
    return edges((0, 3)), edges((5, 8))


def views_svg(shape, dims, width=900.0, max_height=760.0, only=None):
    """Top, front and right-side views of `shape` in third-angle projection,
    hidden edges dashed, with `dims`: (view, kind, p1, p2, at, label), the
    points in model coordinates. Kind "u" or "v" measures along that view
    axis, drawn `at` rows beyond the view (u: + below, - above; v: + left,
    - right); "a" measures p1 to p2 directly, drawn `at` mm to the left of
    the line from p1 to p2; "angle" measures the angle at p1 between the
    lines to the two points in p2, an arc `at` rows out from p1, with
    the lines drawn thin to p1 (a sharp corner the rounds have cut off);
    "mark" is a centre mark at p1 and "line" a construction line from p1
    to p2 (no label). `only` draws just those views (names of VIEW_AXES)."""
    views = {name: view_edges(shape, name) for name in (only or VIEW_AXES)}
    boxes = {}
    for name, (seen, hidden) in views.items():
        pts = [p for e in seen + hidden for p in e]
        boxes[name] = [min(p[0] for p in pts), max(p[0] for p in pts),
                       min(p[1] for p in pts), max(p[1] for p in pts)]
    extent = max(max(b[1] - b[0], b[3] - b[2]) for b in boxes.values())
    step = 0.06 * extent

    items = {name: [] for name in views}   # (kind, ends, roots, text) in (u, v)
    ext = {name: list(box) for name, box in boxes.items()}
    for view, kind, p1, p2, at, label in dims:
        a, b = _uv(view, p1), _uv(view, p1 if kind == "angle" else p2 or p1)
        u_lo, u_hi, v_lo, v_hi = boxes[view]
        if kind == "mark":
            items[view].append(("mark", [a], [], ""))
            continue
        if kind == "line":
            items[view].append(("line", [a, b], [], ""))
            continue
        if kind == "angle":
            legs = [_uv(view, q) for q in p2]
            t1, t2 = (math.atan2(q[1] - a[1], q[0] - a[0]) for q in legs)
            sweep = (t2 - t1 + math.pi) % (2 * math.pi) - math.pi
            r = at * step
            arc = [(a[0] + r * math.cos(t1 + sweep * i / 24),
                    a[1] + r * math.sin(t1 + sweep * i / 24)) for i in range(25)]
            items[view].append(("angle", arc, [a] + legs,
                                f"{label} {num(abs(math.degrees(sweep)))}°"))
            e = ext[view]
            for q in arc:
                e[0], e[1] = min(e[0], q[0] - 3 * step), max(e[1], q[0] + 3 * step)
                e[2], e[3] = min(e[2], q[1] - step), max(e[3], q[1] + step)
            continue
        if kind == "u":
            line = v_lo - at * step if at > 0 else v_hi - at * step
            ends, size = [(a[0], line), (b[0], line)], abs(b[0] - a[0])
        elif kind == "v":
            line = u_lo - at * step if at > 0 else u_hi - at * step
            ends, size = [(line, a[1]), (line, b[1])], abs(b[1] - a[1])
        else:
            du, dv = b[0] - a[0], b[1] - a[1]
            size = (du * du + dv * dv) ** 0.5
            n = (-dv / size, du / size)
            ends = [(a[0] + n[0] * at, a[1] + n[1] * at), (b[0] + n[0] * at, b[1] + n[1] * at)]
        items[view].append(("dim", ends, [a, b], f"{label} {num(size)}"))
        e = ext[view]
        for q in ends:
            e[0], e[1] = min(e[0], q[0] - step), max(e[1], q[0] + step)
            e[2], e[3] = min(e[2], q[1] - step), max(e[3], q[1] + step)

    gap = 2 * step
    offset = {"front": (0.0, 0.0)}
    if "top" in views:
        offset["top"] = (0.0, ext["front"][3] + gap - ext["top"][2])
    if "side" in views:
        offset["side"] = (ext["front"][1] + gap - ext["side"][0], 0.0)
    u_lo = min(ext[n][0] + offset[n][0] for n in views)
    u_hi = max(ext[n][1] + offset[n][0] for n in views)
    v_lo = min(ext[n][2] + offset[n][1] for n in views) - step
    v_hi = max(ext[n][3] + offset[n][1] for n in views)
    scale = min(width / (u_hi - u_lo), max_height / (v_hi - v_lo))
    pad = 12.0
    w, h = (u_hi - u_lo) * scale + 2 * pad, (v_hi - v_lo) * scale + 2 * pad

    out = [f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" role="img">',
           '<defs><marker id="vdim" viewBox="0 0 10 10" refX="5" refY="5" '
           'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
           '<path d="M 0 2 L 10 5 L 0 8 z" fill="var(--muted)"/></marker></defs>']
    for name, (seen, hidden) in views.items():
        du, dv = offset[name]

        def xy(p):
            return (pad + (p[0] + du - u_lo) * scale, pad + (v_hi - p[1] - dv) * scale)

        def pts(ps):
            return " ".join(f"{x:.2f},{y:.2f}" for x, y in map(xy, ps))
        for e in hidden:
            out.append(f'<polyline points="{pts(e)}" fill="none" stroke="var(--edge)" '
                       f'stroke-width="0.6" stroke-dasharray="3 2" opacity="0.45"/>')
        for e in seen:
            out.append(f'<polyline points="{pts(e)}" fill="none" stroke="var(--edge)" '
                       f'stroke-width="0.9"/>')
        line = 'stroke="var(--muted)" stroke-width="0.7" fill="none"'
        for kind, ends, roots, text in items[name]:
            if kind == "mark":
                (cx, cy), r = xy(ends[0]), 0.5 * step * scale
                out.append(f'<path d="M {cx - r:.2f} {cy:.2f} H {cx + r:.2f} M {cx:.2f} '
                           f'{cy - r:.2f} V {cy + r:.2f}" stroke="var(--axis)" stroke-width="0.8"/>')
                continue
            if kind == "line":
                out.append(f'<polyline points="{pts(ends)}" stroke="var(--axis)" '
                           f'stroke-width="0.7" stroke-dasharray="8 2 2 2" fill="none"/>')
                continue
            if kind == "angle":
                vertex = roots[0]
                for leg in roots[1:]:
                    out.append(f'<polyline points="{pts([vertex, leg])}" {line} '
                               f'stroke-dasharray="3 2" opacity="0.6"/>')
                out.append(f'<polyline points="{pts(ends)}" {line} '
                           f'marker-start="url(#vdim)" marker-end="url(#vdim)"/>')
                mid = ends[len(ends) // 2]
                far = (vertex[0] + 1.6 * (mid[0] - vertex[0]),
                       vertex[1] + 1.6 * (mid[1] - vertex[1]))
                tx, ty = xy(far)
                out.append(f'<text x="{tx:.2f}" y="{ty + 3:.2f}" text-anchor="middle" '
                           f'font-size="10" fill="var(--fg)">{esc(text)}</text>')
                continue
            for root, end in zip(roots, ends):
                out.append(f'<polyline points="{pts([root, end])}" {line} opacity="0.6"/>')
            out.append(f'<polyline points="{pts(ends)}" {line} '
                       f'marker-start="url(#vdim)" marker-end="url(#vdim)"/>')
            (x0, y0), (x1, y1) = xy(ends[0]), xy(ends[1])
            angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if angle > 90 or angle <= -90:
                angle -= 180 if angle > 0 else -180
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            out.append(f'<text x="{mx:.2f}" y="{my - 3:.2f}" text-anchor="middle" font-size="10" '
                       f'fill="var(--fg)" transform="rotate({angle:.1f} {mx:.2f} {my:.2f})">'
                       f'{esc(text)}</text>')
        title_x, title_y = xy(((boxes[name][0] + boxes[name][1]) / 2, ext[name][2]))
        out.append(f'<text x="{title_x:.2f}" y="{title_y + 12:.2f}" text-anchor="middle" '
                   f'font-size="11" font-weight="600" fill="var(--muted)">'
                   f'{VIEW_TITLES[name]}</text>')
    out.append("</svg>")
    return "".join(out)


def views_section(cls, env, sheet, shape):
    """The views in third-angle projection, dimensioned with the
    parameters they show, and those parameters' table."""
    pt = lambda p: tuple(value(sheet, expand(c, env)) for c in p)  # noqa: E731
    dims = [(view, kind, pt(p1),
             tuple(map(pt, p2)) if kind == "angle" else pt(p2) if p2 else None, at, label)
            for view, kind, p1, p2, at, label in cls.views]
    names = list(dict.fromkeys(label for *_, label in cls.views if label))
    notes = {p.name: p.note for p in cls.params}
    notes.update((n, note) for n, _, note in cls.fixed + cls.derived)
    rows = [(f"<code>{esc(n)}</code>", num(value(sheet, expand(n, env))),
             esc(notes.get(n, "")))
            for n in names]
    return ("<h2>Views</h2>"
            f"<figure>{views_svg(shape, dims)}<figcaption>Third-angle projection at the "
            "defaults: top view above the front view, right side view to its right; "
            "hidden edges dashed, axes marked where shown, dimensions labelled with the "
            "parameters that set them (mm).</figcaption></figure>"
            + table(("parameter", "default", "note"), rows, num_cols=(1,)))


def shape_section(cls, env, sheet, shape):
    """Any other primitive: plan view and section of the built shape."""

    groups = []                       # each solid's top face(s), filled
    for solid in shape.Solids:
        z_top = solid.BoundBox.ZMax
        groups.append([[(x, y) for x, y, _ in w.discretize(Deflection=0.01)]
                       for f in solid.Faces
                       if abs(f.BoundBox.ZMin - z_top) < 1e-6
                       and abs(f.BoundBox.ZMax - z_top) < 1e-6
                       for w in f.Wires])
    lines = []
    for e in shape.Edges:
        pts = [(x, y) for x, y, _ in _polyline(e)]
        span = max(abs(pts[0][0] - p[0]) + abs(pts[0][1] - p[1]) for p in pts)
        if span > 1e-6:
            lines.append(pts)

    planes = cls.section_y or (None,)
    if isinstance(planes, str):
        planes = (planes,)
    out = ["<h2>Shape</h2>",
           f"<figure>{shape_svg(groups, lines)}<figcaption>Plan view from "
           f"above at the defaults: each solid's top face, with every edge "
           f"below it drawn thin.</figcaption></figure>"]
    if cls.front_view:
        dims = [(axis, value(sheet, expand(lo, env)), value(sheet, expand(hi, env)), row)
                for axis, lo, hi, row in cls.front_dims]
        out.append(f"<p></p><figure>{front_svg(shape, dims)}<figcaption>Front view at "
                   f"the defaults, the whole shape seen from +x with y across and "
                   f"z up: hidden edges dashed"
                   f"{', main dimensions in mm' if dims else ''}.</figcaption></figure>")
    for plane in planes:
        y_cut = (value(sheet, expand(plane, env)) if plane
                 else shape.BoundBox.Center.y)
        cut = [[[(x, z) for x, _, z in w.discretize(Deflection=0.01)]
                for w in solid.slice(App.Vector(0, 1, 0), y_cut)]
               for solid in shape.Solids]
        out.append(f"<p></p><figure>{shape_svg([g for g in cut if g], [])}"
                   f"<figcaption>Section at y = {num(y_cut)}"
                   f"{f' (<code>{esc(plane)}</code>)' if plane else ''}, "
                   f"looking along +y.</figcaption></figure>")
    return "".join(out)


def objects_note(cls, key):
    tag = f"tagged <code>PrimlibPrimitive = \"{key}\"</code>"
    if issubclass(cls, Revolved):
        made = ("a sketch <code>&lt;name&gt;_sketch</code> whose vertex <i>i</i> "
                "is held by constraints <code>r<i>i</i></code> and "
                "<code>z<i>i</i></code>, and the <code>Part::Revolution</code> "
                f"<code>&lt;name&gt;</code>, {tag}")
    else:
        made = (f"the hidden helper objects described above, and the result "
                f"<code>&lt;name&gt;</code>, {tag}")
    return (f"<p>Objects created: the spreadsheet rows, {made}. They are plain "
            "FreeCAD objects: the saved file does not need primlib.</p>")


def render(key, cls):
    doc = App.newDocument(f"docs_{key}")
    sheet = parameter_sheet(doc)
    env = cls.bind(sheet)
    doc.recompute()
    ev = lambda e: value(sheet, expand(e, env))  # noqa: E731

    desc = "".join(f"<p>{prose(par)}</p>"
                   for par in (cls.intro or inspect.getdoc(cls)).split("\n\n"))
    body = [f"<h1>{esc(cls.title)}</h1>",
            f"<p class=\"sub\"><code>primlib/primitives/{key}.py</code> · "
            f"class <code>{cls.__name__}</code> · "
            f"<a href=\"../../index.html\">all primitives</a></p>", desc]

    shape = None
    if not issubclass(cls, Revolved):
        shape = cls.build(doc, "Part", sheet, env)
        doc.recompute()
        shape = shape.Shape
        if cls.views:
            body.append(views_section(cls, env, sheet, shape))

    if cls.fixed:
        body.append("<h2>Fixed parameters</h2><p>These define the part. They aren't for "
                    "changing, and are read only on the sheet.</p>")
        body.append(table(("name", "value", "note"),
                          [(f"<code>{esc(n)}</code>", num(ev(n)), esc(note))
                           for n, _, note in cls.fixed], num_cols=(1,)))
        body.append("<h2>Variable parameters</h2>")
    else:
        body.append("<h2>Parameters</h2>")
    heading = {} if cls.fixed else {names[0]: h for h, names in cls.groups}
    rows = []
    for p in cls.params:
        if p.name in heading:
            rows.append((f"<b>{esc(heading[p.name])}</b>", "", ""))
        rows.append((f"<code>{esc(p.name)}</code>", f"<code>{esc(p.default)}</code>",
                     esc(p.note)))
    body.append(table(("name", "default", "note"), rows))

    # The drawing straight after the parameters it shows.
    if issubclass(cls, Revolved):
        body.append(profile_section(cls, env, sheet))
    else:
        body.append(shape_section(cls, env, sheet, shape))
        prims = available()
        for key_, note in cls.fits:
            body.append(slide_fit_section(cls, env, sheet, shape, key_, note, prims))

    if cls.derived and cls.derived_on_page:
        body.append("<h2>Derived values</h2><p>Expanded inline into the "
                    "object expressions; values shown at the defaults.</p>")
        body.append(table(("name", "expression", "value", "note"),
                          [(f"<code>{esc(n)}</code>",
                            f"<code>{esc(e)}</code>", num(ev(n)), esc(note))
                           for n, e, note in cls.derived], num_cols=(2,)))

    if cls.checks:
        body.append("<h2>Valid range</h2><p>Checked when the primitive is "
                    "built; later edits to the sheet are not checked.</p>")
        body.append(table(("must be > 0", "otherwise"),
                          [(check_expr(e), esc(m)) for e, m in cls.checks]))

    name = cls.__name__
    args = ", ".join(f"{p.name}={p.default!r}" for p in cls.params[:2])
    body.append("<h2>Use</h2>")
    body.append(f"""<pre><code>import primlib
# appended to the document's Params sheet under "{name}: {esc(cls.title)}",
# aliases {name}_{cls.params[0].name}, {name}_{cls.params[1].name}, ...
obj = primlib.make("{key}", doc, "{name}")
obj = primlib.make("{key}", doc, "{name}", {esc(args)})   # starting values

# into another sheet, or with plain shared aliases ({cls.params[0].name}, ...)
obj = primlib.make("{key}", doc, "{name}", sheet=sheet)
obj = primlib.make("{key}", doc, "{name}", prefix="")

# or drive params from expressions you already have
obj = primlib.make("{key}", doc, "{name}", sheet=sheet,
                 bind={{"{cls.params[0].name}": "MyAlias * 2"}})</code></pre>""")
    body.append(
        "<p>In the FreeCAD GUI: the <b>primlib</b> workbench has a button "
        f"for <b>{esc(cls.title)}</b>. Its parameters are appended to the "
        "document's <code>Params</code> sheet under a title row, or to the "
        "selected spreadsheet if one is selected.</p>"
        + objects_note(cls, key))
    App.closeDocument(doc.Name)
    return page(f"{cls.title} — primlib", "".join(body))


# ------------------------------------------------------------------ paths

PATH_G, PATH_E = "0.2", "0.5"   # the slot's clearance and the lead-in drawn on a path's page


def loops_svg(layers, window=None, width=640.0, notes=()):
    """Loops in (u, v), v up: `layers` of (loops, fill, stroke, dashed),
    drawn in order; a fill of "none" draws them as open lines. `window` (u0, u1, v0, v1) shows only
    that region, larger. `notes` are (u, v, text) labels."""
    pts = [p for loops, *_ in layers for loop in loops for p in loop]
    if window:
        u_lo, u_hi, v_lo, v_hi = window
    else:
        u_lo, u_hi = min(p[0] for p in pts), max(p[0] for p in pts)
        v_lo, v_hi = min(p[1] for p in pts), max(p[1] for p in pts)
    scale = min(width / (u_hi - u_lo), 0.8 * width / (v_hi - v_lo))
    pad = 16.0
    w, h = (u_hi - u_lo) * scale + 2 * pad, (v_hi - v_lo) * scale + 2 * pad

    def xy(p):
        return f"{pad + (p[0] - u_lo) * scale:.2f},{pad + (v_hi - p[1]) * scale:.2f}"

    clip = f"clip{next(_CLIPS)}"
    out = [f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" role="img">'
           f'<clipPath id="{clip}"><rect x="{pad / 2}" y="{pad / 2}" width="{w - pad:.2f}" '
           f'height="{h - pad:.2f}"/></clipPath><g clip-path="url(#{clip})">']
    for loops, fill, stroke, dashed in layers:
        end = "" if fill == "none" else " Z"
        d = " ".join("M " + " L ".join(xy(p) for p in loop) + end for loop in loops)
        dash = ' stroke-dasharray="4 3"' if dashed else ""
        out.append(f'<path d="{d}" fill="{fill}" fill-opacity="0.85" fill-rule="evenodd" '
                   f'stroke="{stroke}" stroke-width="1.3" stroke-linejoin="round"{dash}/>')
    for u, v, text in notes:
        x, y = (float(c) for c in xy((u, v)).split(","))
        out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="11" fill="var(--fg)">'
                   f'{esc(text)}</text>')
    out.append("</g></svg>")
    return "".join(out)


def _section(shape, x=0.5):
    """The (y, z) loops of `shape` cut at x."""
    return [[(y, z) for _, y, z in w.discretize(Deflection=0.002)]
            for w in shape.slice(App.Vector(1, 0, 0), x)]


def path_probe(cls, groove=False):
    """A primitive drawing path `cls` three ways, 1 thick along x, for
    its page: the outline (`_tongue`), its slot, grown by g (`_slot`),
    and a lead-in, the dovetail shrunk by e with its base kept (`_lead`)."""
    from primlib.core import Builder, Param, Primitive

    d = cls.declare(groove=groove)
    on = {"groove": groove}

    class Probe(Primitive):
        title = cls.title
        params = d.params + (Param("slot_g", PATH_G, "the slot's offset"),
                             Param("lead_e", PATH_E, "the lead-in's offset"))
        derived = d.derived
        checks = d.checks

        @classmethod
        def build(cls_, doc, name, sheet, env):
            b = Builder(doc, name, sheet, env)
            span = ("0", "1")
            return (b.prism("tongue", cls.points(**on), "yz", span),
                    b.prism("lead", cls.points("-lead_e", "0", **on), "yz", span),
                    b.prism("slot", cls.points("slot_g", **on), "yz", span))

    return Probe


class PathMismatch(Exception):
    pass


def _boundary_points(shape, x=0.5):
    return [(y, z) for loop in _section(shape, x) for y, z in loop]


def _measure(tongue, slot, lead, ev, groove):
    """What the solids measure, checked against the parameters: raises
    PathMismatch, so the page isn't written, if they disagree."""
    out = {}
    below = Part.makeBox(1, 400, 200, App.Vector(0, -200, -200))
    tip = tongue.common(below)
    out["width"] = tip.BoundBox.YLength
    out["depth"] = -tip.BoundBox.ZMin
    above = tongue.common(Part.makeBox(1, 400, 200, App.Vector(0, -200, 0))).BoundBox
    out["base_width"], out["base_height"] = above.YLength, above.ZMax
    out["radii"] = sorted({round(e.Curve.Radius, 6) for e in tongue.Edges
                           if isinstance(e.Curve, Part.Circle)})
    g, e = ev("slot_g"), ev("lead_e")
    slot_edges = Part.Compound(slot.slice(App.Vector(1, 0, 0), 0.5))
    tongue_edges = Part.Compound(tongue.slice(App.Vector(1, 0, 0), 0.5))
    vertex = lambda y, z: Part.Vertex(App.Vector(0.5, y, z))  # noqa: E731
    gaps = [slot_edges.distToShape(vertex(y, z))[0] for y, z in _boundary_points(tongue)]
    leads = [tongue_edges.distToShape(vertex(y, z))[0]
             for y, z in _boundary_points(lead) if z < -1]
    out["gap"] = (min(gaps), max(gaps), sum(abs(x - g) < 1e-5 for x in gaps) / len(gaps))
    out["lead"] = (min(leads), max(leads), sum(abs(x - e) < 1e-5 for x in leads) / len(leads))

    wrong = []
    for n in ("width", "depth", "base_width", "base_height"):
        if abs(out[n] - ev(n)) > 1e-5:
            wrong.append(f"{n} measures {out[n]:.6f}, not {ev(n)}")
    for n in ("tip_radius", "root_radius"):
        if ev(n) > 0 and not any(abs(r - ev(n)) < 1e-5 for r in out["radii"]):
            wrong.append(f"no round of {n} {ev(n)}")
    # every face of the tongue is g from the slot; with a groove's sharp
    # corners, the slot is further off at a few points, never nearer
    lo, hi, share = out["gap"]
    if abs(lo - g) > 1e-5 or share < (0.9 if groove else 0.999) or (not groove and abs(hi - g) > 1e-5):
        wrong.append(f"the slot is {lo:.6f} to {hi:.6f} off the tongue, not {g}")
    lo, hi, share = out["lead"]
    if abs(lo - e) > 1e-5 or share < 0.9:
        wrong.append(f"the lead-in is {lo:.6f} to {hi:.6f} inside the tongue, not {e}")
    if wrong:
        raise PathMismatch("; ".join(wrong))
    return out


def _vertex_table(cls, groove):
    pts = cls.points("g", "f", "w", groove)
    labels = (["left root", "left tip"]
              + (["groove, left foot", "groove, left top", "groove, right top",
                  "groove, right foot"] if groove else [])
              + ["right tip", "right root", "base, right foot", "base, right top",
                 "base, left top", "base, left foot"])
    return table(("", "point", "u", "v", "round"),
                 [(str(i), esc(lab), f"<code>{esc(p[0])}</code>", f"<code>{esc(p[1])}</code>",
                   f"<code>{esc(p[2])}</code>" if len(p) > 2 else "sharp")
                  for i, (lab, p) in enumerate(zip(labels, pts))])


def render_path(key, cls):
    doc = App.newDocument(f"docs_path_{key}")
    sheet = parameter_sheet(doc)
    every = {o: True for o in cls.options}
    variants = {"plain": {}}
    if "groove" in cls.options:
        variants["groove"] = {"groove": True}
    shapes, env = {}, {}
    for v, on in variants.items():
        probe = path_probe(cls, **on)
        env[v] = probe.bind(sheet, prefix="" if v == "plain" else f"{v}_")
        doc.recompute()
        objs = probe.build(doc, v.capitalize(), sheet, env[v])
        doc.recompute()
        shapes[v] = [o.Shape.copy() for o in objs]
    ev = lambda e, v="plain": value(sheet, expand(e, env[v]))  # noqa: E731
    measured = {v: _measure(sh[0], sh[2], sh[1], (lambda e, v=v: ev(e, v)),
                            variants[v].get("groove", False))
                for v, sh in shapes.items()}
    d = cls.declare(**every)

    desc = "".join(f"<p>{prose(par)}</p>"
                   for par in (cls.intro or inspect.getdoc(cls)).split("\n\n"))
    users = [k for k, c in available().items()
             if f"primlib.paths.{key}" in open(inspect.getfile(c)).read()]
    status = (f"Used by {', '.join(f'<code>{u}</code>' for u in users)}." if users else
              "Designed: no primitive draws it yet. <code>tests/test_path.py</code> holds it, "
              "base included, to the outlines <code>rail15</code>, <code>topeak_rail</code> "
              "and their housings draw today, number for number, with lead-ins, offsets and "
              "clearances.")
    body = [f"<h1>{esc(cls.title)} path</h1>",
            f"<p class=\"sub\"><code>primlib/paths/{key}.py</code> · class "
            f"<code>{cls.__name__}</code> · <a href=\"../../index.html\">all primitives "
            f"and paths</a></p>", desc, f"<p><strong>Status:</strong> {status}</p>"]

    body.append("<h2>Parameters</h2><p>A primitive takes these into its own names: as "
                "its parameters, or as fixed parameters where they define the part. The "
                "profile's defaults are the 15 mm rail's.</p>")
    body.append(table(("name", "default", "note"),
                      [(f"<code>{esc(p.name)}</code>", f"<code>{esc(p.default)}</code>",
                        esc(p.note)) for p in cls.params]))
    for opt, (ps, _, _) in cls.options.items():
        body.append(f"<h3>Option <code>{esc(opt)}</code></h3>")
        body.append(table(("name", "default", "note"),
                          [(f"<code>{esc(p.name)}</code>", f"<code>{esc(p.default)}</code>",
                            esc(p.note)) for p in ps]))

    # The outline, dimensioned: a front view of the tongue, 1 thick.
    pt = lambda p, v="plain": tuple(ev(c, v) if isinstance(c, str) else c for c in p)  # noqa: E731
    dims = [("front", "u", pt(("0", "-width / 2", "tip_radius - depth")),
             pt(("0", "width / 2", "tip_radius - depth")), 1, "width"),
            ("front", "v", pt(("0", "-root_hw", "-depth")), pt(("0", "-root_hw", "0")), 1,
             "depth"),
            ("front", "angle", pt(("0", "-tip_hw", "-depth")),
             (pt(("0", "3 - tip_hw", "-depth")), pt(("0", "-root_hw", "0"))), 1.5, "angle"),
            ("front", "a", pt(("0", "width / 2 - tip_radius", "tip_radius - depth")),
             pt(("0", "width / 2", "tip_radius - depth")), 0, "tip_radius"),
            ("front", "a", pt(("0", "root_hw + t_root", "-root_radius")),
             pt(("0", "root_hw + t_root - root_radius", "-root_radius")), 0, "root_radius"),
            ("front", "u", pt(("0", "-base_width / 2", "base_height")),
             pt(("0", "base_width / 2", "base_height")), -1, "base_width"),
            ("front", "v", pt(("0", "base_width / 2", "0")),
             pt(("0", "base_width / 2", "base_height")), -1, "base_height")]
    tongue = shapes["plain"][0]
    m = measured["plain"]
    body.append("<h2>Outline</h2>")
    body.append(f"<figure>{views_svg(tongue, dims, max_height=420, only=('front',))}"
                "<figcaption>The outline at the defaults, seen along its normal: u across, "
                "v up, the root line at v = 0, the base above it. Dimensions in mm."
                "</figcaption></figure>")
    body.append(table(("measured on the solid", "value", "parameter"), [
        ("width, between vertical tangents to the tip rounds", num(m["width"]),
         f"<code>width</code> {num(ev('width'))}"),
        ("depth, root line to tip face", num(m["depth"]), f"<code>depth</code> {num(ev('depth'))}"),
        ("rounds", ", ".join(num(r) for r in m["radii"]),
         f"<code>tip_radius</code> {num(ev('tip_radius'))}, <code>root_radius</code> "
         f"{num(ev('root_radius'))}"),
        ("base width", num(m["base_width"]), f"<code>base_width</code> {num(ev('base_width'))}"),
        ("base height, up from the root line", num(m["base_height"]),
         f"<code>base_height</code> {num(ev('base_height'))}")], num_cols=(1,)))

    # Offsets: the tongue, its slot at g, its lead-in at -e.
    t, lead, slot = shapes["plain"]
    layers = [(_section(slot), "transparent", "var(--mate-edge)", False),
              (_section(t), "transparent", "var(--edge)", False),
              (_section(lead), "transparent", "var(--axis)", True)]
    x_r, v_t = ev("tip_hw"), -ev("depth")
    window = (ev("root_hw") - 1.6, ev("base_width / 2 + slot_g") + 0.5, v_t - 0.7,
              ev("base_height + slot_g") + 0.4)
    body.append("<h2>Offsets</h2><p>Each mate is the same outline offset: "
                "<code>points(grow, face)</code>. Drawn here: the tongue (blue, "
                "<code>grow</code> 0); its slot (orange), the tongue grown by a "
                f"clearance g = {num(ev('slot_g'))} normal to every face, base and all "
                "(<code>grow</code> = <code>face</code> = g); and a lead-in (red, dashed), "
                f"the dovetail shrunk by e = {num(ev('lead_e'))} with its base kept "
                "(<code>grow</code> = -e, <code>face</code> 0).</p>")
    lip = ev("root_radius - slot_g")
    body.append(f"<figure>{loops_svg(layers, width=640)}<figcaption>The three outlines, whole."
                f"</figcaption></figure><p></p><figure>"
                f"{loops_svg(layers, window=window, width=420)}<figcaption>The right side, "
                "larger: the slot's tip round is concentric with the tongue's, "
                "<code>tip_radius</code> + g; its root corner is <code>root_radius</code> "
                f"- g, {'here 0, so sharp' if lip <= 1e-9 else num(lip)}; its base is g "
                "further out and up.</figcaption></figure>")
    lo, hi, _ = m["gap"]
    llo, lhi, _ = m["lead"]
    body.append(table(("measured on the solids", "value", "should be"), [
        ("gap, tongue to slot, at every point of the tongue", f"{num(lo)} to {num(hi)}",
         f"g = {num(ev('slot_g'))}"),
        ("lead-in inside the tongue, flanks and tip face", f"{num(llo)} to {num(lhi)}",
         f"e = {num(ev('lead_e'))}")], num_cols=(1,)))

    if "groove" in cls.options:
        gdims = [("front", "u", pt(("0", "-groove_width / 2", "-depth"), "groove"),
                  pt(("0", "groove_width / 2", "-depth"), "groove"), 1, "groove_width"),
                 ("front", "v", pt(("0", "groove_width / 2", "-depth"), "groove"),
                  pt(("0", "groove_width / 2 - groove_depth / tan(groove_angle)",
                         "-depth + groove_depth"), "groove"), -1, "groove_depth"),
                 ("front", "angle", pt(("0", "groove_width / 2", "-depth"), "groove"),
                  (pt(("0", "groove_width / 2 - 2", "-depth"), "groove"),
                   pt(("0", "groove_width / 2 - groove_depth / tan(groove_angle)",
                       "-depth + groove_depth"), "groove")), 1, "groove_angle")]
        gt, glead, gslot = shapes["groove"]
        glo, ghi, _ = measured["groove"]["gap"]
        body.append("<h2>Option <code>groove</code></h2>")
        body.append(f"<figure>{views_svg(gt, gdims, max_height=420, only=('front',))}"
                    "<figcaption>With a centre groove in the tip face, at the defaults. "
                    "Dimensions in mm.</figcaption></figure>")
        gl = [(_section(gslot), "transparent", "var(--mate-edge)", False),
              (_section(gt), "transparent", "var(--edge)", False),
              (_section(glead), "transparent", "var(--axis)", "groove")]
        gw = ev("groove_width / 2", "groove")
        gwin = (-gw - 1.5, gw + 1.5, v_t - 0.8, v_t + ev("groove_depth", "groove") + 0.6)
        body.append(f"<p></p><figure>{loops_svg(gl, window=gwin, width=640)}"
                    "<figcaption>The groove offset with the rest: the slot's guide is the "
                    f"groove shrunk by g; measured {num(glo)} to {num(ghi)} from the tongue "
                    "(its sharp corners stand further off at a few points, never nearer)."
                    "</figcaption></figure>")

    body.append("<h2>The points</h2><p><code>points(grow=g, face=f, widen=w, "
                "groove=True)</code>, the closed outline from the left root corner "
                "anticlockwise. A round of 0 or less is a sharp corner. "
                "<code>face</code> left out is <code>grow</code>; <code>widen</code> is a "
                "printer's width offset, half each side, and leaves the groove alone.</p>")
    body.append(_vertex_table(cls, "groove" in cls.options))
    body.append("<h2>Derived values</h2><p>Worked in from the width; values at the "
                "defaults.</p>")
    body.append(table(("name", "expression", "value", "note"),
                      [(f"<code>{esc(n)}</code>", f"<code>{esc(e)}</code>", num(ev(n)),
                        esc(note)) for n, e, note in d.derived], num_cols=(2,)))
    body.append("<h2>Valid range</h2><p>A primitive drawing the path takes these checks "
                "into its own (an option's only with it on). Its offsets have "
                "limits of their own: a lead-in e must be less than <code>tip_radius</code>, "
                "and a slot's root round goes sharp once g reaches "
                "<code>root_radius</code>.</p>")
    body.append(table(("must be > 0", "otherwise"),
                      [(check_expr(e), esc(msg)) for e, msg in d.checks]))
    body.append("<h2>Use</h2>")
    body.append(f"""<pre><code>from primlib.core import Builder, Primitive
from primlib.paths.{key} import {cls.__name__}

D = {cls.__name__}.declare()           # or declare(groove=True)

class Rail(Primitive):
    params = D.params + (...)        # or fixed = ..., to hold them
    derived = D.derived + (...)
    checks = D.checks + (...)

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        pts = {cls.__name__}.points()                     # the tongue and its base
        # its slot: {cls.__name__}.points(grow="clearance")
        # lead-in sections: {cls.__name__}.points(grow="-end_taper", face="0")
        return b.finish(b.prism(None, pts, "yz", ("0", "length")))</code></pre>""")
    body.append("<p>A path makes no object of its own: the primitive's prism, loft or "
                "revolve sketch holds its points, bound to the sheet as any other.</p>")
    App.closeDocument(doc.Name)
    return page(f"{cls.title} path — primlib", "".join(body))

# The warning at the top of index.html, the site's front page.
CAUTION = ('<p style="border:2px solid #c0392b;border-radius:6px;background:#fdecea;color:#7b1d14;padding:0.8em 1em"><strong>All the code in this repository was generated by Claude, a'
           'n AI from Anthropic, and has not been checked by a person.</strong> It may have bugs or not do what it says. Read it before you rely on it, and use it at your own risk.</p>')


def render_index(prims, paths=None):
    rows = [(f"<a href=\"primlib/primitives/{k}.html\">{esc(c.title)}</a>",
             f"<code>{k}</code>",
             esc(" ".join(inspect.getdoc(c).split("\n\n")[0].split())))
            for k, c in prims.items()]
    out = ("<h1>primlib primitives</h1><p class=\"sub\">Spreadsheet-driven "
           "parametric primitives for FreeCAD.</p>" + CAUTION
           + table(("primitive", "key", "description"), rows))
    if paths:
        out += ("<h2>Paths</h2><p>Outlines that more than one primitive draws, "
                "declared once.</p>" + table(("path", "key", "description"), [
                    (f"<a href=\"primlib/paths/{k}.html\">{esc(c.title)}</a>",
                     f"<code>{k}</code>",
                     esc(" ".join(inspect.getdoc(c).split("\n\n")[0].split())))
                    for k, c in paths.items()]))
    return page("primlib primitives", out)


if __name__ == "__main__" or (len(sys.argv) > 1
                              and sys.argv[1].endswith("make_docs.py")):
    prims = available()
    for key, cls in prims.items():
        path = os.path.join(ROOT, "primlib", "primitives", f"{key}.html")
        with open(path, "w") as fh:
            fh.write(render(key, cls))
        print(f"wrote {path}")
    from primlib.paths import available as available_paths
    paths = available_paths()
    for key, cls in paths.items():
        path = os.path.join(ROOT, "primlib", "paths", f"{key}.html")
        with open(path, "w") as fh:
            fh.write(render_path(key, cls))
        print(f"wrote {path}")
    with open(os.path.join(ROOT, "index.html"), "w") as fh:
        fh.write(render_index(prims, paths))
    print(f"wrote {os.path.join(ROOT, 'index.html')}")
