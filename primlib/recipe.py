"""Recipes and assemblies (docs/FORMAT.md#recipes): reusable patterns of
primitives -- a row of pieces by key, a length filled, a series, a mirrored
pair -- each with its own parameters and checks, like a primitive's. An
assembly is a recipe whose parts may themselves be recipes or assemblies,
and which can turn what a joint holds (a lid on its hinges).

A recipe declares `parts` (a primitive at values bound to the recipe's
names, maybe mirrored) and places them in `place(r)` through a Placer. It
records as a .prim document of kind "recipe", with the primitives it uses
inside it, which view4d draws live and the FreeCAD target compiles.

    doc = record_recipe(EdgeFill)
    for p in layout(doc, {"span": "300"}):      # plain Python: the reference
        print(p.part, p.at)
"""

import math
from dataclasses import dataclass

from primlib.core import Param, merge  # noqa: F401 - for the recipes
from primlib.expr import ExprError, evaluate, failed_checks, is_string, names
from primlib.targets.record import FORMAT

KIND = "recipe"
ASSEMBLY = "assembly"
RECIPE_VERSION = 2
AXES = ("x", "y", "z")


class RecipeError(ValueError):
    """A recipe that can't be recorded or laid out."""


@dataclass(frozen=True)
class Part:
    """A primitive at values bound to the recipe's names. `bind`: param ->
    expression (unbound params keep the primitive's defaults); `mirror`:
    "x", "y" or "z" to mirror it across the plane through its origin normal
    to that axis; `colour`: (r, g, b), 0 to 1, or None. `pieces`: the names
    of the compound's pieces to take (a hinge's ("side_a",)), or None for
    all. `to_print`: on the print list. In an assembly `primitive` may name
    a recipe or an assembly: the part is that, laid out at its values."""

    name: str
    primitive: str
    bind: dict
    mirror: str = None
    colour: tuple = None
    pieces: tuple = None
    to_print: bool = False


class Recipe:
    """Base class: subclasses declare params, fixed, derived, checks, parts
    and place(r)."""

    title = ""
    params = ()
    fixed = ()
    derived = ()
    checks = ()
    groups = ()
    parts = ()
    slots = 8   # the longest key, and the most a series holds, in FreeCAD
    kind = KIND

    @classmethod
    def key(cls):
        return cls.__module__.rsplit(".", 1)[-1]

    @classmethod
    def place(cls, r):
        """Place the parts with Placer `r`; return the placement that is the
        result."""
        raise NotImplementedError


class Assembly(Recipe):
    """A recipe whose parts may be recipes or assemblies (primlib/assemblies/)."""

    kind = ASSEMBLY


def _turns(turn):
    out = []
    for t in turn or ():
        axis, angle = t
        if axis not in AXES:
            raise RecipeError(f"a turn about {axis!r}: x, y or z")
        out.append({"axis": axis, "angle": str(angle)})
    return out


def _at(at):
    if len(at) != 3:
        raise RecipeError(f"a place is (x, y, z), not {at!r}")
    return [str(v) for v in at]


