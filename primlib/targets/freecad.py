"""The FreeCAD target: each operation a FreeCAD object (Part, Draft,
Sketcher), every size bound by an expression to the parameter sheet, so a
saved file recomputes in stock FreeCAD. This was fc_lib's Builder, unchanged.
"""

import FreeCAD as App

from primlib.core import (Builder, _hide, bind_props, expand, pinned_sketch, value,  # noqa: F401
                          value_str)


# Sketch plane -> (rotation taking local x, y onto its axes, normal axis).
# Every plane is right-handed: xy -> z, yz -> x, zx -> y.
_PLANES = {
    "xy": (App.Rotation(), "z"),
    "yz": (App.Rotation(0.5, 0.5, 0.5, 0.5), "x"),
    "zx": (App.Rotation(-0.5, -0.5, -0.5, 0.5), "y"),
}
# The XZ plane: sketch (u, v) -> global (u, 0, v).
_XZ = App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), 90))
# Cylinder / cone axis -> rotation taking the primitive's z onto it.
_AXES = {
    "x": App.Rotation(App.Vector(0, 1, 0), 90),
    "y": App.Rotation(App.Vector(1, 0, 0), -90),
    "z": App.Rotation(),
}


class FreeCADBuilder(Builder):
    """Creates the objects of a non-revolved primitive's build(), every
    dimension bound to the sheet.

    Expressions are written over the primitive's param / derived names and
    expanded through `env`. Objects are named `{name}_{suffix}`, or `name`
    for suffix None (the result). Spans are (lo, hi) expression pairs.
    """

    def __init__(self, doc, name, sheet, env):
        self.doc, self.name, self.sheet, self.env = doc, name, sheet, env
        self.made = []

    def x(self, expr):
        """`expr` over the sheet's aliases."""
        return expand(expr, self.env)

    def add(self, kind, suffix):
        obj = self.doc.addObject(kind, self.name if suffix is None
                                 else f"{self.name}_{suffix}")
        self.made.append(obj)
        return obj

    def bind(self, obj, props):
        bind_props(obj, self.sheet, {k: self.x(v) for k, v in props.items()})
        return obj

    def box(self, suffix, x, y, z):
        """Part::Box spanning `x`, `y`, `z`."""
        props = {}
        for axis, size, (lo, hi) in zip("xyz", ("Length", "Width", "Height"),
                                        (x, y, z)):
            props[size] = f"({hi}) - ({lo})"
            props[f"Placement.Base.{axis}"] = lo
        return self.bind(self.add("Part::Box", suffix), props)

    def beyond(self, suffix, normal, d, size="500"):
        """A cut tool: everything on the far side of the plane normal . p = d, as
        a box `size` wide and deep with one face on the plane, so that what it
        cuts stays flat. `normal` is a unit vector of numbers, `d` an expression."""
        n = App.Vector(*normal)
        rot = App.Rotation(App.Vector(0, 0, 1), n)
        u, v = rot.multVec(App.Vector(1, 0, 0)), rot.multVec(App.Vector(0, 1, 0))
        obj = self.add("Part::Box", suffix)
        obj.Placement = App.Placement(App.Vector(), rot)
        props = {"Length": size, "Width": size, "Height": size}
        for axis in "xyz":
            props[f"Placement.Base.{axis}"] = (
                f"({d}) * ({getattr(n, axis):.10f}) - ({size}) / 2 * "
                f"({getattr(u, axis) + getattr(v, axis):.10f})")
        return self.bind(obj, props)

    def _round(self, kind, suffix, axis, centre, span, radii):
        """Cylinder or cone along `axis`; `centre` gives the other two
        coordinates in xyz order."""
        obj = self.add(kind, suffix)
        obj.Placement = App.Placement(App.Vector(), _AXES[axis])
        others = [a for a in "xyz" if a != axis]
        props = dict(radii, Height=f"({span[1]}) - ({span[0]})")
        props[f"Placement.Base.{axis}"] = span[0]
        for a, c in zip(others, centre):
            props[f"Placement.Base.{a}"] = c
        return self.bind(obj, props)

    def cylinder(self, suffix, axis, centre, r, span):
        return self._round("Part::Cylinder", suffix, axis, centre, span,
                           {"Radius": r})

    def cone(self, suffix, axis, centre, r1, r2, span):
        """Radius `r1` at span[0], `r2` at span[1]."""
        return self._round("Part::Cone", suffix, axis, centre, span,
                           {"Radius1": r1, "Radius2": r2})

    def slot(self, suffix, axis, centre, r, along, travel, span):
        """A round hole along `axis` stretched by `travel` along the axis
        `along`: two cylinders and the box between them, fused."""
        others = [a for a in "xyz" if a != axis]
        k = others.index(along)
        ends = []
        for sign, end in (("-", "lo"), ("+", "hi")):
            at = list(centre)
            at[k] = f"({centre[k]}) {sign} ({travel}) / 2"
            ends.append(self.cylinder(f"{suffix}_{end}", axis, at, r, span))
        spans = {axis: span}
        for i, a in enumerate(others):
            half = f"({travel}) / 2" if i == k else f"({r})"
            spans[a] = (f"({centre[i]}) - {half}", f"({centre[i]}) + {half}")
        mid = self.box(f"{suffix}_mid", spans["x"], spans["y"], spans["z"])
        return self.fuse(suffix, ends + [mid])

    def _pts(self, pts):
        """Polygon vertices expanded; a rounded vertex (a, b, radius) whose
        radius is 0 or less now is left sharp (the sketch can't round by 0,
        so this is fixed when built)."""
        out = []
        for v in pts:
            v = tuple(self.x(e) for e in v)
            if len(v) > 2 and value(self.sheet, v[2]) <= 1e-6:
                v = v[:2]
            out.append(v)
        return out

    def _sketch(self, name, pts, plane, at):
        """Pinned polygon sketch `name` in `plane`, at `at` along its normal."""
        rot, normal = _PLANES[plane]
        sketch = pinned_sketch(
            self.doc, name, self.sheet, self._pts(pts),
            App.Placement(App.Vector(), rot), labels=("a", "b"))
        if sketch is not None:
            self.made.append(sketch)
            self.bind(sketch, {f"Placement.Base.{normal}": at})
        return sketch

    def prism(self, suffix, pts, plane, span):
        """Closed polygon of (a, b) expressions in `plane` ("xy", "yz" or
        "zx"), extruded along the plane's normal over `span`. The sketch is
        `{name}_{suffix}_sketch`, every vertex pinned (constraints a{i},
        b{i}); a vertex given as (a, b, r) is rounded to radius r
        (constraint fillet{i}). None if the sketch fails."""
        sketch = self._sketch(f"{self.name}_{suffix or 'prism'}_sketch", pts, plane, span[0])
        if sketch is None:
            return None
        ext = self.add("Part::Extrusion", suffix)
        ext.Base = sketch
        ext.DirMode = "Normal"
        ext.Solid = True
        return self.bind(ext, {"LengthFwd": f"({span[1]}) - ({span[0]})"})

    def loft(self, suffix, sections, plane):
        """Ruled loft through `sections`, each (pts, at): a polygon as for
        prism() in `plane`, at `at` along the plane's normal. Matching
        vertices are joined, so the polygons must correspond vertex for
        vertex, rounds included. The sketches are
        `{name}_{suffix}_sketch{i}`. None if a sketch fails."""
        sketches = []
        for i, (pts, at) in enumerate(sections):
            sketch = self._sketch(f"{self.name}_{suffix or 'loft'}_sketch{i}", pts, plane, at)
            if sketch is None:
                return None
            sketches.append(sketch)
        obj = self.add("Part::Loft", suffix)
        obj.Sections = sketches
        obj.Solid = True
        obj.Ruled = True
        return obj

    def revolve(self, suffix, pts, span):
        """Closed polygon of (r, z) expressions (a vertex (r, z, radius) is
        rounded) in the XZ plane, revolved about the z axis over the angle
        `span` (deg, from span[0] anticlockwise seen from +z). The sketch is
        `{name}_{suffix}_sketch`. None if the sketch fails."""
        sketch = pinned_sketch(
            self.doc, f"{self.name}_{suffix or 'revolve'}_sketch", self.sheet,
            self._pts(pts), _XZ, labels=("r", "z"))
        if sketch is None:
            return None
        self.made.append(sketch)
        rev = self.add("Part::Revolution", suffix)
        rev.Source = sketch
        rev.Axis, rev.Base = App.Vector(0, 0, 1), App.Vector()
        rev.Solid = True
        rev.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 0))
        return self.bind(rev, {"Angle": f"({span[1]}) - ({span[0]})",
                               "Placement.Rotation.Angle": span[0]})

    def loft_about(self, suffix, sections):
        """Loft through `sections`, each (pts, angle): an (r, z) polygon as
        for revolve(), in the half-plane at `angle` (deg) about the z axis.
        Matching vertices are joined (smoothly, not ruled), so the polygons
        must correspond vertex for vertex. The angles are evaluated now, not
        bound: rebuild after changing them. None if a sketch fails."""
        sketches = []
        for i, (pts, angle) in enumerate(sections):
            turn = App.Rotation(App.Vector(0, 0, 1), value(self.sheet, self.x(angle)))
            sketch = pinned_sketch(
                self.doc, f"{self.name}_{suffix or 'loft'}_sketch{i}", self.sheet,
                self._pts(pts),
                App.Placement(App.Vector(), turn.multiply(_XZ.Rotation)), labels=("r", "z"))
            if sketch is None:
                return None
            self.made.append(sketch)
            sketches.append(sketch)
        obj = self.add("Part::Loft", suffix)
        obj.Sections = sketches
        obj.Solid = True
        obj.Ruled = False
        return obj

    def sector(self, suffix, r, span, start, angle):
        """A cylinder sector about the z axis over the z `span`: radius `r`,
        from `start` (deg, anticlockwise from +x) through `angle`."""
        obj = self.add("Part::Cylinder", suffix)
        obj.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 90))
        return self.bind(obj, {"Radius": r, "Height": f"({span[1]}) - ({span[0]})", "Angle": angle,
                               "Placement.Base.z": span[0], "Placement.Rotation.Angle": start})

    def polygon(self, suffix, sides, r, span):
        """A regular prism about the z axis over the z `span`: `sides` (a
        number) corners on a circle of radius `r`, one on +x."""
        obj = self.add("Part::Prism", suffix)
        obj.Polygon = sides
        return self.bind(obj, {"Circumradius": r, "Height": f"({span[1]}) - ({span[0]})",
                               "Placement.Base.z": span[0]})

    def sphere(self, suffix, centre, r):
        """Part::Sphere of radius `r` centred at `centre` (x, y, z)."""
        props = {"Radius": r}
        for axis, c in zip("xyz", centre):
            props[f"Placement.Base.{axis}"] = c
        return self.bind(self.add("Part::Sphere", suffix), props)

    def array(self, suffix, base, axis, count, start, step):
        """Fused Draft array of `count` copies of `base` along `axis`, the
        first moved to `start`, then every `step`."""
        return self.grid(suffix, base, {axis: (count, start, step)})

    def grid(self, suffix, base, axes):
        """Fused Draft array of `base` along each axis of `axes`, which maps
        "x", "y" or "z" to (count, start, step) as for array(). A base with
        no shape yet (a sketch-based solid) is recomputed first."""
        import Draft

        if base.Shape.isNull():
            self.doc.recompute()
        arr = Draft.make_ortho_array(base, App.Vector(1, 0, 0), App.Vector(0, 1, 0),
                                     App.Vector(0, 0, 1), 1, 1, 1, use_link=False)
        arr.Label = f"{self.name}_{suffix}"
        arr.Fuse = True
        self.made.append(arr)
        props = {}
        for axis, (count, start, step) in axes.items():
            a = axis.upper()
            props.update({f"Number{a}": count, f"Interval{a}.{axis}": step,
                          f"Placement.Base.{axis}": start})
        return self.bind(arr, props)

    def choose(self, guard, if_true, if_false):
        """The result of `if_true()` when `guard` is over 0, else of
        `if_false()`. Only the chosen one is built, by the values now: rebuild
        after changing the guard's names."""
        return if_true() if value(self.sheet, self.x(guard)) > 0 else if_false()

    def series(self, suffix, count, make, join="fuse"):
        """`count` results of `make(i)`, i an index expression from 0, fused
        (or `join` "compound") as `{name}_{suffix}`; one is returned as it is.
        The count is fixed by the values now: rebuild after changing it."""
        items = [make(str(i)) for i in range(int(value(self.sheet, self.x(count))))]
        if not items or None in items:
            return None
        if len(items) == 1 and join == "fuse":
            return items[0]
        return (self.fuse if join == "fuse" else self.compound)(suffix, items)

    def move(self, obj, by):
        """`obj` moved by `by` (dx, dy, dz; None for no move along an axis),
        added to any placement it has. The object itself moves: use the
        result from here on."""
        bound = {path.lstrip("."): e for path, e in obj.ExpressionEngine}   # paths come as ".Placement..."
        props = {}
        for axis, d in zip("xyz", by):
            if d is None:
                continue
            prop = f"Placement.Base.{axis}"
            d = self.x(d)
            props[prop] = d if prop not in bound else f"({bound[prop]}) + ({d})"
        bind_props(obj, self.sheet, props)
        return obj

    def turn(self, obj, axis, angle):
        """`obj` turned by `angle` degrees about the `axis` ("x", "y" or "z")
        through the origin, after any placement it has (a move before is
        turned with it). The angle must be a number: the rotation is set
        when the object is made. The object itself turns: use the result."""
        from primlib.expr import ExprError, evaluate
        from primlib.recipe import turn_matrix

        try:
            degrees = float(evaluate(str(angle), {}))
        except ExprError as e:
            raise ValueError(f"turn by {angle}: the FreeCAD target turns an object when it makes it, "
                             f"so the angle is a number") from e
        m = turn_matrix(axis, degrees)
        r = App.Matrix()
        for i in range(3):
            for j in range(3):
                setattr(r, f"A{i + 1}{j + 1}", m[i][j])
        rot = App.Rotation(r)
        old = obj.Placement
        bound = {path.lstrip("."): e for path, e in obj.ExpressionEngine}
        terms = [bound.get(f"Placement.Base.{a}") for a in "xyz"]
        obj.Placement = App.Placement(rot.multVec(old.Base), rot.multiply(old.Rotation))
        if any(terms):
            # The base's expressions turned with it: each axis a sum of the old ones.
            for i, a in enumerate("xyz"):
                parts = []
                for k in range(3):
                    c = m[i][k]
                    if abs(c) < 1e-12:
                        continue
                    t = terms[k] or repr(getattr(old.Base, "xyz"[k]))
                    parts.append(f"({t})" if c == 1 else f"-({t})" if c == -1 else f"{c!r} * ({t})")
                prop = f"Placement.Base.{a}"
                if any(terms[k] and abs(m[i][k]) >= 1e-12 for k in range(3)):
                    bind_props(obj, self.sheet, {prop: " + ".join(parts)})
                elif prop in bound:
                    obj.setExpression(f".{prop}", None)
        return obj

    def extent(self, obj, axis):
        """(lo, hi) of `obj` along `axis`, as expressions on its shape."""
        a = axis.upper()
        return (f"{obj.Name}.Shape.BoundBox.{a}Min", f"{obj.Name}.Shape.BoundBox.{a}Max")

    def polar(self, suffix, base, count, angle):
        """Fused Draft polar array of `count` copies of `base` about the z
        axis, spread evenly over `angle` (the first and last copies `angle`
        apart, unless it is 360 deg)."""
        import Draft

        if base.Shape.isNull():
            self.doc.recompute()
        arr = Draft.make_polar_array(base, 2, 360, App.Vector(), use_link=False)
        arr.Label = f"{self.name}_{suffix}"
        arr.Fuse = True
        self.made.append(arr)
        return self.bind(arr, {"NumberPolar": count, "Angle": angle})

    def shapestring(self, suffix, string, font, size, at, justify="4"):
        """A line of text in the xy plane: a Draft ShapeString labelled
        `{name}_{suffix}`, its String, FontFile and Size (the capital height)
        bound to `string`, `font` and `size`, its anchor at `at` (x, y, z).
        `justify` is the anchor's place on the line, an index into
        Top/Middle/Bottom (3 apart) x Left/Center/Right: 0 top left, 4 the
        capital height's middle (the default), 8 bottom right (on the
        baseline)."""
        import Draft

        shape = Draft.make_shapestring(String="H", FontFile=str(value_str(self.sheet, self.x(font))),
                                       Size=10)
        shape.Label = f"{self.name}_{suffix}"
        shape.JustificationReference = "Cap Height"
        shape.ScaleToSize = True
        self.made.append(shape)
        return self.bind(shape, {"String": string, "FontFile": font, "Size": size, "Justification": justify,
                                 "Placement.Base.x": at[0], "Placement.Base.y": at[1],
                                 "Placement.Base.z": at[2]})

    def extrude(self, suffix, base, length, z=None):
        """Solid Part::Extrusion of the planar `base` along +z by `length`,
        moved up by `z` (an expression) if given."""
        ext = self.add("Part::Extrusion", suffix)
        ext.Base = base
        ext.DirMode = "Custom"
        ext.Dir = App.Vector(0, 0, 1)
        ext.Solid = True
        props = {"LengthFwd": length}
        if z is not None:
            props["Placement.Base.z"] = z
        return self.bind(ext, props)

    def _boolean(self, kind, suffix, shapes):
        obj = self.add(kind, suffix)
        obj.Shapes = shapes
        obj.Refine = True
        return obj

    def fuse(self, suffix, objs):
        return self._boolean("Part::MultiFuse", suffix, objs)

    def common(self, suffix, objs):
        return self._boolean("Part::MultiCommon", suffix, objs)

    def cut(self, suffix, base, tools):
        """`base` minus `tools` (fused first when there are several)."""
        tool = tools[0] if len(tools) == 1 else self.fuse(f"{suffix or 'cut'}_tools", tools)
        obj = self.add("Part::Cut", suffix)
        obj.Base, obj.Tool = base, tool
        obj.Refine = True
        return obj

    def compound(self, suffix, objs):
        obj = self.add("Part::Compound", suffix)
        obj.Links = objs
        return obj

    def finish(self, result):
        """Hide every object made here except `result`; return `result`."""
        for obj in self.made:
            if obj is not result:
                _hide(obj)
        return result
