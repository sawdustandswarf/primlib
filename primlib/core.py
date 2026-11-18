r"""
================================================================================
CORE -- the Primitive base class and spreadsheet-driven solids of revolution
================================================================================

Every primlib primitive is a part whose dimensions are FreeCAD *expressions*
over spreadsheet aliases. Primitive holds what all of them share --
parameters, derived values, checks, the sheet rows -- and calls the
subclass's build() to create the geometry.

Most primitives are solids of revolution (Revolved): the half-profile, a
closed polyline in the (r, z) half-plane, is written as expressions.
Building one:

  1. resolves each parameter to an expression (a sheet alias, or a formula
     the caller binds it to);
  2. expands the primitive's derived values and wall points into plain
     expressions over those parameters;
  3. draws the profile as a Sketcher sketch in the XZ plane, pinning every
     vertex with DistanceX / DistanceY constraints `r{i}` / `z{i}` bound to
     its expressions -- the sketch is fully constrained by the sheet;
  4. sweeps the sketch 360 degrees about z with a Part::Revolution.

The result is native FreeCAD (sheet + sketch + revolution): a saved file
opens and recomputes without primlib installed. Edit a cell, recompute,
and the solid follows.

Writing a primitive
-------------------
Subclass Revolved (a solid of revolution, give walls()) or Primitive (any
other shape, give build()) in its own module under primlib/primitives/ and
declare:

  title    human name for docs and the toolbar
  params   tuple of Param(name, default, note). `default` is a value
           ("6", "45 deg") or a formula over earlier params ("=diam / 2").
  derived  tuple of (name, expression, note): intermediate values over
           params and earlier derived names, expanded inline at build.
  fixed    optional tuple of (name, value, note): the part's fixed parameters,
           which define it and aren't for changing. Written to the sheet above
           the params under "Fixed (read only)", and the model reads them
           from there, so don't overtype them. Listed apart on the docs page.
  derived_on_page
           False leaves the derived table off the docs page, for a part
           whose derived values are only working.
  checks   tuple of (expression, message): each must evaluate > 0 or the
           build is refused with `message`.
  walls(x) Revolved: return (outer, inner), lists of (r, z) expressions
           bottom to top, `inner` None for a solid body. `x.<name>` is
           the expression for a param or derived value -- write
           f"{x.height} - {x.rim_h}".
  build(doc, name, sheet, env)
           Primitive: create the objects and return the result object
           named `name`. `env` maps param / derived names to expressions;
           bind_props() binds object properties to them, and Builder makes
           bound boxes, cylinders, cones, slots, sketch prisms (vertices
           optionally rounded), ruled lofts between such polygons,
           partial revolutions and lofts about the z axis, spheres, arrays
           and booleans from expressions over
           the primitive's names.
  body(b)  Machined (a body with features cut from it): return (body,
           [tools]) made with Builder `b`; build() cuts them. An assembly
           can call body() and fuse more on before the cut.
  groups   optional tuple of (heading, param names): sub-headings for a
           long parameter list, in the sheet and on the docs page.
           grouped() derives params and groups from part primitives.
  variants optional tuple of (label, {param: value}): documentation only,
           the page draws the profile once per variant.
  section_y
           optional expression, or tuple of them: documentation only, for
           a non-Revolved primitive the y of each section plane (default:
           the middle).
  mates    optional tuple of Mate(key, bind, note, details, fit):
           primitives this one fits with, `bind` mapping the mate's params
           to expressions over this one's params and derived values,
           `details` a tuple of (mate vertex index, label) to enlarge, and
           `fit` "outside" (the mate sits in a cavity of this part and
           must not overlap it) or "inside" (this part is an envelope the
           mate must lie within). Documentation only: the page draws each
           mate in place, tabulates the clearance and adds a detail view
           at the minimum clearance and at each listed vertex.
  fits     optional tuple of (key, note): non-Revolved primitives built
           along x that this one slides into or over, sharing its param
           names. Documentation only: the page builds the mate with this
           one's values at the same origin, draws the pair in section
           across x, tabulates the clearance and adds a detail view at the
           minimum clearance.

The class docstring is the primitive's description in its HTML page;
make_docs.py renders the page from these declarations.

Walls
-----
With no inner wall the profile closes along the axis (a solid body); with
one it runs up the outer wall and back down the inner (a hollow body).
Adjacent points with the same expression are merged, so walls may share
end points (a sharp rim) without zero-length edges.

Expressions
-----------
Bare aliases of the target sheet are qualified automatically (`pd` ->
`Params.pd`); expressions may also name other sheets explicitly. Avoid
the alias `h`: the expression engine reads a bare `h` as the hour unit.
================================================================================
"""