class Placer:
    """Records placements as a recipe's `place` list; each returns its id."""

    def __init__(self, parts):
        self.parts = {p.name for p in parts}
        self.nodes = []

    def _node(self, op, name, **fields):
        self.nodes.append({"id": len(self.nodes), "op": op, "name": name, **fields})
        return len(self.nodes) - 1

    def _part(self, part):
        if part not in self.parts:
            raise RecipeError(f"no part {part!r}")
        return part

    def instance(self, name, part, at=("0", "0", "0"), turn=()):
        """`part` turned by `turn` ((axis, angle), ...: in order, about its
        own origin), then put at `at`."""
        return self._node("instance", name, part=self._part(part), at=_at(at), turn=_turns(turn))

    def row(self, name, key, pieces, at=("0", "0", "0"), along="z", gap="0", lead="0", turn=()):
        """Pieces end to end by `key`: each letter a piece of `pieces`
        (letter -> (part, length)), along `along` ("x", "-y", ...) from
        `at`, `lead` before the first and `gap` between them, each piece
        turned by `turn`."""
        if along.lstrip("-") not in AXES:
            raise RecipeError(f"along {along!r}: x, y or z, or -x, -y or -z")
        pieces = {c: {"part": self._part(p), "length": str(n)} for c, (p, n) in pieces.items()}
        if any(len(c) != 1 for c in pieces):
            raise RecipeError("a row's pieces are single letters")
        return self._node("row", name, key=str(key), pieces=pieces, at=_at(at), along=along,
                          gap=str(gap), lead=str(lead), turn=_turns(turn))

    def series(self, name, count, item):
        """`item(i)` placed for i = 0 .. count - 1: it is called once with
        the name "i" and its placements may use it."""
        return self._node("series", name, count=str(count), index="i", item=item("i"))

    def choose(self, guard, then, otherwise=None):
        """`then` if `guard` is over 0, else `otherwise` (or nothing)."""
        return self._node("choose", None, guard=str(guard), then=then, otherwise=otherwise)

    def group(self, name, of):
        return self._node("group", name, of=list(of))

    def move(self, name, base, by=("0", "0", "0"), turn=()):
        """`base`'s placements turned (about the origin) and moved."""
        return self._node("move", name, base=base, by=_at(by), turn=_turns(turn))

    def joint(self, name, base, at, axis, angle):
        """`base`'s placements turned by `angle` (an expression: a parameter
        that opens it) about the line through `at` along `axis`."""
        if axis not in AXES:
            raise RecipeError(f"a joint about {axis!r}: x, y or z")
        return self._node("joint", name, base=base, at=_at(at), axis=axis, angle=str(angle))


def _documents():
    """{key: (kind, class)} of every primitive, recipe and assembly."""
    from primlib.assemblies import available as assemblies
    from primlib.primitives import available as primitives
    from primlib.recipes import available as recipes

    out = {k: ("primitive", c) for k, c in primitives().items()}
    out.update({k: (KIND, c) for k, c in recipes().items()})
    out.update({k: (ASSEMBLY, c) for k, c in assemblies().items()})
    return out


def compound_pieces(prim):
    """The names of a primitive document's compound pieces, or () if its
    result isn't a compound."""
    ops = prim["ops"]
    result = ops[prim["result"]]
    return tuple(ops[i]["name"] for i in result["of"]) if result["op"] == "compound" else ()


def record_recipe(cls):
    """Recipe or assembly `cls` as a .prim document of its kind, with the
    documents its parts use (primitives at their defaults, recipes and
    assemblies recorded in turn) inside it."""
    from primlib.targets.record import record

    docs = _documents()
    uses = {}
    for part in cls.parts:
        what = f"part {part.name}"
        if part.primitive not in docs:
            raise RecipeError(f"{what}: no primitive, recipe or assembly {part.primitive!r}")
        kind, sub = docs[part.primitive]
        if kind != "primitive" and cls.kind != ASSEMBLY:
            raise RecipeError(f"{what}: a {kind} is a part of an assembly, not of a recipe")
        if part.primitive not in uses:
            uses[part.primitive] = record(sub) if kind == "primitive" else record_recipe(sub)
        used = uses[part.primitive]
        unknown = set(part.bind) - {p["name"] for p in used["params"]}
        if unknown:
            raise RecipeError(f"{what}: {part.primitive} has no {', '.join(sorted(unknown))}")
        if part.mirror not in (None, *AXES):
            raise RecipeError(f"{what}: mirror {part.mirror!r}")
        if kind != "primitive" and (part.mirror or part.pieces):
            raise RecipeError(f"{what}: only a primitive is mirrored or taken in pieces")
        if part.pieces is not None:
            missing = set(part.pieces) - set(compound_pieces(used))
            if missing:
                raise RecipeError(f"{what}: {part.primitive} has no piece {', '.join(sorted(missing))}")
    r = Placer(cls.parts)
    result = cls.place(r)
    group_of = {n: heading for heading, ns in cls.groups for n in ns}
    return {
        "format": FORMAT,
        "version": RECIPE_VERSION,
        "kind": cls.kind,
        "primitive": cls.key(),
        "title": cls.title,
        "params": [{"name": p.name, "default": str(p.default), "note": p.note, "group": group_of.get(p.name)}
                   for p in cls.params],
        "fixed": [{"name": n, "expr": str(e), "note": note} for n, e, note in cls.fixed],
        "derived": [{"name": n, "expr": str(e), "note": note} for n, e, note in cls.derived],
        "checks": [{"expr": str(e), "message": m} for e, m in cls.checks],
        "slots": cls.slots,
        "parts": [{"name": p.name, "primitive": p.primitive, "bind": {k: str(v) for k, v in p.bind.items()},
                   "mirror": p.mirror, "colour": list(p.colour) if p.colour else None,
                   "pieces": list(p.pieces) if p.pieces is not None else None, "print": p.to_print}
                  for p in cls.parts],
        "place": r.nodes,
        "result": result,
        "uses": uses,
        "motion": [],
    }


