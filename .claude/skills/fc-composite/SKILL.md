---
name: fc-composite
description: >
  How to put primlib primitives together into a composite: a recipe (primlib/recipe.py,
  primlib/recipes/) that places primitives as parts (a row by key, a series, a choice, a
  mirrored pair), or an assembly (primlib/assemblies/) that takes recipes as parts, with
  pieces of a compound, a print list and joints. Covers declaring and placing parts, live
  keys, counts and fallbacks, the Status check, moving parts on a joint, what the FreeCAD
  compiler (recipe_freecad.make_recipe) makes of it, and checking it (layout(),
  recipe_check, view4d). The hybrid case (primlib/assemblies/hybrid_case.py) is the worked
  example. Use when assembling primitives into a box, case or other composite, adding a part
  to one, or changing how its keys, counts or placement work.
---

# Building a composite

A composite puts many primitives together into one thing, such as the hybrid
case: a plywood case with printed corners, keyed edge runs, hinges and latches.
In primlib a composite is declared in Python, once, and runs on every target:

- a **recipe** places primitives as parts: a row of pieces by key, a length
  filled, a series, a mirrored pair, a choice;
- an **assembly** is a recipe whose parts may themselves be recipes or
  assemblies, with pieces of a compound, a print list and joints (a lid on its
  hinges).

It records as a `.prim` file (version 2, `docs/FORMAT.md#recipes`) that view4d
draws live, and `primlib/recipe_freecad.py` compiles it into a FreeCAD document
that stock FreeCAD recomputes by itself, tailored by editing its sheet.

The parts themselves are primitives (`fc-primitive`). This skill covers putting
them together. Read `primlib/recipe.py`'s docstrings, then the examples:
`primlib/recipes/edge_run.py` (a keyed run), `primlib/assemblies/hinged_lid.py`
(a small assembly with a joint) and `primlib/assemblies/hybrid_case.py` (the
whole case).

## 1. Where it goes

- **General patterns** (a run of edges by key, a pair of supports) go in
  `primlib/recipes/`, one class per file, named by its key.
- **Assemblies** go in `primlib/assemblies/` when they are examples of the
  library or general; one design's own composite stays in the project that uses
  it, built on primlib.

## 2. Declaring it

A `Recipe` (or `Assembly`) subclass declares what a primitive does, then its
parts and how they're placed:

- **`params`, `derived`, `checks`, `fixed`, `groups`,** as a primitive's: each
  `Param(name, default, note)`; each check an expression that must be over 0,
  with a message saying what to change. Put the composite's first order sizes
  (length, width, height, split, panel thickness) first, and keep them few.
