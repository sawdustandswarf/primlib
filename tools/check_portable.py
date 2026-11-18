#!/usr/bin/env python3
"""What a saved FreeCAD file needs beyond stock FreeCAD, and how its sheets
handle tolerance and status.

    python3 tools/check_portable.py File.FCStd [More.FCStd ...]

Reads Document.xml from the zip; FreeCAD isn't needed. Reports:
  - Python feature modules (Part::FeaturePython and the like) the file needs to
    recompute, each marked as shipped with FreeCAD or as outside code;
  - objects that pick edges by number (Part::Chamfer, Part::Fillet), which can
    break when the shape resizes;
  - each sheet's tolerance-like aliases and status aliases.
Exit status 1 if any outside module is needed.
"""

import glob
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

SHIPPED_ROOTS = ["/usr/lib/freecad/Mod", "/usr/share/freecad/Mod", "/usr/lib/freecad/lib",
                 "/usr/share/freecad/Ext", "/usr/lib/freecad/Ext"]
USER_MODS = glob.glob(os.path.expanduser("~/.local/share/FreeCAD/*/Mod")) + \
    [os.path.expanduser("~/.FreeCAD/Mod")]
FRAGILE = {"Part::Chamfer", "Part::Fillet", "PartDesign::Chamfer", "PartDesign::Fillet"}
TOLERANCE = re.compile(r"tol|clearance|size_?offset|printer_width_offset", re.I)
STATUS = re.compile(r"status", re.I)


def found_in(roots, top):
    """The first root holding module `top`, directly or one workbench folder down."""
    for root in roots:
        for base in [root] + sorted(glob.glob(os.path.join(root, "*"))):
            for cand in (os.path.join(base, top + ".py"), os.path.join(base, top, "__init__.py"),
                         os.path.join(base, top)):
                if os.path.exists(cand) and (cand.endswith(".py") or os.path.isdir(cand)):
                    return base
    return None


def where(module):
    top = module.split(".")[0]
    if found_in(SHIPPED_ROOTS, top):
        return "shipped"
    hit = found_in(USER_MODS, top)
    if hit:
        return f"OUTSIDE (add-on: {hit})"
    return "OUTSIDE (not found)"


def check(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("Document.xml"))
    types = {o.get("name"): o.get("type") for o in root.iter("Object") if o.get("type")}
    modules = {}
    for obj in root.iter("Object"):
        name = obj.get("name")
        for py in obj.iter("Python"):
            mod, cls = py.get("module"), py.get("class")
            if mod:
                modules.setdefault((mod, cls), []).append(name)
    fragile = sorted(n for n, t in types.items() if t in FRAGILE)
    sheets = {}
    data = root.find("ObjectData")
    for obj in (data if data is not None else []):
        if types.get(obj.get("name")) != "Spreadsheet::Sheet":
            continue
        label = next((p.find("String").get("value") for p in obj.iter("Property")
                      if p.get("name") == "Label" and p.find("String") is not None), obj.get("name"))
        aliases = [c.get("alias") for c in obj.iter("Cell") if c.get("alias")]
        sheets[label] = aliases

    print(f"== {path}")
    outside = False
    if modules:
        print("Python features:")
        for (mod, cls), names in sorted(modules.items()):
            w = where(mod)
            outside |= w.startswith("OUTSIDE")
            print(f"  {w:30} {mod}.{cls}  x{len(names)}  e.g. {', '.join(names[:3])}")
    else:
        print("Python features: none")
    if fragile:
        print(f"Edges picked by number ({len(fragile)}): {', '.join(fragile[:8])}"
              + (" ..." if len(fragile) > 8 else ""))
    for label, aliases in sheets.items():
        tol = [a for a in aliases if TOLERANCE.search(a)]
        status = [a for a in aliases if STATUS.search(a)]
        print(f"Sheet {label}: {len(aliases)} aliases")
        print(f"  tolerance-like: {', '.join(tol) or 'none'}")
        print(f"  Clearance: {'yes' if 'Clearance' in aliases else 'no'}   "
              f"SizeOffset: {'yes' if 'SizeOffset' in aliases else 'no'}")
        print(f"  status: {', '.join(status) or 'none'}")
    print("RESULT:", "needs outside code" if outside else "stock FreeCAD only")
    return outside


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bad = [check(p) for p in sys.argv[1:]]
    sys.exit(1 if any(bad) else 0)
