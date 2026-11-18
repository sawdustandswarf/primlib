"""Test data for view4d's .prim reader (its `view4d-prim` crate), in plain
Python: every primitive that exports, as a .prim file, and the values
primlib/expr.py gives its names and expressions, which the Rust evaluator
must match.

    python3 tools/view4d_fixtures.py ../view4d/prim/tests/data [baseline.json]

Writes DIR/<key>.prim and DIR/cases.json:

    {"files": {"<key>.prim": [{"values": {..}, "names": {..}, "failed": [..],
                               "exprs": [[text, i or null, value], ..]}, ..]},
     "errors": [text, ..],
     "text": {"env": {..}, "cases": [[text, value], ..], "errors": [text, ..]}}

And each recipe and assembly as DIR/<key>.prim, with DIR/recipes.json: at its defaults
and other values, what primlib/recipe.py's layout gives (or the checks
that fail), which view4d's must match:

    {"<key>.prim": [{"values": {..}, "failed": [..], "parts": {part path: {param: value}}, "print": [path, ..],
                     "placed": [[name, part, rotation rows, at], ..]}, ..]}

With a baseline (tools/baseline.py's output, which needs FreeCAD), also
DIR/freecad.json: each exported primitive's volume and bounding box as
FreeCAD builds it at its defaults, which view4d's solids must match.

An expression that uses a series' index is given at i = 0, 1 and 2; one
that uses an operation's bounds (@id) is left out (it needs geometry).
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from primlib.expr import ExprError, evaluate, failed_checks, is_string, names  # noqa: E402
from primlib.prim import _NAME_I, PrimError, dumps, export  # noqa: E402
from primlib.primitives import available  # noqa: E402
from primlib.targets.record import NotRecordable  # noqa: E402
from tools.text_cases import TEXT_CASES, TEXT_ENV, TEXT_ERRORS  # noqa: E402

SKIP = {"op", "name", "axis", "plane", "join", "index", "id", "ruled", "sides", "normal"}

# Values beyond the defaults, to reach other branches (as in the replay check).
VARIANTS = {
    "rail15": [{"base_width": "30", "end_taper": "0.3"}],
    "topeak_rail": [{"base_width": "70"}],
    "rail15_housing": [{"end_taper": "0.3", "clearance": "0.1"}],
    "rotary_latch": [{"clearance": "0.15"}],
    "support_half": [{"radius": "20", "trim": "-5"}],
    "hinge": [{"length": "60", "rings": "5", "side_b": "12"}],
}

# Values that fail checks (export refuses them; the reader must name them).
FAILING = {"hinge": {"rings": "1"}, "pin": {"diam": "0", "height": "1"}}

# Recipe values beyond the defaults: other keys, counts, a fallback, failures.
RECIPE_VARIANTS = {
    "edge_fill": [{"bigs": "3", "littles": "2", "span": "400"}, {"bigs": "0", "span": "60"},
                  {"littles": "1"}, {"bigs": "9"}],
    "edge_run": [{"key": "'LMSF"}, {"run": "100"}, {"key": "'SXF"}, {"key": "'FFF", "run": "160"}],
    "support_pair": [{"split": "2", "radius": "8"}],
    "hinged_lid": [{"open_angle": "90"}, {"key": "'SMF", "run": "160", "open_angle": "45"},
                   {"hinge_length": "200"}],
    "hybrid_case": [{"open_angle": "60", "key_x": "'SFMF", "key_z_upper": "'SF", "key_hinge": "'TSFMT",
                     "length": "400"},
                    {"split_height": "20"}, {"rail_on": "0"}, {"width": "180"}, {"width": "120"}],
}

# Expressions the evaluator must refuse (as tests/test_expr.py).
ERRORS = ["1 +", "(1", "1 2", "foo(1)", "sin(1; 2)", "nosuchname", "1 / 0", "@2", "1 $ 2",
          "xmin(@3)", "max()", "sqrt(-1)", "asin(2)", ""]


def expressions(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from expressions(x)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in SKIP:
                yield from expressions(x)


def number(v):
    return v if isinstance(v, str) else float(v)


def case(tree, values):
    env = names(tree, values)
    exprs = sorted({e for e in expressions(tree["ops"]) if "@" not in e and not is_string(e)})
    exprs += [c["expr"] for c in tree["checks"]]
    out = []
    for text in exprs:
        for i in ((0, 1, 2) if _NAME_I.search(text) else (None,)):
            try:
                v = evaluate(text, env if i is None else dict(env, i=float(i)))
            except (ExprError, TypeError):
                continue
            out.append([text, i, number(v)])
    return {"values": values, "names": {k: number(v) for k, v in env.items()},
            "failed": failed_checks(tree, env), "exprs": out}


def main(out_dir, baseline=None):
    os.makedirs(out_dir, exist_ok=True)
    files, skipped = {}, []
    for key in sorted(available()):
        try:
            tree = export(key)
        except (NotRecordable, PrimError) as e:
            skipped.append(f"{key}: {e}")
            continue
        name = f"{key}.prim"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(dumps(tree))
        files[name] = [case(tree, {})] + [case(export(key, v), v) for v in VARIANTS.get(key, [])]
        if key in FAILING:
            files[name].append(case(tree, FAILING[key]))
            assert files[name][-1]["failed"], f"{key} {FAILING[key]} fails no check"
    from primlib.assemblies import available as assemblies
    from primlib.recipe import layout, leaf_parts, recipe_checks
    from primlib.recipes import available as recipes

    recipe_cases = {}
    for key in list(recipes()) + list(assemblies()):
        tree = export(key)
        name = f"{key}.prim"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(dumps(tree))
        recipe_cases[name] = []
        for values in [{}] + RECIPE_VARIANTS.get(key, []):
            failed = recipe_checks(tree, values)
            placed = [] if failed else [[p.name, p.part, [list(r) for r in p.rotation], list(p.at)]
                                        for p in layout(tree, values)]
            leaves = {} if failed else leaf_parts(tree, values)
            parts = {k: v["values"] for k, v in leaves.items()}
            printed = sorted(k for k, v in leaves.items() if v["print"])
            recipe_cases[name].append({"values": values, "failed": failed, "parts": parts, "print": printed,
                                       "placed": placed})
    with open(os.path.join(out_dir, "recipes.json"), "w", encoding="utf-8") as f:
        json.dump(recipe_cases, f, indent=1, ensure_ascii=False)
        f.write("\n")
    for bad, env in [(b, {}) for b in ERRORS] + [(b, TEXT_ENV) for b in TEXT_ERRORS]:
        try:
            evaluate(bad, env)
        except ExprError:
            continue
        raise SystemExit(f"python evaluates {bad!r}: not an error case")
    text = {"env": TEXT_ENV, "cases": [[t, evaluate(t, TEXT_ENV)] for t in TEXT_CASES], "errors": TEXT_ERRORS}
    with open(os.path.join(out_dir, "cases.json"), "w", encoding="utf-8") as f:
        json.dump({"files": files, "errors": ERRORS, "text": text}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    if baseline:
        with open(baseline, encoding="utf-8") as f:
            base = json.load(f)
        fc = {f"{k}.prim": {"volume": v["volume"], "box": v["box"], "solids": v["solids"]}
              for k, v in sorted(base.items()) if f"{k}.prim" in files}
        with open(os.path.join(out_dir, "freecad.json"), "w", encoding="utf-8") as f:
            json.dump(fc, f, indent=1)
            f.write("\n")
        print(f"freecad.json: {len(fc)} primitives from {baseline}")
    n = sum(len(c["exprs"]) for cs in files.values() for c in cs)
    print(f"{len(files)} files, {n} expression values, {len(ERRORS)} error cases, "
          f"{len(recipe_cases)} recipes -> {out_dir}")
    for s in skipped:
        print(f"  skipped {s}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fixtures", sys.argv[2] if len(sys.argv) > 2 else None)