import math
import re
from collections import namedtuple
from types import SimpleNamespace

try:
    import FreeCAD as App
    import Part
    import Sketcher
except ImportError:  # plain Python: recording and export only (primlib/targets/record.py)
    App = Part = Sketcher = None

_IDENT = re.compile(r"(?<![\w.])([A-Za-z_]\w*)(?![\w.]|\s*\()")

Param = namedtuple("Param", "name default note")
Mate = namedtuple("Mate", "key bind note details fit",
                  defaults=((), "outside"))


def _hide(obj):
    """Hide a construction object when a GUI is present (headless has no ViewObject)."""
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.Visibility = False


# ------------------------------------------------------------------ sheets

SHEET = "Params"   # the document-wide parameter sheet primitives default to


def parameter_sheet(doc, name=SHEET, label="Parameters"):
    """New spreadsheet with an alias / value / note header row."""
    sheet = doc.addObject("Spreadsheet::Sheet", name)
    sheet.Label = label
    sheet.set("A1", "alias")
    sheet.set("B1", "value")
    sheet.set("C1", "note")
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 170)
    sheet.setColumnWidth("C", 300)
    return sheet


def document_sheet(doc):
    """The document's shared `Params` sheet, created on first use."""
    return doc.getObject(SHEET) or parameter_sheet(doc)


def next_row(sheet):
    """First row below every used cell."""
    rows = [int(re.sub(r"[A-Z]+", "", cell)) for cell in sheet.getUsedCells()]
    return max(rows, default=0) + 1


def add_section(sheet, title, style="bold"):
    """Append a title row (bold; italic for a sub-heading), a blank row
    above it unless at the top."""
    row = next_row(sheet)
    if row > 2:
        row += 1
    sheet.set(f"A{row}", title)
    sheet.setStyle(f"A{row}", style, "add")


def add_parameter(sheet, alias, content, note=""):
    """Append an aliased row (alias, content, note) below the used cells."""
    row = next_row(sheet)
    sheet.set(f"A{row}", alias)
    sheet.set(f"B{row}", str(content))
    sheet.setAlias(f"B{row}", alias)
    sheet.set(f"C{row}", note)
    return alias


def qualify(sheet, expr):
    """Prefix every bare alias of `sheet` in `expr` with the sheet's name.

    "pd / 2" -> "Params.pd / 2". Function names, units and already
    qualified references are left alone.
    """
    def sub(match):
        word = match.group(1)
        if sheet.getCellFromAlias(word):
            return f"{sheet.Name}.{word}"
        return word
    return _IDENT.sub(sub, str(expr))


def expand(expr, env):
    """Replace every name of `env` in `expr` by its parenthesised expression.

    A conditional gets a unary plus as well: FreeCAD (1.1) drops the
    parentheses around a conditional used in a comparison when it saves
    the expression, so "(c ? a : b) == 0 ? x : y" reloads as
    "c ? a : (b == 0 ? x : y)". "+(c ? a : b)" keeps them.
    """
    def sub(match):
        word = match.group(1)
        if word not in env:
            return word
        e = str(env[word])
        return f"+({e})" if "?" in e else f"({e})"
    return _IDENT.sub(sub, str(expr))


def bind_props(obj, sheet, props):
    """Bind each property of `obj` (incl. sub-properties such as
    "Placement.Base.z") to an expression over `sheet`'s aliases."""
    for prop, expr in props.items():
        obj.setExpression(prop, qualify(sheet, expr))


def _no_sheet(expr):
    """A recorded build (no sheet) can't know a value while building."""
    from primlib.targets.record import NotRecordable
    return NotRecordable(f"needs the value of {expr} while building")


def value(sheet, expr):
    """Numeric value (mm, deg, ...) of an expression over `sheet`'s aliases."""
    if sheet is None:
        raise _no_sheet(expr)
    val = sheet.evalExpression(qualify(sheet, expr))
    return float(getattr(val, "Value", val))


