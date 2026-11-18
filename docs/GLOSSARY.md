# primlib — Glossary

The words primlib uses for directions, sizes and shapes, one meaning each. New
names follow it from 2026-11-15; older names that differ are listed at the end
and keep their meaning, because sheets and projects use them.

## Axes

The frame comes from the hybrid case (`primlib/assemblies/hybrid_case.py`, the library's
worked example): a box standing on its floor, seen from the front.

| Axis | Direction | Size along it |
|---|---|---|
| **x** | left to right | **length** |
| **y** | front to rear | **width** |
| **z** | floor up | **height** |

- **Origin:** the inside left, front, bottom corner. The box's inside runs 0 to
  `length` in x, 0 to `width` in y, 0 to `height` in z.
- **A part made flat** (a panel) lies with its length along x, its width along y and
  its thickness up z, and is turned into place.
- **A primitive** states its own frame in its docstring and on its page, in these
  axes: where its origin is and what x, y and z point along. A rail runs along x,
  across y, with its root at z = 0.

## A path's plane

A path (`primlib/paths/`) is drawn in its own plane, **(u, v)**:

| Axis | Direction | Size along it |
|---|---|---|
| **u** | across, centred on u = 0 | **width** |
| **v** | up from the path's base line | **height** |

The primitive drawing it maps (u, v) into its frame: (y, z) for a rail, (r, z) about
the z axis for a revolved part.

## Sizes

- **length, width, height:** sizes along x, y and z (u and v in a path's plane).
- **depth:** how far something goes *into* a face, whichever axis that is: a slot, a
  pocket, a groove, the dovetail's tongue below its root line. Not a size along z in
  general.
- **thickness:** a sheet's or plate's size normal to its own face.
- **radius**, **diameter:** written out; `_r` and `_d` are the short forms in names.

## Offsets and fit

- **clearance:** the one gap between mating printed parts, normal to every face; the
  female part is the male grown by it, rounds concentric.
- **grow**, **face:** a path's offsets: `grow` moves the profile's faces normal to
  themselves (outwards when positive), `face` moves its base the same way. The slot
  is grow = face = clearance; a lead-in is grow = −e, face 0.
- **lead-in:** a part shrunk at its ends so it finds its way into its mate.
- **printer_width_offset** (`widen` in a path): added to a width so the part prints at
  its design width. Not part of the fit.
- **caliper width:** a width measured where calipers read it (a rail's, between
  vertical tangents to its tip rounds), as opposed to a **sharp** width, between
  corners before they're rounded.

## Shapes

- **tongue:** the male dovetail; **slot:** the female.
- **root**, **tip:** a tongue's narrow end, at its base, and its wide end.
- **flank:** a tongue's sloping side; **tip face:** its end face.
- **base:** the rectangle a tongue stands on (a rail's support).
- **mouth**, **lip:** a slot's opening, and the edge over the tongue's root.
- **groove**, **guide:** a channel in a tongue's tip face, and the slot's ridge in it.

## Older names that differ

Kept as they are; don't copy them into new work.

| Name | Where | Under this glossary |
|---|---|---|
| `base_depth` | `rail15`, `topeak_rail` | a height (the support, up from the root) |
| `block_depth` | both rail housings | a height |
| `plate_t`, `flange_t`, `body_t` | several | thickness, short form |
| `plate_w`, `lid_h` | several | width, height, short forms |
| `mouth_d` | `twist_socket`, `twist_plug` | a sharp diameter, not a caliper one |
