"""The record target: a primitive's operations kept as a tree, with every size
left as an expression over the primitive's own names (its params, fixed and
derived values), so that another program can build it at any values.

    tree = record(available()["hinge"])

Each operation is a node `{"id": n, "op": "box", "name": suffix, ...}`; an
argument that is another operation is its id. Expressions are strings, as the
primitive wrote them. A build that evaluates a value on the way (to choose
between shapes) or makes FreeCAD objects itself can't be recorded yet: it
raises NotRecordable, saying which (docs/PLAN.md 1.2).
"""

from primlib.core import Builder, expand


FORMAT = "primlib.prim"  # docs/FORMAT.md
VERSION = 1


class NotRecordable(Exception):
    """The build does something the record target can't keep."""


class Recording:
    """What a recorded build() gets as its `doc`: the nodes made so far."""

    def __init__(self, root=""):
        self.nodes = []
        self.root = root  # the primitive's name: node names are relative to it

    def __repr__(self):
        return f"Recording({len(self.nodes)} nodes)"


class Node:
    """An operation's result, as the primitive holds it: its id."""

    __slots__ = ("id", "op")

    def __init__(self, id_, op):
        self.id, self.op = id_, op

    def __repr__(self):
        return f"Node({self.id}, {self.op})"


def _e(expr):
    """An expression as text."""
    return str(expr)


def _pts(pts):
    """Points of expressions: (a, b) or (a, b, radius)."""
    return [[_e(c) for c in p] for p in pts]


def _ref(node):
    if not isinstance(node, Node):
        raise NotRecordable(f"an operation was given {type(node).__name__}, not another operation's result")
    return node.id