# -- laying out, in plain Python: the reference ------------------------------------

@dataclass
class Placed:
    """A part placed: `rotation` (3x3, rows) then `at`; `name` says where
    it came from (the row's name and slot, as FreeCAD names the link)."""

    name: str
    part: str
    rotation: tuple
    at: tuple


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def turn_matrix(axis, degrees):
    """The rotation about `axis` by `degrees`, anticlockwise seen from its +
    end; quarter turns exact."""
    q = degrees / 90.0
    if q == round(q):
        c, s = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(round(q)) % 4]
    else:
        a = math.radians(degrees)
        c, s = math.cos(a), math.sin(a)
    c, s = float(c), float(s)
    return {"x": ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)),
            "y": ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c)),
            "z": ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))}[axis]


def _rotation(turns, env):
    m = IDENTITY
    for t in turns:
        m = _mul(turn_matrix(t["axis"], evaluate(t["angle"], env)), m)
    return m


def _num(text, env, what):
    v = evaluate(text, env)
    if isinstance(v, str):
        raise RecipeError(f"{what}: {text} is text, not a number")
    return v


def recipe_names(doc, values=None):
    """The recipe's names at `values` (or its own)."""
    return names(doc, values if values is not None else doc.get("values"))


def recipe_checks(doc, values=None):
    """The messages of the checks recipe `doc` fails at `values` (or its
    own): its own, then each part's primitive's at the part's values."""
    env = recipe_names(doc, values)
    failed = failed_checks(doc, env)
    if failed:
        return failed
    for part, vals in part_values(doc, values).items():
        used = doc["uses"][next(p["primitive"] for p in doc["parts"] if p["name"] == part)]
        try:
            if is_recipe(used):
                failed += [f"part {part}: {m}" for m in recipe_checks(used, vals)]
            else:
                failed += [f"part {part}: {m}" for m in failed_checks(used, names(used, vals))]
        except ExprError as e:
            failed.append(f"part {part}: {e}")
    return failed


def layout(doc, values=None):
    """Recipe document `doc` laid out at `values`: [Placed, ...]. Raises
    RecipeError if a check fails (its own or a part's) or a placement can't
    be made."""
    env = recipe_names(doc, values)
    failed = recipe_checks(doc, values)
    if failed:
        raise RecipeError(f"{doc['primitive']}: " + "; ".join(failed))
    nodes = doc["place"]

    def place(i, env):
        node = nodes[i]
        kind, name = node["op"], node["name"]
        try:
            if kind == "instance":
                at = tuple(_num(v, env, "at") for v in node["at"])
                return [Placed(name or node["part"], node["part"], _rotation(node["turn"], env), at)]
            if kind == "row":
                return _row(node, env)
            if kind == "series":
                count = _num(node["count"], env, "count")
                return [p for k in range(int(math.trunc(count)))
                        for p in place(node["item"], dict(env, **{node["index"]: float(k)}))]
            if kind == "choose":
                pick = node["then"] if _num(node["guard"], env, "guard") > 0 else node["otherwise"]
                return [] if pick is None else place(pick, env)
            if kind == "group":
                return [p for j in node["of"] for p in place(j, env)]
            if kind == "move":
                m = _rotation(node["turn"], env)
                by = tuple(_num(v, env, "by") for v in node["by"])
                return [_moved(p, m, by) for p in place(node["base"], env)]
            if kind == "joint":
                m = turn_matrix(node["axis"], _num(node["angle"], env, "angle"))
                a = tuple(_num(v, env, "at") for v in node["at"])
                # About the line through a: p' = m (p - a) + a.
                by = tuple(x - y for x, y in zip(a, _apply(m, a)))
                return [_moved(p, m, by) for p in place(node["base"], env)]
        except ExprError as e:
            raise RecipeError(f"placement {i} ({kind} {name}): {e}") from e
        raise RecipeError(f"placement {i}: unknown op {kind!r}")

    placed = place(doc["result"], env)
    # A part that is a recipe or an assembly: its own layout, where it is placed.
    nested = {p["name"]: doc["uses"][p["primitive"]] for p in doc["parts"] if is_recipe(doc["uses"][p["primitive"]])}
    if not nested:
        return placed
    vals = part_values(doc, values)
    inner = {part: layout(sub, vals[part]) for part, sub in nested.items()}
    out = []
    for p in placed:
        if p.part not in inner:
            out.append(p)
            continue
        for q in inner[p.part]:
            q = _moved(q, p.rotation, p.at)
            out.append(Placed(f"{p.name}/{q.name}", f"{p.part}/{q.part}", q.rotation, q.at))
    return out


