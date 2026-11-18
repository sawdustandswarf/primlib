"""Every recipe and assembly built in FreeCAD (primlib/recipe_freecad.py)
against primlib/recipe.py's layout, its reference: the links shown (in a
joint's App::Part too), their masters and places, the Status cell and the
print list.

    tools/run.sh tools/recipe_check.py

For each recipe: built at its defaults, then its sheet cells changed to
other values (tools/view4d_fixtures.py's RECIPE_VARIANTS) and recomputed,
without building again: the layout must follow. Then saved, opened again
and checked once more (FreeCAD has dropped parentheses on saving).
"""

import os
import sys
import tempfile

import FreeCAD as App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from primlib.core import document_sheet  # noqa: E402
from primlib.prim import export  # noqa: E402
from primlib.assemblies import available as assemblies  # noqa: E402
from primlib.recipe import layout, leaf_parts, recipe_checks  # noqa: E402
from primlib.recipe_freecad import make_recipe, placed, print_list  # noqa: E402
from primlib.recipes import available  # noqa: E402
from tools.view4d_fixtures import RECIPE_VARIANTS  # noqa: E402


def close(a, b):
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def compare(tree, name, doc, values):
    """Differences between FreeCAD's links and layout() at `values`."""
    sheet = document_sheet(doc)
    group = doc.getObject(name)
    failed = recipe_checks(tree, values)
    status = sheet.get(f"{name}_Status")
    if failed:
        return [] if status == failed[0] else [f"Status {status!r}, want {failed[0]!r}"]
    if status != "OK":
        return [f"Status {status!r}, want 'OK'"]
    leaves = leaf_parts(tree, values)
    master = {k: f"{name} {k}" + (" mirrored" if v["mirror"] else "") for k, v in leaves.items()}
    want = [(p.name, master[p.part], p.rotation, p.at) for p in layout(tree, values)]
    got = placed(group)
    out = []
    printed = sorted(master[k] for k, v in leaves.items() if v["print"])
    if print_list(doc, name) != printed:
        out.append(f"print list {print_list(doc, name)}, want {printed}")
    if [w[:2] for w in want] != [g[:2] for g in got]:
        return [f"links {[g[:2] for g in got]}, want {[w[:2] for w in want]}"]
    for (label, _, wr, wa), (_, _, gr, ga) in zip(want, got):
        if not all(close(a, b) for a, b in zip(sum(wr, ()), sum(gr, ()))) or not all(
                close(a, b) for a, b in zip(wa, ga)):
            out.append(f"{label}: {gr} {ga}, want {wr} {wa}")
    return out


def set_values(tree, name, doc, values):
    """The recipe's cells changed to `values` (the rest back to defaults)."""
    sheet = document_sheet(doc)
    for p in tree["params"]:
        v = str(values.get(p["name"], p["default"]))
        cell = sheet.getCellFromAlias(f"{name}_{p['name']}")
        sheet.set(cell, v if v.startswith("'") else "=" + v.lstrip("="))
    doc.recompute()


lines, bad, n = [], 0, 0
tmp = tempfile.mkdtemp()
for key in list(available()) + list(assemblies()):
    tree = export(key)
    name = "".join(w.title() for w in key.split("_"))
    doc = App.newDocument(f"recipe_{key}")
    make_recipe(tree, doc, name)
    runs = [{}] + RECIPE_VARIANTS.get(key, []) + [{}]
    for values in runs:
        set_values(tree, name, doc, values)
        diff = compare(tree, name, doc, values)
        n += 1
        bad += bool(diff)
        lines += [f"  {key} {values}: {d}" for d in diff]
    path = os.path.join(tmp, f"{key}.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    doc = App.openDocument(path)
    doc.recompute()
    for values in runs[1:2] + [{}]:
        set_values(tree, name, doc, values)
        diff = compare(tree, name, doc, values)
        n += 1
        bad += bool(diff)
        lines += [f"  {key} {values}, reopened: {d}" for d in diff]
    App.closeDocument(doc.Name)
    os.remove(path)
os.rmdir(tmp)
lines.insert(0, f"{n} layouts compared, {bad} differ")
os.write(1, ("\n".join(lines) + "\n").encode())