class RecordBuilder(Builder):
    """The FreeCAD target's operations (targets/freecad.py), kept."""

    def __init__(self, doc, name, sheet, env):
        self.doc, self.name, self.sheet, self.env = doc, name, sheet, env
        self.made = []

    def _node(self, op, suffix, unnamed=False, **args):
        """A node named as FreeCAD would name its object, less the primitive's
        own name: a nested part's operations keep the part's name. A choice,
        move or turn is `unnamed` (a file can't name one), nested or not."""
        node = Node(len(self.doc.nodes), op)
        part = self.name[len(self.doc.root):].lstrip("_")
        name = None if unnamed else "_".join(n for n in (part, suffix) if n) or None
        self.doc.nodes.append({"id": node.id, "op": op, "name": name, **args})
        return node

    def x(self, expr):
        """Names stay names: the file says what they are."""
        return self._e(expr)

    def _e(self, expr):
        """An expression as text. In a part nested in another (Builder.part),
        each of its names is the outer expression it is bound to: the file
        holds the outer primitive's names only."""
        if self.name == self.doc.root:
            return _e(expr)
        # A name bound to itself stays (a part's text may be in the outer names already).
        rebound = {k: v for k, v in self.env.items() if str(v).strip("() ") != k}
        return expand(_e(expr), rebound)

    def _pts(self, pts):
        return [[self._e(c) for c in p] for p in pts]

    # -- reaching past the operations: not recordable (yet) -----------------

    def add(self, kind, suffix):
        raise NotRecordable(f"makes a FreeCAD {kind} itself ({suffix})")

    def bind(self, obj, props):
        raise NotRecordable(f"binds FreeCAD properties itself ({', '.join(props)})")

    # -- solids --------------------------------------------------------------

    def box(self, suffix, x, y, z):
        return self._node("box", suffix, x=[self._e(v) for v in x], y=[self._e(v) for v in y], z=[self._e(v) for v in z])

    def beyond(self, suffix, normal, d, size="500"):
        return self._node("beyond", suffix, normal=[float(v) for v in normal], d=self._e(d), size=self._e(size))

    def cylinder(self, suffix, axis, centre, r, span):
        return self._node("cylinder", suffix, axis=axis, centre=[self._e(c) for c in centre], r=self._e(r),
                          span=[self._e(v) for v in span])

    def cone(self, suffix, axis, centre, r1, r2, span):
        return self._node("cone", suffix, axis=axis, centre=[self._e(c) for c in centre], r1=self._e(r1), r2=self._e(r2),
                          span=[self._e(v) for v in span])

    def slot(self, suffix, axis, centre, r, along, travel, span):
        return self._node("slot", suffix, axis=axis, centre=[self._e(c) for c in centre], r=self._e(r), along=along,
                          travel=self._e(travel), span=[self._e(v) for v in span])

    def sector(self, suffix, r, span, start, angle):
        return self._node("sector", suffix, r=self._e(r), span=[self._e(v) for v in span], start=self._e(start),
                          angle=self._e(angle))

    def polygon(self, suffix, sides, r, span):
        return self._node("polygon", suffix, sides=int(sides), r=self._e(r), span=[self._e(v) for v in span])

    def sphere(self, suffix, centre, r):
        return self._node("sphere", suffix, centre=[self._e(c) for c in centre], r=self._e(r))

    # -- from profiles -------------------------------------------------------

    def prism(self, suffix, pts, plane, span):
        return self._node("prism", suffix, points=self._pts(pts), plane=plane, span=[self._e(v) for v in span])

    def loft(self, suffix, sections, plane):
        return self._node("loft", suffix, plane=plane, ruled=True,
                          sections=[{"points": self._pts(p), "at": self._e(at)} for p, at in sections])

    def revolve(self, suffix, pts, span):
        return self._node("revolve", suffix, points=self._pts(pts), span=[self._e(v) for v in span])

    def loft_about(self, suffix, sections):
        return self._node("loft_about", suffix,
                          sections=[{"points": self._pts(p), "angle": self._e(a)} for p, a in sections])

    def shapestring(self, suffix, string, font, size, at, justify="4"):
        return self._node("text", suffix, string=self._e(string), font=self._e(font), size=self._e(size),
                          at=[self._e(v) for v in at], justify=self._e(justify))

    def extrude(self, suffix, base, length, z=None):
        return self._node("extrude", suffix, base=_ref(base), length=self._e(length),
                          z=None if z is None else self._e(z))

    # -- patterns ------------------------------------------------------------

    def array(self, suffix, base, axis, count, start, step):
        return self.grid(suffix, base, {axis: (count, start, step)})

    def grid(self, suffix, base, axes):
        return self._node("array", suffix, base=_ref(base),
                          along={a: {"count": self._e(c), "start": self._e(s), "step": self._e(d)}
                                 for a, (c, s, d) in axes.items()})

    def choose(self, guard, if_true, if_false):
        a, b = if_true(), if_false()
        if None in (a, b):
            return None
        return self._node("choose", None, unnamed=True, guard=self._e(guard), then=_ref(a), otherwise=_ref(b))

    def series(self, suffix, count, make, join="fuse"):
        """One item, over the index `i`."""
        item = make("i")
        if item is None:
            return None
        return self._node("series", suffix, count=self._e(count), index="i", item=_ref(item), join=join)

    def move(self, obj, by):
        return self._node("move", None, unnamed=True, base=_ref(obj), by=[None if d is None else self._e(d) for d in by])

    def turn(self, obj, axis, angle):
        return self._node("turn", None, unnamed=True, base=_ref(obj), axis=axis, angle=self._e(angle))

    def extent(self, obj, axis):
        """Functions of the operation's result: xmin(@3), xmax(@3)."""
        return (f"{axis}min(@{_ref(obj)})", f"{axis}max(@{_ref(obj)})")

    def polar(self, suffix, base, count, angle):
        return self._node("polar", suffix, base=_ref(base), count=self._e(count), angle=self._e(angle))

    # -- booleans ------------------------------------------------------------

    def fuse(self, suffix, objs):
        return self._node("fuse", suffix, of=[_ref(o) for o in objs])

    def common(self, suffix, objs):
        return self._node("common", suffix, of=[_ref(o) for o in objs])

    def cut(self, suffix, base, tools):
        return self._node("cut", suffix, base=_ref(base), tools=[_ref(t) for t in tools])

    def compound(self, suffix, objs):
        return self._node("compound", suffix, of=[_ref(o) for o in objs])

    def finish(self, result):
        return result


def names(cls):
    """Every name a primitive's expressions use, as itself."""
    return {n: n for n in [p.name for p in cls.params] + [d[0] for d in cls.fixed + cls.derived]}


def record(cls):
    """Primitive class `cls` as a tree: its declarations and its operations,
    sizes over its own names. Raises NotRecordable if its build can't be kept."""
    if cls.freecad_only:
        raise NotRecordable(f"FreeCAD only: {cls.freecad_only}")
    rec = Recording(cls.key())
    env = names(cls)
    try:
        result = cls.build(rec, cls.key(), None, env)
    except NotRecordable:
        raise
    except (AttributeError, TypeError) as e:
        # A build that asks the sheet or the document for something.
        raise NotRecordable(f"asks FreeCAD for something while building: {type(e).__name__}: {e}") from e
    if not isinstance(result, Node):
        raise NotRecordable(f"build returned {result!r}, not an operation")
    group_of = {n: heading for heading, ns in cls.groups for n in ns}
    return {
        "format": FORMAT,
        "version": VERSION,
        "primitive": cls.key(),
        "title": cls.title,
        "params": [{"name": p.name, "default": str(p.default), "note": p.note, "group": group_of.get(p.name)}
                   for p in cls.params],
        "fixed": [{"name": n, "expr": str(e), "note": note} for n, e, note in cls.fixed],
        "derived": [{"name": n, "expr": str(e), "note": note} for n, e, note in cls.derived],
        "checks": [{"expr": str(e), "message": m} for e, m in cls.checks],
        "ops": rec.nodes,
        "result": result.id,
        "motion": [],
    }