def _moved(p, m, by):
    """`p` turned by `m` about the origin, then moved by `by`."""
    return Placed(p.name, p.part, _mul(m, p.rotation), tuple(a + b for a, b in zip(_apply(m, p.at), by)))


def _row(node, env):
    key = evaluate(node["key"], env)
    if not isinstance(key, str):
        raise RecipeError(f"row {node['name']}: its key {node['key']} is a number, not text")
    sign = -1.0 if node["along"].startswith("-") else 1.0
    axis = AXES.index(node["along"].lstrip("-"))
    start = [_num(v, env, "at") for v in node["at"]]
    gap = _num(node["gap"], env, "gap")
    m = _rotation(node["turn"], env)
    out, s = [], _num(node["lead"], env, "lead")
    for k, c in enumerate(key):
        piece = node["pieces"].get(c)
        if piece is None:
            raise RecipeError(f"row {node['name']}: its key {key!r} has {c!r}, not one of "
                              f"{' '.join(node['pieces'])}")
        at = list(start)
        at[axis] += sign * s
        out.append(Placed(f"{node['name']}_{k + 1}{c}", piece["part"], m, tuple(at)))
        s += _num(piece["length"], env, "length") + gap
    return out


def part_values(doc, values=None):
    """Each part's primitive values at the recipe's `values`: part name ->
    {param: value as an expression}."""
    env = recipe_names(doc, values)
    out = {}
    for part in doc["parts"]:
        vals = {}
        for k, e in part["bind"].items():
            v = evaluate(e, env)
            vals[k] = f"'{v}" if isinstance(v, str) else repr(float(v))
        out[part["name"]] = vals
    return out


def leaf_parts(doc, values=None, prefix="", printed=False):
    """Every primitive part, nested ones by path ("hinges/T"): path ->
    {"doc": the primitive's document, "values": its values, "mirror",
    "pieces", "colour", "print"}, as layout's Placed.part names them. A
    part to print prints all of a recipe or assembly it is."""
    out = {}
    vals = part_values(doc, values)
    for p in doc["parts"]:
        used = doc["uses"][p["primitive"]]
        path = f"{prefix}{p['name']}"
        if is_recipe(used):
            out.update(leaf_parts(used, vals[p["name"]], f"{path}/", printed or p.get("print", False)))
        else:
            out[path] = {"doc": used, "values": vals[p["name"]], "mirror": p["mirror"], "pieces": p.get("pieces"),
                         "colour": p.get("colour"), "print": printed or p.get("print", False)}
    return out


def is_recipe(doc):
    """A recipe or an assembly (laid out), not a primitive (built)."""
    return doc.get("kind") in (KIND, ASSEMBLY)


__all__ = ["Recipe", "Assembly", "Part", "Placer", "Placed", "record_recipe", "layout", "part_values",
           "recipe_checks", "leaf_parts", "compound_pieces", "turn_matrix",
           "is_recipe", "RecipeError", "Param", "is_string"]
