""".prim files (docs/FORMAT.md): write a primitive's record, read one back,
and build it through any Builder.

    tree = export("hinge", {"pitch": "12"})     # plain Python
    save(tree, "hinge.prim")
    Hinge = primitive(load("hinge.prim"))       # a Primitive class
    Hinge.make(doc, "Hinge")                    # FreeCAD: sheet rows, checks, objects
"""

import json
import re

from primlib.core import Param, Primitive
from primlib.expr import evaluate, failed_checks, names
from primlib.targets.record import FORMAT, VERSION, NotRecordable, record  # noqa: F401


class PrimError(ValueError):
    """A .prim file that can't be read or built."""


# -- writing ---------------------------------------------------------------------

def export(key, values=None):
    """Primitive or recipe `key` recorded, with `values` (name -> expression)
    to build at. Raises PrimError for an unknown key or name, a value that
    doesn't evaluate, or a check that fails at those values."""
    from primlib.recipe import RecipeError, _documents, record_recipe

    docs = _documents()
    if key not in docs:
        raise PrimError(f"no primitive, recipe or assembly {key!r}; there are: {', '.join(docs)}")
    kind, cls = docs[key]
    try:
        tree = record(cls) if kind == "primitive" else record_recipe(cls)
    except RecipeError as e:
        raise PrimError(f"{key}: {e}") from e
    values = {k: str(v) for k, v in (values or {}).items()}
    unknown = set(values) - {p["name"] for p in tree["params"]}
    if unknown:
        raise PrimError(f"{key} has no parameter {', '.join(sorted(unknown))}")
    failed = check(tree, values)
    if failed:
        raise PrimError(f"{key}: " + "; ".join(failed))
    if values:
        tree = dict(tree, values=values)
    return tree


def dumps(tree):
    """The file's text: one operation (or part, or placement) per line, so a
    diff reads well; a recipe's primitives each as a file of their own."""
    return _dumps(tree, "") + "\n"


