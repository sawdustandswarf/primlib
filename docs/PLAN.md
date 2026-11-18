# primlib — Plan

Status: `[x]` done · `[~]` in progress · `[ ]` not started.

primlib is a library of parametric primitives for printed parts with more than one
target: FreeCAD, and view4d (https://github.com/sawdustandswarf/view4d), which will draw
primitives from a file, move them in time, edit them and export them for printing. It
began as a copy of fc_lib, an earlier FreeCAD-only version of the same library.

Three layers: **primitives** (one part each), **recipes** (reusable patterns of
primitives: fill a length, a series, pick by key, mirror and pair) and
**assemblies** (a project such as the hybrid case: instances, placements, colours,
the print list, joints).

## P0 — The start

- [x] 0.1 A baseline: `tools/baseline.py` builds every primitive at its defaults and
  records valid, solids, volume and bounding box; `tools/baseline_diff.py` compares
- [x] 0.2 The package renamed from fc_lib's `fclib` to `primlib`, the workbench and
  commands `Primlib`, the build tag `PrimlibPrimitive` (the workbench still reads the
  older `FcLibPrimitive`). All 21 primitives identical to fc_lib's
  - freecadcmd loads a script by module name, add-on folders first: an installed add-on
    with a same-named script runs instead. `tools/run.sh` runs a file by its path

## P1 — Targets and a file format

- [x] 1.1 `Builder` becomes an operation interface with targets in
  `primlib/targets/`: `freecad.py` (today's code, unchanged geometry) and
  `record.py` (the operation tree, expressions unexpanded). `Builder(doc, ...)`
  picks the target by `doc` (a `Recording` records). Baseline unchanged.
  `tools/record_check.py` lists what records: 8 of 21 (box_edge, hinge,
  twist_plug, twist_socket and the four `Revolved`, which record as a `revolve`)
- [x] 1.2 No reaches past it: every build goes through `Builder`, so 19 of 21
  record (`tools/record_check.py`). New operations: `grid`, `move`, `extent`,
  `sector`, `polygon`, `part` (a nested primitive), `choose` (a guard and both
  branches) and `series` (a count and an item over the index `i`). The FreeCAD
  target evaluates `choose` and `series` when it builds, as before, and leaves a
  vertex of radius 0 or less sharp. Baseline unchanged, and every branch the
  defaults don't reach checked against the previous commit.
  - [ ] `latch` moves to `hinge`; then `hinge_deprecated` and `plate` go. Until
    then both are `freecad_only` (a geometry change: needs your go-ahead)
- [x] 1.3 `docs/EXPRESSIONS.md`: values, operators, functions (degrees), bounds
  `xmin(@id)`, names and their order. `primlib/expr.py` evaluates it in plain
  Python; `tests/test_expr.py` (no FreeCAD) and `tools/expr_check.py` (all 1453
  distinct expressions of the 19 recorded primitives agree with FreeCAD)
- [x] 1.4 `docs/FORMAT.md`: `.prim` version 1, JSON: the document (params,
  fixed, derived, checks, optional values, ops, result, empty motion) and every
  operation's fields and shape, with planes, angles and how readers treat
  `choose`, `series` and what they can't build
- [x] 1.5 `python3 -m primlib export KEY [--set name=value] -o FILE.prim` (also
  `list`, `check`), in plain Python: `core` no longer needs FreeCAD to load.
  `primlib/prim.py`: load, `build` through any Builder, `primitive(tree)` (a
  Primitive class), `replay` into FreeCAD. Checks: `tests/test_prim.py` (every
  primitive records again the same), `tools/replay_check.py` (make = export +
  replay for all 19 at the defaults and 7 branch cases), baseline unchanged

## P2 — Recipes and assemblies

- [x] 2.1 Recipes: fill a length (`spacing.py`, no slot limit), a series (`i`, `n`),
  pick by key, mirror and pair; live in view4d, compiled to slots and `Visibility`
  formulas in FreeCAD; `spacing()` the reference
  - [x] 2.1a Text in expressions, for keys: `<<…>>`, `+`, `==`/`!=`, `name[a:b]`,
    `name[k]`, `mod` (all FreeCAD's), and `len`, `count`, `repeat`, which FreeCAD
    hasn't: `expr.freecad(text, slots)` writes them out over a key's slots. Checked in
    FreeCAD after a save and reopen (`tools/expr_check.py`: 1473 agree), in
    `tests/test_expr.py`, and in view4d's reader (`tools/text_cases.py` into
    `cases.json`). FreeCAD slices only a name (`(key)[0:1]` fails) and gives `key[1:]`
    as empty: so the language slices names only, both ends written
  - [x] 2.1b Recipe documents (`.prim` version 2, `kind: recipe`): the primitives
    they use inside, `parts` (a primitive at bound values, mirrored or not, a colour),
    placed by `instance`, `row` (a key's letters end to end), `series`, `choose`,
    `group` and `move`. Fit lengths and keys are derived names. `primlib/recipe.py`
    (the class, its recorder, `layout` in plain Python: the reference), recipes
    `edge_fill` (a row whose key `spacing()`'s pattern makes: 85 layouts as
    `spacing()` gives them), `edge_run` (the original case's keyed run, its fallback key) and
    `support_pair` (mirror and pair). A part's own checks are the recipe's.
    `primlib export` and `check` take recipes
  - [x] 2.1c view4d reads recipes: each part built once at its values, placed.
    `tools/view4d_fixtures.py` writes the recipes and `recipes.json` (what `layout`
    places at the defaults and other values, the checks that fail); view4d places
    every part as `layout` does
  - [x] 2.1d The FreeCAD target compiles them (`primlib/recipe_freecad.py`,
    `make_recipe`): every name a cell (FreeCAD slices only a name), a master per part
    (mirrored by a Part::Mirroring), links per slot and letter with `Visibility` and
    placement formulas, a cell per row slot's start, a `Status` cell with every check,
    the parts' too. `tools/recipe_check.py`: built at the defaults, then the cells
    changed to other values and recomputed, saved and reopened: 21 layouts as `layout`
    gives them. FreeCAD can't parse conditionals nested ~57 deep (Status goes eight
    checks a cell) and left a cell stale that referred to one below it (the cells refer
    upwards). Turn angles are numbers there; a row or series inside a series isn't
    laid out there yet
- [x] 2.2 Assemblies: instances (primitive, recipe or assembly) with bound
  parameters, placements, colours, the print list and joints; the hybrid case as
  an assembly, rebuilt in FreeCAD with the same shapes
  - [x] 2.2a Assembly documents (`kind: assembly`): a recipe whose parts may be
    recipes or assemblies, a part may take some pieces of a compound (`pieces`: a
    hinge's `side_a`), parts marked to print, and a `joint` placement that turns what
    it holds about an axis by an angle expression (the lid). `layout` flattens it;
    view4d draws it
    - `primlib/assemblies/hinged_lid.py`, the example: two keyed edge runs, a hinge's
      side A with the lid run on a joint, side B and the pins with the base run.
      `leaf_parts` gives each primitive part by path; a recipe part to print prints
      all of it. view4d lays it out as `layout` does at every variant in
      `recipes.json`, and draws only the pieces a part takes
  - [x] 2.2b The FreeCAD target: nested recipes and assemblies, joints (an App::Part
    turned by formulas, as the original case's lid), the print list
    - A recipe part's cells and masters made once, its links laid out wherever it is
      placed (`lid_run/edge_1S`); a joint's App::Part turned by Roll/Pitch/Yaw and
      base formulas; a part of some pieces a Part::Compound of them (the hinge's two
      leaves sum to the whole); the print list a group of masters.
      `tools/recipe_check.py`: 28 layouts, hinged_lid's included, 0 differ
  - [x] 2.2c The hybrid case as an assembly (`primlib/assemblies/hybrid_case.py`):
    corners, panels and the keyed edges, against the parts measured from
    the original case's FreeCAD model (opened, never saved)
    - A `panel` primitive (a sheet cut to size, lying flat; the case turns it into
      its wall). `edge_run` passes box_edge's whole section and screws through, and
      takes `lead_gap` and `end_gap` (the Z runs end flush at the split); its
      defaults lay out as before. Everything above the split is on the `open`
      joint about the hinge line, at `-open_angle` as the original case's lid.
    - `tools/case_check.py`: built in FreeCAD and measured against a copy of the
      case (its rail off), by name, volume and placed bounds: 34 parts at the
      defaults and 50 with the lid open 60, other keys and length 400, 0 differ.
      view4d draws it in under a second
  - [x] 2.2d Its rail: sections by key, the notched and plain bottom edges, the ends
    - `rail_end`, a primitive: the original case's end piece (a notched box_edge fused to a
      topeak_rail tongue, the drop-on entry and screw rows cut), within 0.004 mm3 of
      the original's (its key widths rounded). It needed a `turn` operation (FORMAT.md),
      nested parts recorded in the outer names, and a fix to the FreeCAD target's
      `move` (it replaced an expression already on a base, not added to it: no
      primitive's geometry changed). `rail_run`, a recipe: keyed topeak_rail sections.
    - The case's bottom Y edges become plain, notched and end pieces while the rail
      shows; narrow, the rail drops and the notched pieces go; narrower, it's off.
      `tools/case_check.py`: 43 parts at the defaults, 61 open with other keys,
      34 rail off, 39 dropped, 0 differ
  - [x] 2.2e Its hinge row (T hinges, halves on the lid and the base), latches, and
    the lid on its joint; every shown part as the original case has it
    - `hinge_run`, a recipe: keyed hinges (S, M, L, F and the little T, its own pitch
      and side plates), each in two halves by `pieces`, side A's on a joint of its own
      that the case binds to its lid's angle. The latches are rotary_latch's base,
      knob and cap on the body and its lid plate on the lid.
    - `tools/case_check.py`: every part the original case shows, 57 at the defaults, 75 open
      with other keys (the hinges' too) and length 400, 48 rail off, 53 dropped,
      0 differ. Not yet: the original's tunable parts (odd lengths to print on their own)
      and its print list of whole hinges

## P3 — Paths

Outlines that more than one primitive draws, declared once (`core.Path`,
`primlib/paths/`), in Python first: a primitive's points are what they were, so the
format and view4d don't change.

- [x] 3.1 The dovetail path: the rails' section, closed by a base (`base_width`,
  `base_height`), with an optional groove, offset by `grow` and `face` (tongue,
  slot, lead-ins). `tests/test_path.py`: number for
  number the outlines rail15, topeak_rail and both housings draw, with lead-ins,
  offsets and clearances. Its page, `primlib/paths/dovetail.html`, from
  `make_docs.py`, measured on the solids (width, depth, rounds, the slot g off the
  tongue everywhere, base included, the lead-in e inside it)
- [ ] 3.2 rail15, topeak_rail, both housings and rotary_latch draw the dovetail path;
  geometry unchanged (baseline, replay), view4d's fixtures regenerated
- [ ] 3.3 The twist lock on a revolved dovetail: one clearance normal to every face,
  the width what calipers read (a geometry change: needs your go-ahead on the
  defaults)

view4d's side (reading `.prim`, the geometry kernel, time, the editor, print formats,
a slicer) is in view4d's `docs/PLAN.md`.
