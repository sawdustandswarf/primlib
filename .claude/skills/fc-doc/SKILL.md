---
name: fc-doc
description: >
  How to document a primitive in primlib: one generated page per primitive
  (primlib/primitives/<key>.html, from make_docs.py), describing only its current state,
  laid out by a fixed template (introduction, isometric view, first order parameters, a
  third angle drawing showing every first order parameter with the local x, y, z, parts
  detail for assemblies, print orientation), with per-primitive overrides in <key>.doc.md.
  Use whenever a primitive's documentation is written, regenerated, reviewed or changed,
  and before handing a primitive over as done.
---

# Documenting a primitive

Every primitive has **one documentation page**, and it describes the primitive
**as it is now**. Read this whole skill, then the primitive's override file
(below), before writing or changing a page.

## Rules

1. **One page per primitive:** `primlib/primitives/<key>.html`, beside
   `<key>.py`. Everything about the primitive goes in that one page. Don't
   start a second page for the same primitive. The two spec pages
   (`rail15_spec.html`, `topeak_rail_spec.html`) are exceptions to fold in
   when their primitive is next documented, not patterns to copy.
2. **Current state only.** The page says what the primitive is, not how it got
   there. No history, no "was 25, now 35", no dropped options, no dates
   of changes. The record of how it developed belongs in git, `docs/PLAN.md`
   and the notes of the projects that use it. One **Status** line is allowed,
   because it is current: designed, printed, fits, or in use.
3. **Generated, never hand-edited.** `tools/run.sh make_docs.py` builds every
   page, and `index.html`, from the primitives. Every number on the page comes
   from the model. The spec scripts (`make_rail15_spec.py`,
   `make_topeak_rail_spec.py`) also measure the real solids, and refuse to
   write if they disagree with the parameters.
4. **Follow the template** (`template.md` in this skill), unless the primitive's
   override file says otherwise.
5. **A third angle drawing is always there**, for the whole primitive and for
   each part of an assembly. No page is finished without it.
6. **No brands or trademarks.** Don't name a brand, a trademark, or anything
   that could be linked to one company's products. Use the generic term (a
   sailboard, not a Windsurfer), unless the brand name has become the common
   word. Describe where an idea came from by the idea itself. The Topeak
   exception is in `fc-prototype`.

## The importance of parameters

Not every parameter matters equally, and the documentation must say which
matter most. Each parameter belongs to one class:

| Class | What it is |
|---|---|
| **First order** | What a user tailors the part with: overall sizes, counts, the size of the thing it mates with or holds (hardware, panel thickness), and `clearance`. Few, and each one meaningful on its own. |
| **Second order** | The detail that shapes the part but rarely changes: chamfers, lead-ins, minimum walls, rib widths, a size offset. Defaults come from a print. |
| **Fixed** | Set by something outside the design (the profile of a rack the part fits, a hinge that has been confirmed). Read only. |
| **Derived** | Worked out from the others. Shown so they can be checked. |

The page leads with the first order parameters, and the drawing shows every
one of them. Second order, fixed and derived values come later, in the
parameter reference.

How each parameter's class is recorded in the code is a separate, open question.
Today `Param` has no class field, and primitives group their parameters by part
(`grouped(...)`) instead. Until that is settled:
- Decide the first order set for the primitive yourself.
- Write it in the override file under "First order", and confirm it with the
  author.
- Don't change `core.py` or `make_docs.py` to store the class unless that work
  is asked for.

## Overrides for one primitive

The author can change the documentation of one primitive without changing this
skill. Their requests are kept in an override file beside the primitive:
`primlib/primitives/<key>.doc.md` (`stencil.doc.md` is one).

- **Read it first.** Where it disagrees with this skill or the template, the
  override wins, for that primitive only.
- **When the author asks for a change to one primitive's page,** record it
  there, in their words with the date, before regenerating. Don't edit this
  skill for a single primitive. If the same override keeps coming up across
  primitives, suggest moving it into the skill.
- It holds requests, not page text: sections to add, drop or reorder, which
  dimensions to show on a view, names to use, the first order set, extra notes.
  Text that should appear on the page word for word goes under a heading
  "Text", and the generator includes it.
- `override.md` in this skill is the starting layout for a new file.

## Writing a new page

1. Read the primitive's code and docstring, and its override file if there is one.
2. Copy `override.md` to `<key>.doc.md` if there isn't one, and fill in the
   first order set and the part names (for one with several parts).
3. Give the generator what each template section needs:
   - the class docstring, or `intro`, for the introduction;
   - `views` for the dimensioned third angle drawing (and `front_view`,
     `front_dims`, `section_y`, `mates`, `fits`, `variants` where they apply:
     see `primlib/core.py`);
   - the frame (origin and local x, y, z) stated in the docstring;
   - each part's print orientation.
   The drawing's dimensions must cover every first order parameter.
4. Generate it (`tools/run.sh make_docs.py`), and read the page (or check its
   sections). Make sure:
   - every template section is there, or the override drops it;
   - every first order parameter appears on the drawing;
   - no history crept in.
5. Tell the author what's on the page, and anything the template asked for that
   the generator can't draw yet.

## What the generator does today

`make_docs.py` gives each primitive one page, and `index.html` lists them (with
the paths). For non-revolved primitives with `views`, it draws a dimensioned
third angle drawing (`views_svg`). It also gives the parameter tables, the
derived values, the checks and a Use section. Against the template it is still
missing:
- an isometric view;
- a first order section;
- a parts detail section for primitives with several parts (one drawing per
  part);
- a print orientation section;
- reading `<key>.doc.md`.

Adding these is generator work. Do it when asked, keep it general to every
primitive, and keep pages of primitives that don't use a new feature the same.
Until then, say which sections are missing whenever you report a page.
