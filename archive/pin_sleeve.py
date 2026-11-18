r"""
================================================================================
PIN_SLEEVE -- parametric pin + sleeve document (spreadsheet-driven)
================================================================================

`pin_sleeve.py` assembles the two library parts into one FreeCAD document
driven by an aliased spreadsheet: a `Spreadsheet::Sheet` named `Params`
holds every parameter (five inputs and six derived values), and every
primitive property that depends on a parameter is bound to those aliases
through the expression engine. Edit a cell, recompute, and the whole
document follows.

Layout of the document (three groups spaced 25 mm apart along +x):

     PIN                 SLEEVE              STRUCTURE
   free-standing      free-standing     sleeve on pin, sliced
     (x = 0)            (x = 25)         down the axis (x = 50)

        |                /\    /\            /--|
        |               /  \  /  \          / / |
        |               |    ||  |         / / |
        |               |    ||  |        | | /
         \               \  /\  /         | | |
          \               \/  \/          | |/
     z = 0 .. h         z = 0 .. h     z = 0 .. h, both parts
      flare/shaft       W barrel        on one axis, cut in half

  * PIN       one retained pin, free standing
  * SLEEVE    one sleeve, free standing
  * STRUCTURE a second pin + sleeve pair assembled on a common axis and
              sliced down the centre (inspection_section from
              `sleeve.py`), so the fit -- throat, flares, clearance --
              is visible from outside

Coordinate convention
---------------------
  As in `pin_retained.py` / `sleeve.py`: z along the pin axis, each part
  spanning z = 0 .. h. The three groups sit at x = 0 / 25 / 50.

Spreadsheet `Params` (aliases)
------------------------------
  Inputs (edit these):

    pd       6.0    pin shaft diameter                   (mm)
    rd       10.0   pin retain (flare) diameter          (mm)
    hgt      10.0   pin / sleeve height -- one segment   (mm)
    kd       13.0   sleeve outside diameter              (mm)
    tol      0.1    running clearance, pin -> bore       (mm)

  The height alias is `hgt` rather than the house symbol `h` because the
  expression engine reserves a bare `h` as the hour unit.

  Derived (formula cells; kept in step automatically):

    c_b       (rd - pd) / 2                flare cone height (45 deg)
    outer_rad kd / 2                       sleeve outside radius
    flare_rad rd / 2 + tol                 bore radius at the end faces
    throat_rad pd / 2 + tol                bore radius at the waist
    a         (flare_rad + outer_rad) / 2  ridge ring radius (auto)
    rim_h     outer_rad - a                45-degree end-flank height

Parametric binding
------------------
After the parts are built, `_bind_pin()` / `_bind_sleeve()` walk the
construction objects the library modules create (`{name}_shaft`,
`{name}_bot_core`, ...) and bind their dimensions -- including the
`Placement.Base.z` sub-properties of the cones -- to the spreadsheet,
e.g. `Pin_shaft.Radius = Params.pd / 2`. The cutting box of
`inspection_section()` is bound too, so the section keeps covering the
parts when they grow. The bindings follow the construction-object
naming of `pin_retained.py` / `sleeve.py`, so the three files must stay
in step.

Note: the parameter *validity* checks live in the part modules and run
at build time; editing the sheet afterwards bypasses them -- keep
`pd < rd` and the other ranges listed in those modules.

API
----
  parameters(doc)
      Create the aliased `Params` spreadsheet in `doc`; returns the five
      input values as a dict keyed by alias.

  pin_sleeve_document(doc_name="PinSleeveDoc")
      Create and populate the whole document; returns it.

Run this file directly (freecadcmd pin_sleeve.py) to build the document
with the default parameters, save it as `pin_sleeve.FCStd` beside this
module, and open that file in the FreeCAD GUI -- a headless run would
throw the document away on exit. Without a `freecad` launcher on PATH
the document is still saved and its path printed.
================================================================================
"""

import os
import sys

import FreeCAD as App

from pin_retained import pin_retained
from sleeve import sleeve, inspection_section

SHEET = "Params"            # internal name of the spreadsheet (used in expressions)
SPACING = 25.0              # x offset between the three groups (mm)
OUTPUT = "pin_sleeve.FCStd" # saved beside the module on a direct run
GUI = "freecad"             # FreeCAD GUI launcher used to view a saved document