def value_str(sheet, expr):
    """Text value of an expression over `sheet`'s aliases (a string cell)."""
    if sheet is None:
        raise _no_sheet(expr)
    return sheet.evalExpression(qualify(sheet, expr))


# ------------------------------------------------------------------ profiles

def _key(pt):
    return tuple(str(e) for e in pt)


def wall_profile(outer, inner=None):
    """Closed (r, z) profile from walls, shared end points merged."""
    if inner is None:
        pts = [("0", outer[0][1])] + list(outer) + [("0", outer[-1][1])]
    else:
        pts = list(outer) + list(reversed(inner))
    merged = []
    for pt in pts:
        if not merged or _key(pt) != _key(merged[-1]):
            merged.append(pt)
    if len(merged) > 1 and _key(merged[0]) == _key(merged[-1]):
        merged.pop()
    return merged


def pinned_sketch(doc, name, sheet, profile, placement, labels=("r", "z")):
    """Closed polygon sketch, every vertex pinned to the spreadsheet.

    `profile` is a list of (a, b) expressions in the sketch's own plane;
    vertex i is held by DistanceX / DistanceY constraints named
    `{labels[0]}{i}` / `{labels[1]}{i}`, bound to them. A vertex given as
    (a, b, r) is rounded by a tangent arc of radius r instead (see
    _round_corners). Returns the sketch, or None (with a console error)
    when two neighbouring vertices coincide or the sketch fails to solve.
    """
    count = len(profile)
    radii = [qualify(sheet, v[2]) if len(v) > 2 else None for v in profile]
    exprs = [(qualify(sheet, v[0]), qualify(sheet, v[1])) for v in profile]
    pts = [App.Vector(value(sheet, a), value(sheet, b), 0.0)
           for a, b in exprs]
    for i in range(count):
        if (pts[i] - pts[(i + 1) % count]).Length < 1e-6:
            App.Console.PrintError(
                f"Error: {name}: profile vertices {i} and {(i + 1) % count} "
                f"coincide at {labels[0]}={pts[i].x:.4g}, "
                f"{labels[1]}={pts[i].y:.4g}.\n")
            return None

    sketch = doc.addObject("Sketcher::SketchObject", name)
    sketch.Placement = placement
    rounded = any(radii)
    for i in range(count):
        sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % count]),
                           rounded)
    # Close the wire: end of segment i to the start of segment i + 1.
    for i in range(count):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", i, 2, (i + 1) % count, 1))
    # Pin vertex i (start of segment i) to the spreadsheet.
    la, lb = labels
    for i, (a, b) in enumerate(exprs):
        ca = sketch.addConstraint(
            Sketcher.Constraint("DistanceX", i, 1, pts[i].x))
        cb = sketch.addConstraint(
            Sketcher.Constraint("DistanceY", i, 1, pts[i].y))
        sketch.renameConstraint(ca, f"{la}{i}")
        sketch.renameConstraint(cb, f"{lb}{i}")
        sketch.setExpression(f"Constraints.{la}{i}", a)
        sketch.setExpression(f"Constraints.{lb}{i}", b)
    if rounded and not _round_corners(sketch, name, sheet, pts, radii):
        return None

    if sketch.solve() != 0:
        App.Console.PrintError(f"Error: {name}: profile sketch failed to solve.\n")
        return None
    return sketch


