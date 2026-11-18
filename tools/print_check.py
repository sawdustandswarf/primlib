"""Print check for a prototype's parts, each as it sits on the bed.

    FILE=File.FCStd GROUP=Print tools/run.sh tools/print_check.py
    FILE=File.FCStd OBJECTS=Name1,Name2 tools/run.sh tools/print_check.py
    optional: MAX_OVERHANG=45  RATE=15 (cm3 per hour)  DENSITY=1.27 (g/cm3, PETG)

For each part: valid, number of solids, size, the steepest downward-facing
surface off the bed (degrees past vertical; the bed is the part's lowest z),
the overhang's height above the bed, volume, mass and a rough print time.
Ends with PASS or FAIL. FreeCAD exits 0 either way, so read that line.

The time is volume / RATE. 15 cm3 an hour comes from a real print (a 45 cm3 test
socket took three hours); slice it to know properly.
"""

import math
import os
import sys

import FreeCAD as App
import Part

ENV = os.environ
LIMIT = float(ENV.get("MAX_OVERHANG", "45"))
RATE = float(ENV.get("RATE", "15"))
DENSITY = float(ENV.get("DENSITY", "1.27"))
GRID = 9


def steepest_overhang(shape):
    """(degrees past vertical, height of that point above the bed)."""
    z_bed = shape.BoundBox.ZMin
    worst, at = 0.0, 0.0
    for face in shape.Faces:
        u0, u1, v0, v1 = face.ParameterRange
        for i in range(GRID):
            for j in range(GRID):
                u = u0 + (u1 - u0) * i / (GRID - 1)
                v = v0 + (v1 - v0) * j / (GRID - 1)
                if not face.isPartOfDomain(u, v):
                    continue
                p = face.valueAt(u, v)
                if p.z < z_bed + 1e-6:
                    continue
                n = face.normalAt(u, v)
                if n.z < -1e-6:
                    angle = math.degrees(math.asin(min(1.0, -n.z)))
                    if angle > worst:
                        worst, at = angle, p.z - z_bed
    return worst, at


def parts(doc):
    if ENV.get("OBJECTS"):
        return [doc.getObject(n) or doc.getObjectsByLabel(n)[0] for n in ENV["OBJECTS"].split(",")]
    want = ENV.get("GROUP", "Print")
    group = doc.getObject(want) or next(iter(doc.getObjectsByLabel(want)), None)
    if group is None or not hasattr(group, "Group"):
        groups = [f"{o.Name} ({o.Label})" for o in doc.Objects if o.TypeId == "App::DocumentObjectGroup"]
        raise SystemExit(f"no group {want!r}; groups: {', '.join(groups) or 'none'}; or set OBJECTS")
    out = []
    for o in group.Group:
        if o.TypeId == "App::DocumentObjectGroup":
            out += [c for c in o.Group if hasattr(c, "Shape")]
        elif hasattr(o, "Shape"):
            out.append(o)
    return out


def main():
    doc = App.openDocument(os.path.abspath(ENV["FILE"]))
    failed = []
    total = 0.0
    for o in parts(doc):
        shape = Part.getShape(o)
        if shape.isNull() or not shape.Solids:
            print(f"{o.Label}: no solid")
            failed.append(o.Label)
            continue
        bb = shape.BoundBox
        over, height = steepest_overhang(shape)
        vol = shape.Volume / 1000
        total += vol
        ok = shape.isValid() and over <= LIMIT + 1e-3
        if not ok:
            failed.append(o.Label)
        print(f"{o.Label}: valid {shape.isValid()}, {len(shape.Solids)} solid(s), "
              f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}, "
              f"overhang {over:.1f} deg at {height:.1f} up, "
              f"{vol:.2f} cm3, {vol * DENSITY:.1f} g, ~{vol / RATE * 60:.0f} min"
              + ("" if ok else "  <-- FAIL"))
    print(f"total {total:.2f} cm3, {total * DENSITY:.1f} g, ~{total / RATE * 60:.0f} min at {RATE:g} cm3/h")
    print("PASS" if not failed else f"FAIL: {', '.join(failed)} (overhang over {LIMIT:g} deg, or invalid)")


try:
    main()
except SystemExit as stop:
    print(f"FAIL: {stop}")
except Exception:
    import traceback
    traceback.print_exc(file=sys.stdout)
    print("FAIL: error")
sys.stdout.flush()
os._exit(0)