# (row, symbol, content, alias, note) -- inputs first, then formula cells.
PARAMETERS = (
    (2, "pd", "6.0", "pd", "pin shaft diameter"),
    (3, "rd", "10.0", "rd", "pin retain (flare) diameter"),
    (4, "h", "10.0", "hgt", "pin / sleeve height -- one segment"),
    (5, "kd", "13.0", "kd", "sleeve outside diameter"),
    (6, "tol", "0.1", "tol", "running clearance, pin -> bore"),
    (8, "c_b", "=(rd - pd) / 2", "c_b", "flare cone height (45 deg)"),
    (9, "outer_rad", "=kd / 2", "outer_rad", "sleeve outside radius"),
    (10, "flare_rad", "=rd / 2 + tol", "flare_rad",
         "bore radius at the end faces"),
    (11, "throat_rad", "=pd / 2 + tol", "throat_rad",
         "bore radius at the waist"),
    (12, "a", "=(flare_rad + outer_rad) / 2", "a", "ridge ring radius (auto)"),
    (13, "rim_h", "=outer_rad - a", "rim_h", "45-degree end-flank height"),
)
INPUT_ALIASES = ("pd", "rd", "hgt", "kd", "tol")


def _bind(obj, props):
    """Bind object properties (incl. Placement sub-properties) to Params.

    Values are fully qualified expressions such as "Params.pd / 2".
    """
    for prop, expr in props.items():
        obj.setExpression(prop, expr)


def _bind_pin(doc, name,
              pd=f"{SHEET}.pd", rd=f"{SHEET}.rd", h=f"{SHEET}.hgt"):
    """Bind a pin_retained() build (`name` and its children) to Params.

    `pd` / `rd` / `h` are expressions; the sleeve's internal void passes
    the tolerance-grown ones (pd + 2*tol, rd + 2*tol).
    """
    cone_h = f"(({rd}) - ({pd})) / 2"
    _bind(doc.getObject(f"{name}_bottom"),
          {"Radius1": f"({rd}) / 2", "Radius2": f"({pd}) / 2",
           "Height": cone_h})
    _bind(doc.getObject(f"{name}_shaft"),
          {"Radius": f"({pd}) / 2",
           "Height": f"({h}) - 2 * ({cone_h})",
           "Placement.Base.z": cone_h})
    _bind(doc.getObject(f"{name}_top"),
          {"Radius1": f"({pd}) / 2", "Radius2": f"({rd}) / 2",
           "Height": cone_h,
           "Placement.Base.z": f"({h}) - ({cone_h})"})


def _bind_sleeve(doc, name):
    """Bind a sleeve() build (`name`, its children and its void) to Params."""
    outer_rad, a, rim_h = (f"{SHEET}.outer_rad", f"{SHEET}.a", f"{SHEET}.rim_h")
    h = f"{SHEET}.hgt"

    _bind(doc.getObject(f"{name}_body"), {"Radius": outer_rad, "Height": h})

    _bind(doc.getObject(f"{name}_bot_core"), {"Radius1": a, "Height": a})
    _bind(doc.getObject(f"{name}_bot_rim_cyl"),
          {"Radius": outer_rad, "Height": rim_h})
    _bind(doc.getObject(f"{name}_bot_rim_cone"),
          {"Radius1": a, "Radius2": outer_rad, "Height": rim_h})

    _bind(doc.getObject(f"{name}_top_core"),
          {"Radius2": a, "Height": a, "Placement.Base.z": f"{h} - {a}"})
    _bind(doc.getObject(f"{name}_top_rim_cyl"),
          {"Radius": outer_rad, "Height": rim_h,
           "Placement.Base.z": f"{h} - {rim_h}"})
    _bind(doc.getObject(f"{name}_top_rim_cone"),
          {"Radius1": outer_rad, "Radius2": a, "Height": rim_h,
           "Placement.Base.z": f"{h} - {rim_h}"})

    # The bore is the toleranced pin; its cone height is still (rd - pd)/2.
    _bind_pin(doc, f"{name}_internal_void",
              pd=f"{SHEET}.pd + 2 * {SHEET}.tol",
              rd=f"{SHEET}.rd + 2 * {SHEET}.tol")


def _bind_section(doc):
    """Bind inspection_section()'s cutting box so it keeps covering the parts."""
    outer_rad, h = f"{SHEET}.outer_rad", f"{SHEET}.hgt"
    _bind(doc.getObject("InspectionSliceBox"),
          {"Length": f"2 * 3 * {outer_rad}", "Width": f"3 * {outer_rad}",
           "Height": f"4 * {h}",
           "Placement.Base.x": f"-3 * {outer_rad}",
           "Placement.Base.y": f"-3 * {outer_rad}",
           "Placement.Base.z": f"-3 * {outer_rad}"})