def _round_corners(sketch, name, sheet, pts, radii):
    """The real edges of a pinned polygon with rounded vertices.

    The pinned polygon (geometry 0 .. n-1) is construction geometry here.
    Each real line lies on its construction edge: an end at a plain vertex
    is coincident with it, an end at a rounded vertex slides along the
    edge and meets the vertex's arc, which is tangent to both edges, its
    radius held by the constraint `fillet{i}` bound to r. False (with a
    console error) if a radius is not positive or the rounds of an edge
    do not fit on it.
    """
    count = len(pts)
    t, arcs = [0.0] * count, [None] * count
    for k, r in enumerate(radii):
        if r is None:
            continue
        rv = value(sheet, r)
        u = pts[k] - pts[k - 1]
        w = pts[(k + 1) % count] - pts[k]
        u.normalize()
        w.normalize()
        turn = u.cross(w).z
        if rv <= 0 or abs(turn) < 1e-9:
            App.Console.PrintError(f"Error: {name}: vertex {k} can't be rounded "
                                   f"(radius {rv:.4g}).\n")
            return False
        # Tangent length r / tan(half the corner angle).
        half = math.acos(max(-1.0, min(1.0, -u.dot(w)))) / 2
        t[k] = rv / math.tan(half)
        p1, p2 = pts[k] - u * t[k], pts[k] + w * t[k]
        left = turn > 0
        n = App.Vector(-u.y, u.x, 0) if left else App.Vector(u.y, -u.x, 0)
        centre = p1 + n * rv
        a, b = (p1, p2) if left else (p2, p1)       # arcs run anticlockwise
        start = math.atan2(a.y - centre.y, a.x - centre.x)
        end = math.atan2(b.y - centre.y, b.x - centre.x)
        if end <= start:
            end += 2 * math.pi
        arcs[k] = (Part.ArcOfCircle(Part.Circle(centre, App.Vector(0, 0, 1), rv),
                                    start, end), left, p1, p2)
    for i in range(count):
        j = (i + 1) % count
        if t[i] + t[j] >= (pts[j] - pts[i]).Length - 1e-6:
            App.Console.PrintError(f"Error: {name}: the rounds at vertices {i} "
                                   f"and {j} don't fit on the edge between.\n")
            return False

    lines = []
    for i in range(count):
        j = (i + 1) % count
        a = arcs[i][3] if arcs[i] else pts[i]
        b = arcs[j][2] if arcs[j] else pts[j]
        lines.append(sketch.addGeometry(Part.LineSegment(a, b), False))
    for i, line in enumerate(lines):
        j = (i + 1) % count
        for pos, k in ((1, i), (2, j)):
            if arcs[k] is None:
                sketch.addConstraint(Sketcher.Constraint("Coincident", line, pos, k, 1))
            else:
                sketch.addConstraint(Sketcher.Constraint("PointOnObject", line, pos, i))
    for k, arc in enumerate(arcs):
        if arc is None:
            continue
        geo, left, _, _ = arc
        g = sketch.addGeometry(geo, False)
        into, out = (1, 2) if left else (2, 1)
        sketch.addConstraint(Sketcher.Constraint("Tangent", lines[k - 1], 2, g, into))
        sketch.addConstraint(Sketcher.Constraint("Tangent", g, out, lines[k], 1))
        c = sketch.addConstraint(Sketcher.Constraint("Radius", g, geo.Radius))
        sketch.renameConstraint(c, f"fillet{k}")
        sketch.setExpression(f"Constraints.fillet{k}", radii[k])
    return True


def revolved(doc, name, sheet, profile):
    """Solid of revolution from a closed profile of (r, z) expressions.

    Builds `{name}_sketch` in the XZ plane, every vertex pinned by `r{i}` /
    `z{i}` constraints bound to its expressions, and revolves it 360 degrees
    about the z axis as the Part::Revolution `name`. Returns the revolution,
    or None (with a console error) when the profile is degenerate or the
    sketch fails to solve.
    """
    # Local (u, v) -> global (u, 0, v): rotate the local XY plane onto XZ.
    sketch = pinned_sketch(doc, f"{name}_sketch", sheet, profile, App.Placement(
        App.Vector(0.0, 0.0, 0.0), App.Rotation(App.Vector(1, 0, 0), 90.0)))
    if sketch is None:
        return None

    rev = doc.addObject("Part::Revolution", name)
    rev.Source = sketch
    rev.Axis = App.Vector(0.0, 0.0, 1.0)
    rev.Angle = 360.0
    rev.Solid = True
    _hide(sketch)
    return rev


# ------------------------------------------------------------------ builder

class Builder:
    """Where a primitive's build() makes its shapes.

    `Builder(doc, name, sheet, env)` gives the target `doc` asks for: FreeCAD
    objects for a FreeCAD document (primlib/targets/freecad.py), or the tree of
    operations, kept, for a Recording (primlib/targets/record.py). Both take
    the same operations (box, cylinder, revolve, array, cut, ...), with every
    size an expression over the primitive's names.
    """

    def __new__(cls, doc, name, sheet, env):
        if cls is Builder:
            from primlib.targets import target_for
            cls = target_for(doc)
        return super().__new__(cls)

    def part(self, cls, suffix, bind=None):
        """Primitive `cls` built here as `{name}_{suffix}`, its params bound
        through `bind` to this one's names (default: each to the same name;
        see Primitive.bound)."""
        obj = cls.build_bound(self.doc, f"{self.name}_{suffix}", self.sheet, self.env, bind)
        if obj is not None:
            self.made.append(obj)
        return obj


