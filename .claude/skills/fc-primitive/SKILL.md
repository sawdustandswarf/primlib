---
name: fc-primitive
description: >
  How to write or change the Python that builds a part in primlib: a primitive
  (primlib/primitives/<key>.py, a Primitive class built with Builder from expressions over
  its parameters) and the project script that builds and checks it (loads, motion checks,
  print layout, STL). Covers the frame, parameters, checks, building only through Builder,
  keeping defaults stable (the baseline), recording for the .prim format, strength sizing,
  motion checks, print checks and what to update afterwards. Use when writing a new
  primitive or prototype script, or changing the geometry or parameters of an existing one;
  load fc-prototype first to decide whether new geometry is needed at all.
---

# Developing a primitive

A primitive is the macro that makes a part: a Python class in primlib whose sizes
are expressions over named parameters. In FreeCAD it writes sheet rows and builds
plain FreeCAD objects bound to them; recorded, it exports as a `.prim` file that
other programs build without FreeCAD. The project script around it checks the
part works and gets it to the printer.

Before starting, `fc-prototype` has decided that new geometry is needed, and how
much (a new primitive, or extending one). Its shared rules apply here: one
clearance, a size offset only where absolute size matters, no supports, and a
saved file that needs no outside code. Read `AGENTS.md` ("How it fits together"),
README's "Adding a primitive", and the nearest existing primitive before writing.

## 1. Who owns what

| Where | What goes there |
|---|---|
| `primlib/core.py` | General building blocks: `Builder` methods, `Param`, shared checks. |
| `primlib/primitives/<key>.py` | The geometry and its rules: parameters, derived values, checks, the build. One general class per file. |
| `primlib/paths/<key>.py` | An outline more than one primitive draws, declared once (`dovetail`). |
| `primlib/recipes/`, `primlib/assemblies/` | General patterns of primitives placed together (`fc-composite`). |
| The project script, in the project that uses primlib | What belongs to one use: the loads, the motion checks, the print layout, the STL, renders. |
| The project's notes | The record: what was built, values and why, what was checked and printed. |

Start a new part in the project script if it is still a concept. Move the
geometry into a primlib primitive once its shape is settled (rotary_latch went
this way). After the move, the project script calls
`primlib.make(key, doc, name, sheet=, prefix=)` and keeps only its own work.
Anything specific to one design stays in the project, not in primlib.

## 2. The primitive

- **Frame first.** Choose the origin and the local x, y, z, and state them in the
  class docstring ("the case surface is z = 0, the knob's axis is z ..."). The
  drawings and the print layout rely on it. Names follow `docs/GLOSSARY.md`:
  x length, y width, z height.
- **Parameters:**
  - Each is a `Param(name, default, note)`, the value a plain number (mm or
    degrees).
  - The note says what the parameter does, and its direction (x, y, z) where
    that helps.
  - Group a long list with `grouped(("Heading", PARAMS), ...)`.
  - Values set by something outside the design go in `fixed` (read only), as
    rail15's do.
- **First order set.** Decide which parameters are first order (see
  `fc-doc`), put them first, and keep them few. Make the rest second order,
  with defaults taken from a print where one exists.
