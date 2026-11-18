"""For every primitive that exports: build it with make(), and from its
.prim file with replay(), at the defaults and at the values in CASES; the
two must agree (valid, solids, volume, bounding box).

    tools/run.sh tools/replay_check.py
"""

import os
import sys
import tempfile

import FreeCAD as App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import primlib as lib  # noqa: E402
from primlib.prim import export, replay, save  # noqa: E402
from primlib.targets.record import NotRecordable  # noqa: E402

# Values that take the branches the defaults don't (choose, series, rounds).
CASES = [
    ("rail15", {"base_width": "30"}), ("rail15", {"end_taper": "0.3"}),
    ("topeak_rail", {"base_width": "70", "end_taper": "0.3"}),
    ("rail15_housing", {"clearance": "0.1", "end_taper": "0.3"}),
    ("topeak_rail_housing", {"clearance": "1.0"}),
    ("rotary_latch", {"clearance": "0.15"}), ("support_half", {"radius": "20"}),
]


def measure(make):
    doc = App.newDocument("replay")
    try:
        obj = make(doc)
        doc.recompute()
        if obj is None:
            return {"built": False}
        s, bb = obj.Shape, obj.Shape.BoundBox
        return {"valid": s.isValid(), "solids": len(s.Solids), "volume": s.Volume,
                "box": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax]}
    finally:
        App.closeDocument(doc.Name)


def same(a, b):
    if a.keys() != b.keys() or a.get("built", True) != b.get("built", True):
        return False
    if "volume" not in a:
        return True
    return (a["valid"] == b["valid"] and a["solids"] == b["solids"]
            and abs(a["volume"] - b["volume"]) <= 1e-6 * max(1, abs(a["volume"]))
            and all(abs(x - y) <= 1e-6 for x, y in zip(a["box"], b["box"])))


cases = []
for key, cls in lib.available().items():
    try:
        export(key)
    except NotRecordable:
        continue
    cases.append((key, {}))
cases += CASES

lines, bad = [], 0
with tempfile.TemporaryDirectory() as tmp:
    for key, values in cases:
        path = os.path.join(tmp, f"{key}.prim")
        save(export(key, values), path)
        want = measure(lambda doc: lib.make(key, doc, "P", **values))
        got = measure(lambda doc: replay(path, doc, "P"))
        label = key + "".join(f" {k}={v}" for k, v in values.items())
        if same(want, got):
            lines.append(f"  same   {label}: volume {want.get('volume', 0):.4f}")
        else:
            bad += 1
            lines.append(f"  DIFFER {label}: make {want}, replay {got}")
lines.insert(0, f"{len(cases)} builds compared, {bad} differ")
os.write(1, ("\n".join(lines) + "\n").encode())