# ------------------------------------------------------------------ declarations

def merge(*decls):
    """Union by name of params (Param) or derived ((name, expr, note))
    tuples, first occurrence wins. Derived values of the same name must
    agree, or composing them would silently change one part."""
    out, seen = [], {}
    for decl in decls:
        for item in decl:
            name = item[0]
            if name in seen:
                if isinstance(item, tuple) and not isinstance(item, Param) \
                        and item[1] != seen[name][1]:
                    raise ValueError(f"derived {name!r} differs: "
                                     f"{seen[name][1]!r} / {item[1]!r}")
                continue
            seen[name] = item
            out.append(item)
    return tuple(out)


def grouped(*sections):
    """(params, groups) from (heading, params) sections: the params merged
    by name, each under the heading of the first section that lists it."""
    params = merge(*(p for _, p in sections))
    groups, seen = [], set()
    for heading, ps in sections:
        names = tuple(p.name for p in ps if p.name not in seen)
        seen.update(names)
        if names:
            groups.append((heading, names))
    return params, tuple(groups)


# ------------------------------------------------------------------ primitives

class Primitive:
    """Base class: subclasses declare params, derived, checks and build()."""

    title = ""
    params = ()
    derived = ()
    checks = ()
    groups = ()
    mates = ()
    variants = ()
    section_y = None
    front_view = False  # docs page: also draw the whole shape seen from +x, z up
    front_dims = ()     # ... with dimensions (axis "y" or "z", lo, hi, row from 1)
    summary = ()        # (expr, note) printed to the console after a build
    fixed = ()          # (name, value, note): fixed parameters, read only on the sheet
    derived_on_page = True  # docs page: show the derived table
    intro = None        # docs page: text in place of the docstring
    views = ()          # docs page: third-angle views, dimensioned (see make_docs.views_svg)
    fits = ()           # docs page: (key, note) of primitives this one slides into or over
    freecad_only = None  # why build() makes FreeCAD objects itself, so can't be recorded

    @classmethod
    def key(cls):
        """Registry key: the defining module's name (pin, sleeve, ...)."""
        return cls.__module__.rsplit(".", 1)[-1]

    @classmethod
    def build(cls, doc, name, sheet, env):
        """Create the geometry; return the result object (or None)."""
        raise NotImplementedError

    # -- using a primitive inside another one ------------------------------
    # `bind` maps every param of this (inner) primitive to an expression over
    # the outer primitive's param / derived names, e.g. {"height": "pitch"}.

    @classmethod
    def nested(cls, bind):
        """This primitive's param and derived names as expressions over the
        outer primitive's names."""
        env = {p.name: str(bind[p.name]) for p in cls.params}
        for name, expr, _ in cls.fixed + cls.derived:
            env[name] = expand(expr, env)
        return env

    @classmethod
    def nested_checks(cls, bind, guard=None):
        """This primitive's checks over the outer names, for the outer's
        `checks`; `guard` (an expression) limits them to when it is true."""
        env = cls.nested(bind)
        checks = []
        for expr, message in cls.checks:
            expr = expand(expr, env)
            if guard:
                expr = f"{guard} ? ({expr}) : 1"
            checks.append((expr, f"{cls.title.lower()}: {message}"))
        return tuple(checks)

    @classmethod
    def bound(cls, sheet, env, bind=None):
        """This primitive's env with its params bound through `bind` to the
        outer primitive's `env` (default: each param to the outer param of
        the same name) -- no sheet rows of its own."""
        bind = bind or {p.name: p.name for p in cls.params}
        bind = {k: expand(v, env) for k, v in bind.items()}
        if sheet is None:  # recorded: names only
            return cls.nested(bind)
        return cls.bind(sheet, bind=bind)

    @classmethod
    def build_bound(cls, doc, name, sheet, env, bind=None):
        """build() this primitive bound to the outer `env` (see bound())."""
        return cls.build(doc, name, sheet, cls.bound(sheet, env, bind))

    @classmethod
    def bind(cls, sheet, prefix="", bind=None, title=None, **values):
        """Resolve every param to an expression over `sheet`.

        Per param, in order: an expression given in `bind`; else an existing
        alias `{prefix}{name}` in the sheet (shared with other primitives);
        else a new aliased row holding `values[name]` or the default. New
        rows go at the bottom of the sheet under a `title` row (default: the
        primitive's title), written only if a row is added. Formula defaults
        are rewritten over the resolved params. Returns the environment of
        param and derived names -> expressions.
        """
        bind = bind or {}
        env = {}
        titled = False
        new = [p for p in cls.params if p.name not in bind
               and not sheet.getCellFromAlias(f"{prefix}{p.name}")]
        if cls.fixed and new:
            add_section(sheet, title or cls.title)
            titled = True
            add_section(sheet, "Fixed (read only)", style="italic")
            for name, expr, note in cls.fixed:
                if not sheet.getCellFromAlias(f"{prefix}{name}"):
                    add_parameter(sheet, f"{prefix}{name}", f"={expr}", note)
        group_of = {n: heading for heading, names in cls.groups for n in names}
        group = None
        for p in cls.params:
            alias = f"{prefix}{p.name}"
            if p.name in bind:
                env[p.name] = str(bind[p.name])
            elif sheet.getCellFromAlias(alias):
                env[p.name] = alias
            else:
                if not titled:
                    add_section(sheet, title or cls.title)
                    titled = True
                if group_of.get(p.name, group) != group:
                    group = group_of[p.name]
                    add_section(sheet, group, style="italic")
                content = str(values.get(p.name, p.default))
                if content.startswith("="):
                    content = "=" + expand(content[1:], env)
                env[p.name] = add_parameter(sheet, alias, content, p.note)
        for name, expr, _ in cls.fixed:
            alias = f"{prefix}{name}"
            env[name] = alias if sheet.getCellFromAlias(alias) else str(expr)
        for name, expr, _ in cls.derived:
            env[name] = expand(expr, env)
        return env

    @classmethod
    def make(cls, doc, name, sheet=None, prefix=None, bind=None, **values):
        """Build the primitive `name` into `doc`, driven by `sheet`.

        `sheet` defaults to the document's shared `Params` sheet. New params
        are appended to it as a section titled "{name}: {title}", aliased
        `{prefix}{param}`; `prefix` defaults to "{name}_" so every part has
        its own rows (pass "" to share aliases by plain name). Keyword
        `values` set the cells of newly added params; `bind` maps params to
        expressions instead (see bind()). Returns the result object (from
        build()), or None (with a console error) if a check fails -- the
        rows it added are removed again.
        """
        own_sheet = sheet is None and doc.getObject(SHEET) is None
        sheet = sheet or document_sheet(doc)
        if prefix is None:
            prefix = f"{name}_"
        first_row = next_row(sheet)
        env = cls.bind(sheet, prefix, bind, title=f"{name}: {cls.title}",
                       **values)
        doc.recompute()

        obj = None
        failed = [m for expr, m in cls.checks
                  if value(sheet, expand(expr, env)) <= 0]
        for message in failed:
            App.Console.PrintError(f"Error: {name}: {message}.\n")
        if not failed:
            obj = cls.build(doc, name, sheet, env)
        if obj is None:
            if own_sheet:
                doc.removeObject(sheet.Name)
            else:
                for row in range(first_row, next_row(sheet)):
                    for col in "ABC":
                        sheet.clear(f"{col}{row}")
                doc.recompute()
            return None
        obj.addProperty("App::PropertyString", "PrimlibPrimitive", "Primlib",
                        "primlib primitive this solid was built from")
        obj.PrimlibPrimitive = cls.key()
        for expr, note in cls.summary:
            App.Console.PrintMessage(
                f"{name}: {note}: {value(sheet, expand(expr, env)):.4g}\n")
        return obj