def parameters(doc):
    """Create the aliased `Params` spreadsheet in `doc`.

    Returns the five input values as a dict keyed by alias
    (pd, rd, hgt, kd, tol).
    """
    sheet = doc.addObject("Spreadsheet::Sheet", SHEET)
    sheet.Label = "Parameters"

    sheet.set("A1", "PIN + SLEEVE PARAMETERS")
    sheet.set("A2", "symbol")
    sheet.set("B2", "value")
    sheet.set("C2", "note")
    sheet.set("A7", "derived (formulas)")
    for row, symbol, content, alias, note in PARAMETERS:
        sheet.set(f"A{row}", symbol)
        sheet.set(f"B{row}", content)
        sheet.setAlias(f"B{row}", alias)
        sheet.set(f"C{row}", note)

    doc.recompute()
    return {alias: sheet.get(f"B{row}")
            for row, _, _, alias, _ in PARAMETERS
            if alias in INPUT_ALIASES}


def pin_sleeve_document(doc_name="PinSleeveDoc"):
    """Create and populate the parametric pin + sleeve document."""
    doc = App.newDocument(doc_name)
    values = parameters(doc)
    pd, rd = values["pd"], values["rd"]
    h, kd, tol = values["hgt"], values["kd"], values["tol"]

    # 1. free-standing pin                      2. free-standing sleeve
    pin = pin_retained(doc, "Pin", h, pd, rd)
    slv = sleeve(doc, "Sleeve", h, pd, rd,
                 diam_outer=kd, tolerance=tol)

    # 3. assembled + sectioned pin/sleeve structure
    s_pin = pin_retained(doc, "StructurePin", h, pd, rd)
    s_slv = sleeve(doc, "StructureSleeve", h, pd, rd,
                   diam_outer=kd, tolerance=tol)
    pin_half, slv_half = inspection_section(doc, s_pin, s_slv, h, kd)

    # Space the three groups along +x.
    pin.Placement.Base = App.Vector(0.0, 0.0, 0.0)
    slv.Placement.Base = App.Vector(SPACING, 0.0, 0.0)
    pin_half.Placement.Base = App.Vector(2.0 * SPACING, 0.0, 0.0)
    slv_half.Placement.Base = App.Vector(2.0 * SPACING, 0.0, 0.0)

    # Drive everything from the spreadsheet.
    _bind_pin(doc, "Pin")
    _bind_sleeve(doc, "Sleeve")
    _bind_pin(doc, "StructurePin")
    _bind_sleeve(doc, "StructureSleeve")
    _bind_section(doc)

    doc.recompute()
    return doc


# ==========================================
# MODULE TESTING AND EXECUTION ENTRY POINT
# ==========================================
def _is_main():
    """True when this file is the one FreeCAD was asked to run.

    freecadcmd executes a file with __name__ set to the script's basename
    (not '__main__'), so compare the file against sys.argv as well; that
    way importing the module never fires the entry point.
    """
    if __name__ == "__main__":
        return True
    try:
        return (len(sys.argv) > 1
                and os.path.samefile(__file__, os.path.abspath(sys.argv[1])))
    except OSError:
        return False


def _open_in_gui(path):
    """Hand a saved document to the FreeCAD GUI for viewing.

    Replaces this headless process with the GUI, which opens `path`;
    prints a note when no GUI launcher is on PATH.
    """
    App.Console.PrintMessage(f"opening {path} in the FreeCAD GUI\n")
    try:
        os.execvp(GUI, [GUI, path])
    except FileNotFoundError:
        App.Console.PrintError(
            f"no '{GUI}' launcher on PATH -- open {path} yourself\n")


if _is_main():
    doc = pin_sleeve_document()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT)
    doc.saveAs(out)
    # The document is regenerated from this module on every run, so the
    # .FCBak FreeCAD keeps when overwriting would only be clutter.
    folder = os.path.dirname(out)
    stem = os.path.splitext(os.path.basename(out))[0]
    for name in os.listdir(folder):
        if name.startswith(stem + ".") and name.endswith(".FCBak"):
            os.remove(os.path.join(folder, name))
    App.Console.PrintMessage(
        f"PinSleeveDoc built (defaults pd=6 rd=10 hgt=10 kd=13 tol=0.1)"
        f" and saved to {out}\n"
        "edit the Parameters spreadsheet and recompute.\n")
    if not App.GuiUp:
        _open_in_gui(out)
