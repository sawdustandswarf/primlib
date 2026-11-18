"""Build every primitive at its defaults and record what came out: valid,
volume, bounding box. A change that should leave the geometry alone (a
rename, a refactor, a new target) must leave this unchanged.

    tools/run.sh tools/baseline.py          # writes $BASELINE_OUT, or baseline.json here

Compare two runs with tools/baseline_diff.py (plain Python).
"""

import json
import os
import sys

import FreeCAD as App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import primlib as lib  # noqa: E402


def measure(key):
    doc = App.newDocument(f"baseline_{key}")
    try:
        obj = lib.make(key, doc, "P")
        doc.recompute()
        if obj is None:
            return {"built": False}
        s = obj.Shape
        b = s.BoundBox
        return {
            "built": True,
            "valid": s.isValid(),
            "solids": len(s.Solids),
            "volume": round(s.Volume, 6),
            "box": [round(v, 6) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)],
        }
    except Exception as e:  # noqa: BLE001 -- a primitive that throws is recorded, not fatal
        return {"built": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        App.closeDocument(doc.Name)


out = os.environ.get("BASELINE_OUT", os.path.join(ROOT, "baseline.json"))
results = {key: measure(key) for key in lib.primitives.available()}
with open(out, "w") as f:
    json.dump(results, f, indent=1, sort_keys=True)
App.Console.PrintMessage(f"baseline: {len(results)} primitives -> {out}\n")