class Machined(Primitive):
    """A body with features cut from it: subclasses declare body() instead
    of build(). An assembly can call body() itself and fuse more onto the
    body before the cut, so the features go through everything."""

    @classmethod
    def body(cls, b):
        """Create the objects with Builder `b`; return (body, [tools])."""
        raise NotImplementedError

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        made = cls.body(b)
        if made is None:
            return None
        body, tools = made
        return b.finish(b.cut(None, body, tools))


class Revolved(Primitive):
    """A solid of revolution: subclasses declare walls() instead of build()."""

    @staticmethod
    def walls(x):
        raise NotImplementedError

    @classmethod
    def profile(cls, env):
        """Closed (r, z) profile with names replaced from `env` (see bind())."""
        ns = SimpleNamespace(**{k: f"({v})" for k, v in env.items()})
        return wall_profile(*cls.walls(ns))

    @classmethod
    def symbolic_profile(cls):
        """The profile with param / derived names left unexpanded (for docs)."""
        names = [p.name for p in cls.params] + [d[0] for d in cls.derived]
        return wall_profile(*cls.walls(SimpleNamespace(**{n: n for n in names})))

    @classmethod
    def build(cls, doc, name, sheet, env):
        if sheet is None:  # recorded: the profile as a revolve operation
            b = Builder(doc, name, sheet, env)
            return b.finish(b.revolve(None, cls.profile(env), ("0", "360")))
        return revolved(doc, name, sheet, cls.profile(env))