- **`parts`:** each a `Part(name, primitive, bind, mirror=, colour=, pieces=,
  to_print=)`.
  - `bind` maps the primitive's parameters to expressions over the
    composite's names. Bind everything the composite decides; unbound
    parameters keep the primitive's defaults.
  - `pieces` takes some pieces of a compound (a hinge's `("side_a",)`), so a
    part that spans a joint can be split across it.
  - `to_print` puts the part on the print list; `colour` is (r, g, b), 0 to 1.
  - In an assembly, `primitive` may name a recipe or an assembly, laid out at
    its bound values.
- **`place(r)`** places the parts with the `Placer` `r` and returns the
  result:
  - `r.instance(name, part, at=, turn=)`: one part, at a place, turned about
    x, y or z (`turn=[("z", "90")]`);
  - `r.row(name, key, pieces, at=, along=, gap=, lead=, turn=)`: pieces end
    to end by a key, each letter a `(part, length)`;
  - `r.series(name, count, item)`: `item(i)` for i up to `count`;
  - `r.choose(guard, then, otherwise)`: one side or the other, by whether
    `guard` is over 0;
  - `r.group(name, of)`, `r.move(name, base, by=, turn=)`;
  - `r.joint(name, base, at, axis, angle)`: what turns, about a line, by a
    parameter that opens it.

Places and turns are expressions over the composite's names, so a change of
size lays out again. Work a step at a time: add one part type, check it
(section 5), then the next.

## 3. Live choices: keys, counts and options

The user changes the layout by editing values, never by editing the code.
- **Keys:** a string of letters per run (`'SFMF`), each letter a piece type
  (S, M, L fixed lengths, F a fit piece sharing what's left). The fit length
  and each piece's position are worked out in the expressions (see
  `edge_run.fit`).
- **Fallbacks:** a key whose fit piece would be too short falls back to a
  default key (`fallback`, under `min_fit`), so a smaller box still lays out.
- **Counts:** a series up to a count. In FreeCAD, keys and series hold at most
  `slots` pieces (8 unless the recipe says otherwise).
- **Options:** a switch (`rail_on`) chooses one set of parts or another. If
  the composite can't take the option, it drops it and says so.
- **Checks** become one `Status` cell in FreeCAD: `OK`, or the first check
  that fails, the parts' own checks included. Word each message as what to
  change.

## 4. Moving parts

- Put everything that moves together in a `r.joint(...)`, turned by a
  parameter (`open_angle`) about its line. In FreeCAD it becomes an `App::Part`
  turned by formulas over that angle.
- Place a part that spans the joint (a hinge, a latch) as two parts taking
  different `pieces` of the same primitive: one inside the joint and one
  outside it (`hinged_lid`: side A's leaf with the lid, side B and the pins
  with the base).
- In FreeCAD, a turn's angle (in `instance`, `row` or `move`) must be a plain
  number, because links are turned when they're made. A joint's angle, and
  everything else, follows the sheet.

## 5. Checking

- **The layout, in plain Python:** `layout(doc, values)` (`primlib/recipe.py`)
  gives every placed part and where it is, without FreeCAD. It's the reference
  the other targets are checked against. `tests/test_recipe.py` holds the unit
  tests (`python3 -m unittest discover tests`).
- **Look at it:** export it as a `.prim` file and open it in view4d, which
  draws it live; `--set name=value` tries other values, `--animate` sweeps one
  (a joint opening).
- **In FreeCAD:** `tools/run.sh tools/recipe_check.py` builds every recipe
  and assembly with `make_recipe`, checks the links shown, their masters and
  places, the Status cell and the print list against `layout()`, then changes
  the sheet cells to other values (`RECIPE_VARIANTS` in
  `tools/view4d_fixtures.py`) and recomputes, then saves, opens again and
  checks once more. Add variants for a new recipe there.
- **view4d's reader:** a new recipe or a change to one regenerates view4d's
  test data (`AGENTS.md`).
- **Try the extremes** of the first order sizes, the smallest box especially.
  Every key must still lay out, or the Status must say why it can't.
- **The hybrid case** also has `tools/case_check.py CASE.FCStd`, which
  compares it part by part with the original FreeCAD model of the case (not in
  this repository).
- **Gotchas in FreeCAD:**
  - Headless, `App::Link` reports `Visibility` False unless an expression sets
    it, so don't filter parts by it.
  - A cut result is a compound with no `CenterOfMass`, so compare its solids.
  - Links in a moved `App::Part` move; their masters don't.
  - FreeCAD drops the brackets in `(a ? 1 : 0) > 0` when it saves: write
    conditions as nested `test ? <<message>> : (...)` with plain comparisons.
    `recipe_check` reopens the saved file to catch this.
- `tools/check_portable.py` (fc-prototype's tools) must report stock FreeCAD
  only on a saved composite.

## 6. What the FreeCAD compiler makes

`make_recipe(tree, doc, name, sheet=, **values)` (`primlib/recipe_freecad.py`):
- every name of the composite is a sheet cell, aliased `{name}_{x}`, with the
  `Status` cell;
- each part is made **once**, as a master bound to the cells (mirrored by a
  `Part::Mirroring` if the part is), in the `{name} print list` group if it's
  to print, otherwise `{name} parts`;
- each placement is `App::Link`s to the masters: a row is one per slot and
  letter, shown (`Visibility`) when that slot holds that letter; a series is
  one per slot up to `slots`, shown while the count is over it; a choice shows
  one side or the other;
- a part that is itself a recipe or assembly has its own cells
  (`{name}_{part}_{x}`, bound to the outer ones) and masters, made once.

So a key, a count, a size or a joint's angle changed on the sheet lays out
again on recompute, without primlib installed.

## 7. Saving a composite from a script

When a project script saves the compiled document:
- Save through an offscreen GUI (`QT_QPA_PLATFORM=offscreen`,
  `FreeCADGui.showMainWindow()`), so `GuiDocument.xml` is kept. Otherwise
  FreeCAD shows every object, including every hidden link.
- Before saving: let the GUI make its views (`FreeCADGui.updateGui()`), apply
  each `Visibility` expression again, and set the groups' visibility before
  what's in them.
- Set an isometric view and fit all.
- Write printed output with `os.write(1, ...)`, close every document, then
  `os._exit(0)`. Print a summary the user can check without opening the file
  (the sizes, the keys in use and their fits, the Status, the print list),
  then `saved <path>`.
- Test on a copy in a scratch folder, never the project's own file, and close
  the file in FreeCAD before running the script.
- For a small change (a default, a key, one value), make the edit and recommend
  the complete build. Don't do scratch builds or add extras.
