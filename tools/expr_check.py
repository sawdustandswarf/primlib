"""Every expression of every recorded primitive, evaluated by FreeCAD (on a
sheet, at the defaults) and by primlib/expr.py: they must agree. So must
TEXT_CASES, written for FreeCAD by expr.freecad, in a file saved and opened
again (FreeCAD has dropped parentheses on saving).

    tools/run.sh tools/expr_check.py
"""

import os
import sys
import tempfile

import FreeCAD as App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import primlib as lib  # noqa: E402
from primlib.core import document_sheet, expand, value  # noqa: E402
from primlib.expr import ExprError, evaluate, freecad, is_string, names  # noqa: E402
from primlib.targets.record import NotRecordable, record  # noqa: E402
from tools.text_cases import TEXT_CASES, TEXT_ENV  # noqa: E402

SKIP = {"op", "name", "axis", "plane", "join", "index"}


def expressions(v):
    """The expression strings in a recorded operation tree."""
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from expressions(x)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in SKIP:
                yield from expressions(x)


def close(a, b):
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


lines, total, bad = [], 0, 0
for key, cls in sorted(lib.available().items()):
    try:
        tree = record(cls)
    except NotRecordable:
        continue
    py = names(tree)
    doc = App.newDocument(f"expr_{key}")
    sheet = document_sheet(doc)
    env = cls.bind(sheet, prefix="P_")
    doc.recompute()
    cases = [(n, env[n]) for n, v in py.items() if not isinstance(v, str)]
    exprs = {e for e in expressions(tree["ops"]) if "@" not in e and not is_string(e)}
    exprs |= {c["expr"] for c in tree["checks"]}
    cases += [(e, None) for e in sorted(exprs)]
    n = 0
    for text, fc_expr in cases:
        local = dict(py, i=0.0)
        try:
            want = evaluate(text, local)
        except ExprError as e:
            if "is text, not a number" in str(e):
                continue  # a text name in arithmetic: FreeCAD's own business
            bad += 1
            lines.append(f"  {key}: {text}: python can't: {e}")
            continue
        if isinstance(want, str):
            continue
        got = value(sheet, fc_expr if fc_expr is not None else expand(text, dict(env, i="0")))
        n += 1
        if not close(want, got):
            bad += 1
            lines.append(f"  {key}: {text}: python {want!r}, FreeCAD {got!r}")
    total += n
    App.closeDocument(doc.Name)

path = os.path.join(tempfile.mkdtemp(), "text_check.FCStd")
doc = App.newDocument("text_check")
sheet = doc.addObject("Spreadsheet::Sheet", "S")
for row, (k, v) in enumerate(TEXT_ENV.items(), 1):
    sheet.set(f"A{row}", f"'{v}" if isinstance(v, str) else str(v))
    sheet.setAlias(f"A{row}", k)
for row, text in enumerate(TEXT_CASES, 1):
    sheet.set(f"B{row}", "=" + freecad(text, 8))
doc.recompute()
doc.saveAs(path)
App.closeDocument(doc.Name)
doc = App.openDocument(path)
sheet = doc.getObject("S")
doc.recompute()
for row, text in enumerate(TEXT_CASES, 1):
    want = evaluate(text, TEXT_ENV)
    try:
        got = sheet.get(f"B{row}")
    except Exception as e:  # noqa: BLE001 - FreeCAD's error, reported
        got = f"error: {e}"
    got = float(got) if isinstance(got, bool) else getattr(got, "Value", got)
    total += 1
    same = got == want if isinstance(want, str) or isinstance(got, str) else close(want, got)
    if not same:
        bad += 1
        lines.append(f"  text: {text}: python {want!r}, FreeCAD {got!r}")
App.closeDocument(doc.Name)
os.remove(path)
os.rmdir(os.path.dirname(path))
lines.insert(0, f"{total} expressions compared, {bad} differ")
os.write(1, ("\n".join(lines) + "\n").encode())