- **Derived values** carry the working. Write each as a formula with a note, so
  the page and the sheet show it. If a value can be derived ("the largest pin
  that leaves `wall_in`"), derive it rather than asking for it.
- **Expressions** use only the language in `docs/EXPRESSIONS.md`, so every
  target (FreeCAD, the `.prim` format) reads them the same.
- **Checks:**
  - Each `(expression, message)` must be over 0, or the build is refused.
  - Write the message as what is wrong, so the user knows what to change.
  - Add one for every rule the geometry depends on: walls left, parts that must
    not meet, screws on the plate.
  - Use `+ 0.000001` where exactly 0 is allowed.
- **Clearance:**
  - It is the gap between mating faces, measured normal to the face, so the
    female part is the male grown by `clearance`.
  - On a slanted face, the gap along an axis is `clearance` divided by the
    sine or cosine of the face's angle, as rotary_latch's `gap_r =
    clearance * sqrt(2)` is at 45°.
  - Deliberate interference (`preload`, `pull_down`) is a parameter of its own
    with its own check, never part of the clearance.
  - Space between parts that don't touch is not clearance.
- **Building:**
  - **Build only through `Builder`** (`box`, `cylinder`, `cone`, `revolve`,
    `cut`, `fuse`, `common`, `compound`, `beyond`, `choose`, `series`, `part`,
    ...), with every size an expression. No `doc.addObject`, `b.add`/`b.bind` or
    `value(...)` on the way, or the primitive can't be recorded for the `.prim`
    format.
  - Build chamfers into the shape: lofts through inset sections, cones, or
    `beyond` cuts. Never use `Part::Chamfer` or `Fillet` on edges picked by
    number.
  - Use no `Part::FeaturePython`.
  - Keep FreeCAD imports inside functions: `core` must load without FreeCAD.
- **Several parts.** Each part is its own object in the result compound
  (`{name}_base`, `{name}_knob`, ...), built in its working position, so a
  project or an assembly can find and place each one (an assembly takes them
  as pieces: `fc-composite`).
- **Reuse.** Import shared shapes instead of copying them (rotary_latch takes
  rail15's fixed values and shape; the rails share the `dovetail` path). Nest
  another primitive with `b.part(Inner, suffix, bind)` and its
  `nested_checks`, or use it through `primlib.make(..., bind=...)`.
- **Defaults stay stable.** Printed parts depend on them, so a new option must
  default to the old geometry.

## 3. Checking a primitive

For every change:
1. Run the plain Python tests: `python3 -m unittest discover tests`.
2. Build it in a fresh document (`primlib.make(key, doc, name, **values)`).
   - No object's `State` may hold `Invalid` or `Error`.
   - Each part must be one valid solid.
   - Report the volume.
3. Prove the defaults are unchanged against the last commit, with the
   baseline:
   - `git archive HEAD primlib` into a scratch folder, and run
     `tools/run.sh tools/baseline.py` there and here (`BASELINE_OUT` names the
     file).
   - `python3 tools/baseline_diff.py before.json after.json`, and report it.
   - It compares validity, solids, volume and bounding box for every
     primitive at its defaults.
4. Check it records and replays: `tools/run.sh tools/record_check.py`, then
   `tools/run.sh tools/replay_check.py` (its `.prim` file builds the same as
   `make()`).
5. Try the extremes of the new parameters. A check must refuse a bad value
   before the geometry breaks.
6. Rebuild what uses the primitive: `tools/run.sh tools/recipe_check.py` for
   the recipes and assemblies, and the projects that use it.
7. After a change to the expressions, the format or a primitive's operation
   tree, regenerate view4d's test data and run its tests (`AGENTS.md`).

"No invalid objects" doesn't prove the geometry is right. Measure the gaps and
overlaps that matter with `distToShape` and `common`.

## 4. The project script

The script builds the primitive into a document, checks it, and saves it only
if every check passes. It lives in the project that uses the part, not in
primlib.

- **Sheet:** the primitive's rows (from `make()`), its derived values shown,
  then the project's own sections: the target loads, the material values, the
  load estimates and the `...OK` check cells (1 for OK).
- **Strength sizing**, first order, static and ideal:
  - Choose a target load, and one load case at a time.
  - For each weak point on the load path (pin bending and shear, bearing, walls
    sheared off, screws pulling through), work out its breaking load. Take the
    layer direction into account.
  - `FMax` is the weakest of them. Bring the parts to roughly the same strength.
  - Use no safety factor in the numbers, and suggest 2 to 3 for a working load.
  - Printed PETG: `SigXY` 45, `SigZ` 25, `TauXY` 27, `TauZ` 15 MPa (along and
    across the layers, shear 0.6 × tension).
- **Motion checks** (`motion()`): move the parts through their whole movement
  in steps, and measure with `distToShape`.
  - The gap is at least the clearance all the way, and exactly it where it
    should bear.
  - The part goes in clear.
  - The stops and lead-ins catch what they should.
  - Print the gaps, and refuse to save if any check fails.
- **Print layout:**
  - A `Print` group of `App::Link`s, each part turned to its print orientation.
  - Put each part on the bed with `optimalBoundingBox().ZMin`. The loose
    bounding box sits low on cones and floats the part.
  - Parts that mount side by side can print as one piece, joined by a
    one-layer bridge that is cut after mounting.
- **Output:**
  - Save through an offscreen GUI (`QT_QPA_PLATFORM=offscreen`,
    `FreeCADGui.showMainWindow()`), so the view settings are kept.
  - Write printed output with `os.write(1, ...)`, because the GUI captures
    stdout.
  - Close every document, then `os._exit(0)`.
  - Print the volumes and times, then a `saved <path>` line. Scripts exit 0
    even when they fail, so that line is the result.
  - Run it with `tools/run.sh`, never `freecadcmd SCRIPT`.
- **STL** from the print links, with `MeshPart.meshFromShape(...,
  LinearDeflection=0.01)`.
- **Pictures.** FreeCAD can't draw offscreen without a display. Export the
  part as a `.prim` file and render it with view4d (`view4d part.prim --png
  out.png`), or draw PNGs with a z-buffer of your own.

Then run fc-prototype's tools on the saved file: `tools/print_check.py` (PASS)
and `tools/check_portable.py` (stock FreeCAD only).

## 5. Afterwards

- Documentation: follow `fc-doc`, and regenerate with
  `tools/run.sh make_docs.py`.
- `README.md`: the primitive's line in the layout, and a short section.
- `docs/PLAN.md` and `TODO.md`: what's done, and anything left open.
- The project's notes: what was built, the values and why, and the checks,
  loads, volumes and times.
- Superseded primitives: keep the old one under a new key marked deprecated
  (as `hinge_deprecated` is) while something still uses it, or move it to
  `archive/` if it's kept only for reference. Never edit `archive/`.
- Commit only when asked.
