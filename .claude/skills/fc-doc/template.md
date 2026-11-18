# Documentation template

The sections of a primitive's page, in order. Every number is generated from
the model, at the defaults unless a section says otherwise. A primitive's
`<key>.doc.md` can change this layout, for that primitive only.

---

## 1. Introduction

- What the primitive is and what it's for, in two or three sentences.
- What it mates with or is fixed to: other primitives, hardware, and things that
  aren't printed (a rack, a panel).
- For an assembly: its parts, named as on the rest of the page and as the
  objects are named (`{name}_base`, `_knob`, ...).
- Status: designed, printed, fits, or in use. One line, current only.

## 2. Isometric view

- The whole primitive at its defaults, shaded, from the standard isometric
  direction.
- For an assembly: assembled, in the working position, with each part named on
  the view or in the caption. Add an exploded view when parts hide each other.

## 3. First order parameters

- A table of the first order parameters only: name, default, unit, and what it
  does, in a phrase.
- `clearance` is always first order, wherever the primitive has one.
- Sorted by importance, most important first.

## 4. Third angle projection

An engineering drawing in third angle projection: the front view, the top view
above it and the right side view to its right. It has the third angle symbol, and
hidden edges are dashed.

- **Every first order parameter is dimensioned** on at least one view, and
  labelled with its name. A parameter that can't be seen as a length (a count,
  an angle of turn, the clearance) is shown by a note or a detail view instead.
- A section view where the important faces are inside (a slot, a bore, a fit
  between parts). Give the section plane's name and position.

## 5. Orientation: local x, y, z

- The primitive's own frame, drawn on the views (an axis triad) and stated in
  words: where the origin is, and what x, y and z point along. For example: "the
  case surface is z = 0, the knob's axis is z (out of the case), y is up towards
  the lid".
- How the frame relates to where the part is used, when it isn't obvious.

## 6. Parts detail (assemblies only)

For a primitive made of several parts, each part gets its own subsection, as if
it were a primitive in its own right, repeating sections 1 to 5 for it:

- **6.n.1 Introduction:** what the part does, and what it touches in the
  assembly.
- **6.n.2 Isometric view** of the part alone.
- **6.n.3 First order parameters** that shape this part. A parameter shared by
  several parts is listed in each.
- **6.n.4 Third angle projection** of the part alone, every one of its first
  order parameters dimensioned.
- **6.n.5 Orientation:** the part's own frame, if it differs from the
  assembly's, and where it sits in the assembly's frame.

Leave out this section for a single-part primitive.

## 7. Print orientation

For each part:
- how it sits on the bed, shown by a view of it on the bed with z up;
- why that way (the layers along the load, no supports);
- the steepest overhang and its angle (45° at most), and any known exception
  (round holes across the layers), named;
- volume and a rough print time (about 15 cm³ an hour).

Print aids that are cut off afterwards (bridges, supports) are named here.

## 8. Parameter reference

Everything not in section 3:
- the second order parameters (name, default, note);
- the fixed parameters, read only, with where their values come from;
- the derived values (name, expression, value at the defaults);
- the checks the build makes, and what to change when one fails.

The Use section (how to call the primitive in code) goes last.
