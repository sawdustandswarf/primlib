# AGENTS.md

Guidance for AI coding assistants (and people) working in this repository.

## What this is

primlib is a library of parametric primitives for 3D-printed parts. Each primitive is one general part (a hinge, a rail, a latch, a box edge) whose sizes are expressions over named parameters. It has two targets:

- **FreeCAD 1.1:** primitives are built from spreadsheet aliases, and the folder installs as a FreeCAD add-on (`./install.sh` links `~/.local/share/FreeCAD/v1-1/Mod/primlib` here).
- **A file format:** any primitive exports as a `.prim` file (JSON, `docs/FORMAT.md`) that other programs can build without FreeCAD. view4d (https://github.com/sawdustandswarf/view4d) is the reader this is tested against.

## Commands

```bash
python3 -m unittest discover tests     # plain Python, no FreeCAD needed
python3 -m primlib list                # what exports as .prim
tools/run.sh make_docs.py              # regenerate every primitive's .html and index.html, after any change
tools/run.sh make_rail15_spec.py       # rail15_spec.html: measures the solids, won't write if they disagree
tools/run.sh make_topeak_rail_spec.py  # topeak_rail_spec.html, likewise
tools/run.sh tools/baseline.py         # every primitive at its defaults, to $BASELINE_OUT or baseline.json
python3 tools/baseline_diff.py before.json after.json
tools/run.sh tools/record_check.py     # which primitives record (build only through Builder)
tools/run.sh tools/expr_check.py       # the expression language agrees with FreeCAD
tools/run.sh tools/replay_check.py     # a .prim file builds the same as make()
tools/run.sh tools/recipe_check.py     # recipes and assemblies compiled for FreeCAD
python3 tools/check_portable.py F.FCStd  # outside code a saved file needs (stock FreeCAD only?)
FILE=F.FCStd GROUP=Print tools/run.sh tools/print_check.py  # each part on the bed: overhang, volume, time
```

**Run FreeCAD scripts with `tools/run.sh`, never `freecadcmd SCRIPT`.** freecadcmd loads a script by its module name with FreeCAD's add-on folders first on the path, so another installed add-on with a script of the same name (`make_docs.py`) would run instead. `tools/run.sh` runs the file itself.

**Proving geometry unchanged:** `tools/baseline.py` records validity, solids, volume and bounding box for every primitive at its defaults. A change that should leave geometry alone (a refactor, a new target) must leave the baseline unchanged. Compare against the last commit (for example `git archive HEAD primlib` into a scratch folder).

**view4d's reader:** after a change to the expressions, the format or a primitive's operation tree, regenerate view4d's test data and run its tests, with view4d cloned beside this repository:

```bash
python3 tools/view4d_fixtures.py ../view4d/prim/tests/data
(cd ../view4d && cargo test -p view4d-prim)
```

## How it fits together

- `primlib/core.py`:
  - `Primitive`, the base class, declares `params` (`Param` name, default, note), `derived`, `checks` (expressions that must be over 0), and optionally `fixed` parameters (read only).
  - `Primitive.make(doc, name, sheet=, prefix=, bind=)` writes a sheet row for each parameter not in `bind`, checks, and builds.
  - `Revolved` primitives give `walls()`, a profile that becomes a sketch fully constrained to the sheet and is revolved.
  - `Machined` primitives give `body(b)`, which returns a body and its cut tools, made with `Builder`.
  - `Builder` makes bound boxes, cylinders, cones, sectors, polygon prisms, sketch prisms, ruled lofts, revolves, arrays and grids, moves, nested primitives (`part`), booleans and `beyond` cuts, each size an expression over the primitive's names. A choice between shapes is `b.choose(guard, a, b)` and a counted run `b.series(suffix, count, make)`; a rounded vertex whose radius is 0 or less is sharp.
  - `Builder(doc, ...)` picks a target in `primlib/targets/` by what `doc` is: `freecad.py` binds each size to the sheet; `record.py` keeps the operations as a tree for a file.
- **Build only through `Builder`:** no `doc.addObject`, `b.add`/`b.bind` or `value(...)` on the way, or the primitive can't be recorded.
- **Expressions** are the language in `docs/EXPRESSIONS.md` (`primlib/expr.py`): use nothing outside it.
- **`core` loads without FreeCAD** (for export): keep FreeCAD imports inside functions elsewhere.
- Values are plain numbers in the library. A project sheet in mm binds them as `Alias / 1 mm`.
- `primlib/primitives/<key>.py`: one primitive class per file, with its generated `<key>.html` beside it. An optional `<key>.doc.md` holds overrides for that page (first order parameters, wording), each with its date.
- `primlib/paths/<key>.py`: a `Path` (in `core.py`) is an outline more than one primitive draws, declared once. `dovetail` is the rails' section; `tests/test_path.py` holds it to the rails' outlines.
- `primlib.make(key, doc, name, ...)` is the entry point. `primlib/spacing.py` lays pieces along a length as live sheet formulas.
- **Recipes** (`primlib/recipe.py`, `primlib/recipes/`) place primitives as parts: a row by key, a series, a choice. They export as `.prim` version 2. In FreeCAD, `primlib/recipe_freecad.py` compiles them to masters and links with live formulas.
- **Assemblies** (`primlib/assemblies/`) take recipes as parts, with pieces of a compound, the print list and joints. `hybrid_case` is the worked example, a plywood case with printed edges, hinges and latches. `tools/case_check.py CASE.FCStd` compares it part by part with the original FreeCAD model of that case (not in this repository).
- `primlib/gui.py` and `InitGui.py` are the FreeCAD toolbar.

## Docs map

| Read | For |
|---|---|
| `README.md` | what each primitive does, using the library, adding a primitive |
| `docs/GLOSSARY.md` | the words for axes, sizes and shapes; **names follow it** |
| `docs/EXPRESSIONS.md` | the expression language |
| `docs/FORMAT.md` | the `.prim` file format |
| `docs/PLAN.md` | what is done and what is next |
| `TODO.md` | smaller open work, as a checklist |
| `index.html`, `primlib/primitives/*.html` | generated reference pages (also on GitHub Pages) |

## Skills

Step-by-step guides for the work here, in `.claude/skills/<name>/SKILL.md`. Claude Code loads them by itself; any other agent should read the one for its step.

| Skill | When |
|---|---|
| `fc-prototype` | first, for any new part or feature: new prototype or not, the rules every printed part keeps, the check tools |
| `fc-primitive` | writing or changing a primitive, and the project script around it |
| `fc-doc` | a primitive's generated page: the template and `<key>.doc.md` overrides |
| `fc-composite` | recipes and assemblies: primitives placed together, compiled for FreeCAD |
| `fc-configurator` | a dialog in FreeCAD to configure a composite (draft) |

## Rules

- **Names follow `docs/GLOSSARY.md`:** x length (left to right), y width (front to rear), z height (up); a path's (u, v) is width and height; depth only for how far something goes into a face. Older names that differ keep their meaning.
- **No brands or trademarks** in names, code, comments, sheets, file names or documentation. Use the generic term (a sailboard, not a Windsurfer) unless the brand name has become the common word. The one exception is Topeak, and only in the prototype's name (`topeak_rail`, `topeak_rail_housing`) and in documentation where it refers to the rack system the rail fits.
- **General purpose:** one general `Primitive` per file. Shared building blocks go in `core.py`; anything specific to one design stays in the project that uses it.
- **Docs are generated:** run `tools/run.sh make_docs.py` after a change. Never edit the `.html` by hand.
- **Saved files need no outside code.** A primitive's result must be plain FreeCAD objects (Part, PartDesign, Sketcher, Spreadsheet, Draft), so the file recomputes in stock FreeCAD.
  - Build small chamfers into the shape: lofts through inset sections, or `Builder.beyond` cuts, as `box_edge` and `box_corner` do.
  - Never use `Part::Chamfer` on edges picked by number, and no `Part::FeaturePython`.
- **Tolerances:**
  - One `clearance`, normal to every surface: the female part is the male grown by it, and rounds stay concentric.
  - A size offset (such as `printer_width_offset`) only where absolute size is critical, kept apart from the clearance.
- **Fixed profiles:** `topeak_rail` fits a real rack; `rail15` is the library's own fixed 15.00 rail. Keep them separate, and don't change their fixed parameters.
- **Keep the defaults stable.** Printed parts depend on them, so a new option must default to the old geometry. Prove it with the baseline.
- **Legacy code, not for new work:**
  - `hinge_deprecated` is the old ring hinge, kept only because `latch` is built on it, with `pin`, `sleeve`, `sleeve_clearance`, `plate` and `hole` under it. The latch's next update moves it to `hinge`; then those six go.
  - `archive/` holds earlier attempts, kept for reference. Nothing imports it.
- **Commits:** only when asked.
