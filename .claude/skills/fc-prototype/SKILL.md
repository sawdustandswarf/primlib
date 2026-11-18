---
name: fc-prototype
description: >
  The entry point for adding a feature or part to primlib, the library of parametric
  primitives for 3D-printed parts (FreeCAD and the .prim format): deciding whether it needs
  a new prototype or an existing primitive, recipe or assembly can do it, the rules every
  printed part must keep (one surface-normal clearance, a size offset only where absolute
  size matters, no supports, a file that recomputes in stock FreeCAD, reuse of existing
  primitives), the check tools, and which skill does each later step (fc-primitive, fc-doc,
  fc-composite, fc-configurator). Use before designing or building a new latch, hinge, rail,
  connector, mount or any other new printed part, or a feature on an existing one, and
  before handing a prototype over as done.
---

# Adding a feature: prototypes

A **prototype** is a part (or a set of mating parts) built by a script, saved as a
FreeCAD file, documented, and printed to test it. Once it works, it becomes a
primlib primitive, and recipes and assemblies put it together with others
(`fc-composite`): a file tailored by editing its sheet.

Read `AGENTS.md` first: its commands, rules and docs map apply throughout.

## The skills, in order

| Step | Skill | What it covers |
|---|---|---|
| Decide, and the shared rules | **fc-prototype** (this one) | New prototype or not; clearance, size offset, supports, portability; the check tools |
| Write the primitive | **fc-primitive** | The primitive and the project script around it: frame, parameters, checks, loads, motion, print layout, proving defaults |
| Document it | **fc-doc** | One generated page per primitive, current state only, the template, per-primitive overrides |
| Put it together | **fc-composite** | Recipes and assemblies: primitives placed together, compiled for FreeCAD (the hybrid case) |
| Configure it | **fc-configurator** | A dialog in FreeCAD that sets up a configuration of a composite (draft) |

Load each skill when you reach its step.

## 1. Decide whether to build a new prototype

First, take stock of what exists. Read these:
- `README.md` and `index.html`: the primitives and what each does.
- `primlib/recipes/` and `primlib/assemblies/`: where the primitives are used
  together. Search them (and the project that will use the part) for the
  primitive's key.
- `docs/PLAN.md` and `TODO.md`: what's done, and what's open.
- `git log --oneline`, for anything recent.

Then choose the first option that works:

1. **A parameter change.** An existing primitive already does it at other
   values: change the sheet and don't build anything new. The same goes for a
   small change to a default, a key or one value: make the edit, then recommend
   that the user runs the complete build. Don't run scratch or test builds, and
   don't add migrations or other extras that weren't asked for. The rest of
   this skill doesn't apply.
2. **Extend an existing primitive.** It does most of it: add the missing
   parameter or feature to it. Keep its printed and tested geometry identical at
   its old values, and prove that with the baseline (`fc-primitive`, section 3).
3. **A new prototype built from existing parts.** The function is new, but
   existing primitives supply the geometry: nest them in a primitive
   (`b.part`), or place them with a recipe (`fc-composite`).
4. **A new prototype from scratch.** Only when nothing above can work. Say why
   each existing candidate doesn't fit.

Tell the user the decision, with the reasons and numbers, before building
anything.

**For a new function, start with concepts.** Mock two or three rough options
(rotary_latch went through A, B and C), and let the user choose before detailing
any of them. Study reference parts the user supplies, such as 3MFs or photos,
first.

Build a new prototype, rather than editing one in place, when any of these holds:
- The change would alter geometry that has been printed and tested, and the old
  form must stay buildable. Keep the old one under a new key, marked deprecated
  (as `hinge_deprecated` is), or move it to `archive/` if it's kept only for
  reference.
- A print test failed for a reason no parameter can fix, such as a part that
  can't be gripped or a fit that binds whatever the clearance.
- The user asks for a concept, or for several options to compare.

If the reading of the user's request is ambiguous, state your reading with
numbers and ask in plain words, rather than offering a menu of choices.

## 2. Rules every printed part keeps

### No brands or trademarks

Never refer to a brand, a trademark, or anything that could be linked to one
company's products. This covers names, code, comments, sheets, file names and
documentation. Use the generic term (a sailboard, not a Windsurfer), unless the
brand name has become the common word for the thing. This includes designs
studied for ideas: describe the idea, not where it came from.

The one exception is **Topeak** (decided 2026-11-11), and only in two places:
- the prototype's name: `topeak_rail` and `topeak_rail_housing`;
- documentation where it refers to the Topeak rack system the rail fits.

Anywhere else, call it the rail or the rack.

### Clearance and size offset

Two values with different jobs. Keep them apart, and don't call either of them
a "print tolerance", because that name has meant both.

