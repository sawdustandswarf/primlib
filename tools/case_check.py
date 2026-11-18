"""The hybrid case assembly (primlib/assemblies/hybrid_case.py) built in
FreeCAD against the original FreeCAD model of the case it rewrites
(HybridCaseComponents10.FCStd, not in this repository): every part shown, by name, the same volume
and the same bounds where it is placed.

    tools/run.sh tools/case_check.py CASE.FCStd

At the defaults, then with the lid open, other keys and another length,
the rail off, and a box narrow enough to drop the rail (VARIANTS: the same
change made to the case's sheets and to the assembly's values). The case
file is copied to a temporary folder and the copy opened; the original is
never opened, let alone saved. Every part the case shows is compared.
"""

import os
import re
import shutil
import sys
import tempfile

import FreeCAD as App
import Part

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from primlib.prim import export  # noqa: E402
from primlib.recipe_freecad import make_recipe  # noqa: E402

LATER = ()      # the case's parts the assembly doesn't hold yet

# (the assembly's values, the case's cells as (sheet, alias, formula), the case's lid angle)
VARIANTS = [
    ({}, [], 0),
    ({"open_angle": "60", "key_x": "'SFMF", "key_z_upper": "'SF", "key_rail": "'SFM", "key_hinge": "'TSFMT",
      "length": "400"},
     [("Corners", "EdgeX_Key", "'SFMF"), ("Corners", "EdgeZUpper_Key", "'SF"), ("Corners", "Rail_Key", "'SFM"),
      ("Corners", "Hinge_Key", "'TSFMT"),
      ("PrimaryDimensions", "Length", "=400 mm")], 60),
    ({"rail_on": "0"}, [("Corners", "RailOn", "=0")], 0),
    ({"width": "180"}, [("PrimaryDimensions", "Width", "=180 mm")], 0),
]


def shown(o):
    for path, expr in o.ExpressionEngine:
        if path == "Visibility":
            return bool(o.evalExpression(expr))
    return bool(o.Visibility) if o.TypeId == "App::Link" else True


def measure(group):
    """{label: (volume, bounds)} of every part shown under `group`, placed
    through the App::Parts it is in."""
    out = {}

    def walk(o, chain, vis):
        if o.TypeId == "App::DocumentObjectGroup":
            for c in o.Group:
                walk(c, chain, vis)
            return
        if o.TypeId == "App::Part":
            for c in o.Group:
                walk(c, chain.multiply(o.Placement), vis and shown(o))
            return
        if not (vis and shown(o)):
            return
        s = Part.getShape(o, transform=True).copy()
        s.Placement = chain.multiply(s.Placement)
        b = s.BoundBox
        out[o.Label] = (s.Volume, (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))

    walk(group, App.Placement(), True)
    return out


def case_name(label):
    """The case's name for an assembly's label: its edge, rail and hinge
    pieces are named by run and slot (Edge_X_Top_Front_1F, Hinge_2F_lid)."""
    label = re.sub(r"/lidhinge_(\w+)$", r"_\1_lid", label)
    return re.sub(r"/(edge|rail|hinge)_", "_", label)


def compare(case_path, values, cells, angle):
    tmp = tempfile.mkdtemp()
    copy = os.path.join(tmp, "case.FCStd")
    shutil.copy(case_path, copy)
    case = App.openDocument(copy)
    for name, alias, formula in cells:
        sheet = case.getObject(name)
        sheet.set(sheet.getCellFromAlias(alias), formula)
    case.getObject("Lid").OpenAngle = angle
    case.recompute()
    want = measure(case.getObject("Assembly"))
    App.closeDocument(case.Name)
    shutil.rmtree(tmp)

    doc = App.newDocument("hybrid_case")
    group = make_recipe(export("hybrid_case"), doc, "HybridCase", **values)
    got = {case_name(label): v for label, v in measure(group).items()}
    App.closeDocument(doc.Name)

    later = sorted(k for k in want if LATER and k.startswith(LATER))
    lines, bad = [], 0
    for name in sorted(set(want) - set(later) | set(got)):
        if name not in got or name not in want:
            lines.append(f"  {name}: {'not in the assembly' if name in want else 'not in the case'}")
            bad += 1
            continue
        (wv, wb), (gv, gb) = want[name], got[name]
        if abs(wv - gv) > 1e-6 * max(1.0, wv) or any(abs(a - b) > 1e-4 for a, b in zip(wb, gb)):
            lines.append(f"  {name}: volume {gv:.3f}, bounds {tuple(round(x, 4) for x in gb)}; "
                         f"the case {wv:.3f}, {tuple(round(x, 4) for x in wb)}")
            bad += 1
    lines.insert(0, f"{values or 'defaults'}: {len(got)} parts compared with the case, {bad} differ; "
                    f"{len(later)} of the case's for later")
    return lines


if len(sys.argv) < 2:
    sys.exit("usage: tools/run.sh tools/case_check.py CASE.FCStd")
out = []
for values, cells, angle in VARIANTS:
    out += compare(sys.argv[1], values, cells, angle)
os.write(1, ("\n".join(out) + "\n").encode())