def _dumps(tree, indent):
    lists = ("ops", "parts", "place")
    lines = ["{"]
    last = ("parts", "place", "ops", "uses")
    items = [(k, v) for k, v in tree.items() if k not in last] + [(k, tree[k]) for k in last if k in tree]
    for n, (k, v) in enumerate(items):
        comma = "," if n < len(items) - 1 else ""
        if k in lists:
            lines.append(f"  {json.dumps(k)}: [")
            rows = [f"    {json.dumps(x, ensure_ascii=False)}" for x in v]
            lines += [r + ("," if j < len(rows) - 1 else "") for j, r in enumerate(rows)]
            lines.append(f"  ]{comma}")
        elif k == "uses":
            lines.append(f"  {json.dumps(k)}: {{")
            for j, (name, sub) in enumerate(v.items()):
                inner = _dumps(sub, "    ").replace("\n", "\n    ")
                lines.append(f"    {json.dumps(name)}: {inner}" + ("," if j < len(v) - 1 else ""))
            lines.append(f"  }}{comma}")
        else:
            lines.append(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{comma}")
    lines.append("}")
    return "\n".join(lines)


def save(tree, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(tree))


# -- reading ---------------------------------------------------------------------

def loads(text):
    try:
        tree = json.loads(text)
    except json.JSONDecodeError as e:
        raise PrimError(f"not JSON: {e}") from e
    return _checked(tree)


def _checked(tree):
    from primlib.recipe import ASSEMBLY, KIND, RECIPE_VERSION

    if not isinstance(tree, dict) or tree.get("format") != FORMAT:
        raise PrimError(f"not a {FORMAT} file")
    if not isinstance(tree.get("version"), int) or tree["version"] > RECIPE_VERSION:
        raise PrimError(f"version {tree.get('version')!r}: this reads up to {RECIPE_VERSION}")
    kind = tree.get("kind", "primitive")
    if kind not in ("primitive", KIND, ASSEMBLY):
        raise PrimError(f"kind {kind!r}: a primitive, a {KIND} or an {ASSEMBLY}")
    nodes = "ops" if kind == "primitive" else "place"
    need = ["params", "fixed", "derived", "checks", nodes, "result"]
    if kind != "primitive":
        need += ["parts", "uses", "slots"]
    for k in need:
        if k not in tree:
            raise PrimError(f"no {k!r}")
    for i, op in enumerate(tree[nodes]):
        if op.get("id") != i:
            raise PrimError(f"{'operation' if nodes == 'ops' else 'placement'} {i} has id {op.get('id')!r}")
    if kind != "primitive":
        for name, sub in tree["uses"].items():
            if kind == KIND and sub.get("kind", "primitive") != "primitive":
                raise PrimError(f"uses {name}: a recipe uses primitives only (an assembly uses recipes)")
            try:
                _checked(sub)
            except PrimError as e:
                raise PrimError(f"uses {name}: {e}") from e
        for part in tree["parts"]:
            if part.get("primitive") not in tree["uses"]:
                raise PrimError(f"part {part.get('name')!r}: its primitive {part.get('primitive')!r} isn't in uses")
    return tree


def load(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())


# -- building ----------------------------------------------------------------------

_REFS = ("base", "item", "then", "otherwise")
_REF_LISTS = ("of", "tools")
_NAME_I = re.compile(r"(?<![\w.])i(?![\w(])")
_EXTENT = re.compile(r"\b([xyz])(min|max)\(@(\d+)\)")


def _uses_index(ops):
    """Per operation id: whether it, or anything it is made from, uses `i`."""
    uses = []
    for op in ops:
        own = any(isinstance(v, str) and _NAME_I.search(v) for v in _strings(op))
        refs = [op[k] for k in _REFS if isinstance(op.get(k), int)]
        refs += [r for k in _REF_LISTS for r in op.get(k, ())]
        refs += [int(m[2]) for v in _strings(op) for m in _EXTENT.findall(v)]
        uses.append(own or any(uses[r] for r in refs))
    return uses


def _strings(v, skip=("op", "name", "axis", "plane", "join", "index", "along_axis")):
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in skip:
                yield from _strings(x)


def build(b, tree):
    """Build `tree`'s operations with Builder `b` (any target); return the
    result. Each operation is built once, except one that uses a series'
    index, once per index; only what the result reaches is built."""
    ops = tree["ops"]
    uses_i = _uses_index(ops)
    made = {}
    index = [None]  # the series index now being built, as an expression

    def at(i):
        key = (i, index[0] if uses_i[i] else None)
        if key not in made:
            made[key] = _op(b, ops[i], at, index)
        return made[key]

    return at(tree["result"])


def _extents(v, b, at):
    """`v` with each xmin(@id) and the like in the target's own terms."""
    if isinstance(v, str):
        if "@" not in v:
            return v
        return _EXTENT.sub(lambda m: b.extent(at(int(m[3])), m[1])[m[2] == "max"], v)
    if isinstance(v, list):
        return [_extents(x, b, at) for x in v]
    if isinstance(v, dict):
        return {k: _extents(x, b, at) for k, x in v.items()}
    return v


def _op(b, op, at, index):
    op = _extents(op, b, at)
    kind, name = op["op"], op["name"]
    pts = lambda p: [tuple(v) for v in p]  # noqa: E731
    if kind == "box":
        return b.box(name, op["x"], op["y"], op["z"])
    if kind == "beyond":
        return b.beyond(name, tuple(op["normal"]), op["d"], op["size"])
    if kind == "cylinder":
        return b.cylinder(name, op["axis"], op["centre"], op["r"], op["span"])
    if kind == "cone":
        return b.cone(name, op["axis"], op["centre"], op["r1"], op["r2"], op["span"])
    if kind == "slot":
        return b.slot(name, op["axis"], op["centre"], op["r"], op["along"], op["travel"], op["span"])
    if kind == "sector":
        return b.sector(name, op["r"], op["span"], op["start"], op["angle"])
    if kind == "polygon":
        return b.polygon(name, op["sides"], op["r"], op["span"])
    if kind == "sphere":
        return b.sphere(name, op["centre"], op["r"])
    if kind == "prism":
        return b.prism(name, pts(op["points"]), op["plane"], op["span"])
    if kind == "loft":
        return b.loft(name, [(pts(s["points"]), s["at"]) for s in op["sections"]], op["plane"])
    if kind == "revolve":
        return b.revolve(name, pts(op["points"]), op["span"])
    if kind == "loft_about":
        return b.loft_about(name, [(pts(s["points"]), s["angle"]) for s in op["sections"]])
    if kind == "text":
        return b.shapestring(name, op["string"], op["font"], op["size"], op["at"], op["justify"])
    if kind == "extrude":
        return b.extrude(name, at(op["base"]), op["length"], op["z"])
    if kind == "array":
        return b.grid(name, at(op["base"]),
                      {a: (v["count"], v["start"], v["step"]) for a, v in op["along"].items()})
    if kind == "polar":
        return b.polar(name, at(op["base"]), op["count"], op["angle"])
    if kind == "move":
        return b.move(at(op["base"]), op["by"])
    if kind == "turn":
        return b.turn(at(op["base"]), op["axis"], op["angle"])
    if kind in ("fuse", "common", "compound"):
        return getattr(b, kind)(name, [at(i) for i in op["of"]])
    if kind == "cut":
        return b.cut(name, at(op["base"]), [at(i) for i in op["tools"]])
    if kind == "choose":
        return b.choose(op["guard"], lambda: at(op["then"]), lambda: at(op["otherwise"]))
    if kind == "series":
        def item(i):
            outer, index[0] = index[0], i
            old_env = b.env
            b.env = dict(old_env, **{op["index"]: i}) if i != op["index"] else old_env
            try:
                return at(op["item"])
            finally:
                index[0], b.env = outer, old_env
        return b.series(name, op["count"], item, op["join"])
    raise PrimError(f"operation {op['id']} ({name or 'result'}): unknown op {kind!r}")


def primitive(tree):
    """A Primitive class for `tree`: make() it as any primitive (FreeCAD), or
    record() it again. The file's `values` become the defaults."""
    values = tree.get("values", {})
    groups = {}
    for p in tree["params"]:
        if p.get("group"):
            groups.setdefault(p["group"], []).append(p["name"])

    def build_(cls, doc, name, sheet, env):
        from primlib.core import Builder
        b = Builder(doc, name, sheet, env)
        result = build(b, tree)
        return None if result is None else b.finish(result)

    cls = type(tree["primitive"].title().replace("_", ""), (Primitive,), {
        "__doc__": tree.get("title", ""),
        "__module__": f"primlib.prim.{tree['primitive']}",
        "title": tree.get("title", ""),
        "params": tuple(Param(p["name"], values.get(p["name"], p["default"]), p.get("note", ""))
                        for p in tree["params"]),
        "fixed": tuple((d["name"], d["expr"], d.get("note", "")) for d in tree["fixed"]),
        "derived": tuple((d["name"], d["expr"], d.get("note", "")) for d in tree["derived"]),
        "checks": tuple((c["expr"], c["message"]) for c in tree["checks"]),
        "groups": tuple((g, tuple(ns)) for g, ns in groups.items()),
        "build": classmethod(build_),
    })
    return cls


def replay(path, doc, name, **values):
    """FreeCAD: build the .prim file at `path` into `doc` as `name`, as
    Primitive.make does (sheet rows, checks), at the file's values or these."""
    return primitive(load(path)).make(doc, name, **values)


def check(tree, values=None):
    """The messages of the checks `tree` fails at `values` (or its own); a
    recipe's parts' checks as well."""
    from primlib.recipe import is_recipe, recipe_checks

    if is_recipe(tree):
        return recipe_checks(tree, values or tree.get("values"))
    return failed_checks(tree, names(tree, values or tree.get("values")))


__all__ = ["export", "dumps", "save", "loads", "load", "build", "primitive", "replay", "check",
           "evaluate", "PrimError"]


def canonical(tree):
    """`tree`'s operations reachable from its result, numbered in the order
    a depth-first walk from the result finishes them. Two trees with the
    same structure come out equal, whatever order they were recorded in."""
    ops, order, seen = tree["ops"], [], {}

    def refs(op):
        out = [int(m[2]) for v in _strings(op) for m in _EXTENT.findall(v)]
        out += [op[k] for k in _REFS if isinstance(op.get(k), int)]
        out += [r for k in _REF_LISTS for r in op.get(k, ())]
        return out

    def visit(i):
        if i in seen:
            return
        seen[i] = None
        for r in refs(ops[i]):
            visit(r)
        seen[i] = len(order)
        order.append(i)

    visit(tree["result"])

    def renumber(k, v):
        if k in _REFS and isinstance(v, int):
            return seen[v]
        if k in _REF_LISTS:
            return [seen[r] for r in v]
        return _renumber_strings(v)

    def _renumber_strings(v):
        if isinstance(v, str):
            return _EXTENT.sub(lambda m: f"{m[1]}{m[2]}(@{seen[int(m[3])]})", v)
        if isinstance(v, list):
            return [_renumber_strings(x) for x in v]
        if isinstance(v, dict):
            return {k: _renumber_strings(x) for k, x in v.items()}
        return v

    return [{k: (seen[i] if k == "id" else renumber(k, v)) for k, v in ops[i].items()} for i in order]