# ------------------------------------------------------------------ paths

class Path:
    """A named outline in a primitive's own plane: a shape that more than
    one primitive draws (a dovetail, ...), declared once.

    A path is flat and makes no object. It declares names like a
    Primitive does, `params` (Param), `derived` and `checks`, which a
    primitive takes into its own (as params, or as `fixed` when they
    define the part), and gives its outline as (u, v) or (u, v, radius)
    expressions over those names, for Builder's prism, loft or revolve.
    Optional features (`options`: name -> (params, derived, checks)) add
    their names only when a primitive turns them on.

    A path's outline is closed, so a primitive can prism, loft or revolve
    it as it is. Each path documents its frame and its offsets. Its page,
    `primlib/paths/<key>.html`, comes from `make_docs.py` like a
    primitive's.
    """

    title = ""
    params = ()
    derived = ()
    checks = ()
    options = {}
    intro = None  # docs page: text in place of the docstring

    @classmethod
    def key(cls):
        """Registry key: the defining module's name (dovetail, ...)."""
        return cls.__module__.rsplit(".", 1)[-1]

    @classmethod
    def declare(cls, **on):
        """The names a primitive takes from this path, with the options in
        `on` (name=True) turned on: SimpleNamespace(params, derived,
        checks), each a tuple."""
        unknown = set(on) - set(cls.options)
        if unknown:
            raise ValueError(f"{cls.key()}: no option {', '.join(sorted(unknown))}")
        params, derived, checks = list(cls.params), list(cls.derived), list(cls.checks)
        for name, (p, d, c) in cls.options.items():
            if on.get(name):
                params += p
                derived += d
                checks += c
        return SimpleNamespace(params=tuple(params), derived=tuple(derived),
                               checks=tuple(checks))


_PLAIN = re.compile(r"-?(?:[A-Za-z_]\w*|\d+(?:\.\d*)?)")


def term(expr, additive=False):
    """`expr` bracketed unless it is a name or a number, or (`additive`,
    added or taken away whole) has no + or - of its own."""
    expr = str(expr).strip()
    if _PLAIN.fullmatch(expr) or (additive and not re.search(r"\s[-+]\s", expr)):
        return expr
    return f"({expr})"


def _negated(expr):
    """The x of `-x` (a name, number or whole bracket), else None."""
    if re.fullmatch(r"-(?:[A-Za-z_]\w*|\d+(?:\.\d*)?)", expr):
        return expr[1:]
    if expr.startswith("-(") and expr.endswith(")"):
        depth = 0
        for i, ch in enumerate(expr[1:], 1):
            depth += {"(": 1, ")": -1}.get(ch, 0)
            if depth == 0:
                return expr[2:-1] if i == len(expr) - 1 else None
    return None


def total(base, *terms):
    """`base` plus each (sign, expr, divisor) of `terms` whose expr isn't
    "0", written out: total("tip_hw", ("+", "g", "tan(angle / 2)")) is
    "tip_hw + g / tan(angle / 2)". A term written `-x` turns its sign."""
    out = str(base)
    for sign, expr, over in terms:
        expr = str(expr).strip()
        if expr == "0":
            continue
        inner = _negated(expr)
        if inner is not None:
            sign, expr = "-" if sign == "+" else "+", inner
        out += f" {sign} {term(expr, additive=not over)}" + (f" / {over}" if over else "")
    return out