- **`clearance`, on every mating part.** Every gap between faces that mate or
  slide on each other is this one value, measured normal to the surface. The
  female part is the male part grown by `clearance` along every face's normal,
  with the same centres on its rounds (`radius` ± clearance). Don't split it into
  xy and z values, and don't use a different gap per face. 0.20 is the best fit
  printed so far (the 15 mm rail's print test).
- **Not clearance:**
  - Space between parts that don't touch is a separate gap value.
  - Deliberate interference (`preload`, `pull_down`) is a parameter of its own,
    with a check.
- **Size offset, only where absolute size is critical.**
  - Use it where the part must measure a set size: it fits something that isn't
    printed (a rack, a bolt, a panel), or a stated dimension matters.
  - It's added normal to the critical faces only, so angles and radii stay
    exact.
  - Set it from a measured print, as design minus measured, and leave it 0
    until then. The rails' `printer_width_offset` is the width-only case of it.
  - Leave it off parts whose absolute size doesn't matter, and never fold it
    into `clearance`.
- **A test print:**
  - It sweeps `clearance` (or the size offset) over a few values on small
    pieces, each labelled with its value (raised text, in hundredths).
  - Size each test to the feature being tested, and nothing more.
  - Give the volume and the time before making it.

### Print without supports

- Choose each part's print orientation as part of the design, and state it.
- Nothing more than 45° past vertical, and no flat faces pointing down, except
  the face on the bed. Round holes across the layers are the known exception:
  name them.
- Put grips and other details that would sit on the bed side in as recesses or
  V grooves. Use chamfers rather than fillets on edges facing down.
- Where a support can't be avoided, design it in: the `support`,
  `support_half` and `support_rect` primitives are supports under your own
  control, cut off after printing.
- Check it with `tools/print_check.py` (below), and look at the slicer's
  preview for floating ledges, which the face check can't see.
- Report the cost with every STL: each part's volume, and a rough print time at
  about 15 cm³ an hour. Before making a part bigger, say what the change adds.

### A file that stands on its own

The deliverable is a FreeCAD file that someone tailors by editing its sheet
cells and recomputing, in a stock FreeCAD 1.1 with no outside Python.
- Use only FreeCAD's own object types: Part, PartDesign, Sketcher, Spreadsheet
  and Draft. Draft arrays and clones are fine. Don't use `Part::FeaturePython`
  objects whose code is in primlib or the project.
- Drive every dimension with a sheet expression, and make counts live too. If
  something can only be fixed when the script runs, list it in the
  documentation under "rerun after changing ...", and treat it as a defect to
  remove later.
- Don't use `Part::Chamfer` or `Part::Fillet` on edges picked by number.
- Parts show or hide through `Visibility` expressions.
- Show a status cell (OK, or what to change) for every rule the geometry
  depends on.
- `tools/check_portable.py` (below) must report no outside modules.

### Reuse first

Before writing any geometry, reuse what's there:
- primlib's primitives (`primlib.make(..., bind=...)`, or `b.part` inside
  another primitive) and the `Builder` methods;
- its recipes (`primlib/recipes/`): a row of pieces by key, a length filled,
  a series, a mirrored pair;
- the tested parts: the rails (`rail15`, `topeak_rail` and their housings),
  `hinge`, `rotary_latch`, `box_edge` and `box_corner`. Never
  `hinge_deprecated`: it's the old ring hinge, kept only for the over-centre
  `latch`.

Something already printed and proven beats a new design for the same job.
Each time, move what the new work shares with existing primitives to where it
belongs (`fc-primitive`, section 1).

## Tools

Both are in `tools/`. Run FreeCAD scripts with `tools/run.sh`, never
`freecadcmd SCRIPT` (`AGENTS.md` says why).

```bash
# Outside code a saved file needs (plain python, no FreeCAD), plus its sheets'
# tolerance and status cells
python3 tools/check_portable.py File.FCStd

# Print check: validity, solids, overhang, volume and time for each part in a
# group (default "Print"), or for named objects
FILE=File.FCStd GROUP=Print tools/run.sh tools/print_check.py
FILE=File.FCStd OBJECTS=Part1,Part2 tools/run.sh tools/print_check.py
```

`check_portable.py` also flags every `Part::Chamfer` or `Fillet` that picks
edges by number. One on a plain box built at the origin, then placed (like the
hinge leaves), keeps its numbering and is fine; one on a boolean result isn't.

`print_check.py` treats each part as printed where it sits, with the bed at the
part's lowest z. It exits 0 either way, so read its final line: `PASS` or `FAIL`.

Known limits, until they're fixed:
- `check_portable.py` reports `Clearance` and `SizeOffset` by exact case, so it
  says "no" for primlib's lower-case `clearance` (its tolerance-like list does
  find it). Its status list only finds aliases containing "status", not
  `...OK` cells.
- `print_check.py` finds the bed from the loose bounding box, which sits low on
  cones. Place print parts with `optimalBoundingBox()`, or a false overhang can
  show.
- `print_check.py` checks face angles only. It can't see a ledge with nothing
  under it (rotary_latch A1's knob passed it, but the slicer caught it).

## Done means

- The decision from section 1 was stated, with reasons and numbers.
- `clearance` is the only fit value, applied along surface normals, and a size
  offset is only on parts whose absolute size is critical.
- `print_check.py` passes, the slicer shows no floating ledges, and the
  volumes and times have been reported.
- `check_portable.py` reports no outside modules, and the sheet alone tailors
  the part.
- The primitive's own checks are done (`fc-primitive`), and its page is
  generated and follows `fc-doc`.
- Reuse was considered, and any refactor was proven, with the baseline, to
  leave printed geometry unchanged.
- `README.md` (the primitive's section), `docs/PLAN.md` and `TODO.md` are
  updated, and so are the notes of the project that uses the part.
