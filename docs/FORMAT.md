# The `.prim` file format, versions 1 and 2

A `.prim` file is one primitive, kept as a tree of operations (version 1), or a recipe of primitives (version 2, [below](#recipes)). Every size in the tree is an expression over the primitive's own names (see [EXPRESSIONS.md](EXPRESSIONS.md)), so a reader can build it at any values, not only those it was written at. The file is JSON in UTF-8.

`primlib/targets/record.py` writes it: `record(cls)`, or `primlib export` (P1.5). The readers are:

- **FreeCAD:** `replay` (P1.5).
- **view4d:** the `view4d-prim` crate.

## The document

```json
{
  "format": "primlib.prim",
  "version": 1,
  "primitive": "pin",
  "title": "Retained pin",
  "params":  [{"name": "height", "default": "10", "note": "overall height", "group": null}],
  "fixed":   [{"name": "t", "expr": "2", "note": "..."}],
  "derived": [{"name": "shaft_r", "expr": "diam / 2 + clearance", "note": "shaft radius, grown"}],
  "checks":  [{"expr": "diam", "message": "diam must be positive"}],
  "values":  {"height": "12"},
  "ops":     [{"id": 0, "op": "revolve", "name": null, "points": [["0", "bottom"], ["flare_r", "bottom"]],
               "span": ["0", "360"]}],
  "result": 0,
  "motion": []
}
```

| Key | What it holds |
|---|---|
| `format`, `version` | Always `"primlib.prim"` and `1`. A reader refuses any other format, or a version above the ones it knows. |
| `primitive`, `title` | The library's key for the primitive, and its title. |
| `params` | In order. `default` is an expression: a number, a formula starting with `=` over the params before it, or a string starting with `'`. `group` is the heading it sits under, or null. |
| `fixed`, `derived` | Named expressions, in the order they are evaluated ([EXPRESSIONS.md](EXPRESSIONS.md#names-and-their-order)). |
| `checks` | Expressions that must be over 0 for a valid part. Each failure's `message` says what to change. A reader shows failed checks and does not build. |
| `values` | Optional. Parameter values to build at, name → expression, in place of the defaults. |
| `ops` | The operations. Each one's `id` is its place in the list, and it refers only to operations before it. |
| `result` | The id of the operation that is the part. |
| `motion` | Empty in version 1; time tracks come later (view4d M6). A reader ignores what it doesn't know here. |

## Operations

Every operation has `id`, `op` and `name`:
- `name` is the operation's own name within the primitive (`"hole"`, `"a_bar12"`), or null for the result. FreeCAD names its object `{name of the part}_{name}`.
- The parts of a `compound` keep their names, so a reader can tell them apart and colour them.

**How fields are written:**
- A field holding an expression is a string.
- **Spans** are `[lo, hi]` pairs of expressions.
- A field holding an operation (`base`, `of`, `tools`, `item`, `then`, `otherwise`) is its id.

All lengths are in mm, and all angles are in degrees, anticlockwise seen from the + end of their axis.

### Solids

| `op` | Fields | Shape |
|---|---|---|
| `box` | `x`, `y`, `z`: spans | The box between them. |
| `cylinder` | `axis`: `"x"`, `"y"` or `"z"`; `centre`: the other two coordinates, in xyz order; `r`; `span`: along the axis | A cylinder. |
| `cone` | As `cylinder`, with `r1` at `span[0]` and `r2` at `span[1]` instead of `r` | A truncated cone. |
| `slot` | As `cylinder`, plus `along` (one of the other two axes) and `travel` | A cylinder stretched by `travel` along `along`, centred on `centre`. It is the two end cylinders and the box between them. |
| `sector` | `r`; `span`: along z; `start`, `angle` | A cylinder about the z axis, from `start` (degrees from +x) through `angle`. |
| `polygon` | `sides`: a number, not an expression; `r`; `span`: along z | A regular prism about the z axis, its corners on a circle of radius `r`, one corner on +x. |
| `sphere` | `centre`: x, y, z; `r` | A sphere. |
| `beyond` | `normal`: a unit vector of numbers, not expressions; `d`; `size` | Everything on the far side of the plane normal · p = `d`. It is meant only as a cut tool. FreeCAD makes it a cube `size` across with one face on the plane. A reader may use a half-space, or any solid that covers the part. |

### From profiles

A **polygon** is a list of vertices `[a, b]`. A vertex `[a, b, r]` is rounded to radius `r`; a radius of 0 or less leaves it sharp. The polygon is closed: its last vertex joins its first.

A **plane** names the axes the polygon's (a, b) lie on, and its normal:

| `plane` | a | b | normal |
|---|---|---|---|
| `"xy"` | x | y | z |
| `"yz"` | y | z | x |
| `"zx"` | z | x | y |

| `op` | Fields | Shape |
|---|---|---|
| `prism` | `points`, `plane`, `span`: along the normal | The polygon extruded over the span. |
| `loft` | `plane`; `ruled`: true; `sections`: a list of `{points, at}`, `at` along the normal | A ruled loft through the polygons. They correspond vertex for vertex, rounds included. |
| `revolve` | `points`: (r, z), r ≥ 0; `span`: an angle span | The polygon in the xz half-plane (x = r), turned about the z axis from `span[0]` to `span[1]`. |
| `loft_about` | `sections`: a list of `{points, angle}`, (r, z) polygons | A smooth (not ruled) loft through the polygons, each in the half-plane at its `angle` about z. |
| `text` | `string`, `font` (a file path), `size` (the capital height), `at`: x, y, z; `justify` | A line of text, flat in the xy plane at `at.z`. `justify` places `at` on the line: an index into Top / Middle / Bottom (3 apart) × Left / Center / Right. 0 is top left; 4 is the middle of the capital height; 8 is bottom right, on the baseline. |
| `extrude` | `base` (a flat shape such as `text`); `length`; `z`: an expression or null | `base` extruded along +z by `length`, then moved up by `z`. |

### Patterns, moves and booleans

| `op` | Fields | Shape |
|---|---|---|
| `array` | `base`; `along`: axis → `{count, start, step}` | Copies of `base` on a grid. For each axis in `along`, there are `count` copies at `start`, `start + step`, …. The copies are fused. A count must come out a whole number. |
| `polar` | `base`; `count`; `angle` | `count` copies of `base` about the z axis, fused. The first is where `base` is. The last is `angle` from the first, unless `angle` is 360, where they are spread round the full turn. |
| `move` | `base`; `by`: dx, dy, dz, each an expression or null for 0 | `base` translated. |
| `turn` | `base`; `axis`: `"x"`, `"y"` or `"z"`; `angle` | `base` turned by `angle` degrees about the axis through the origin, anticlockwise seen from its + end. The FreeCAD target needs the angle a number. |
| `fuse` | `of`: a list | The union. |
| `common` | `of`: a list | The intersection. |
| `cut` | `base`; `tools`: a list | `base` minus the union of `tools`. |
| `compound` | `of`: a list | The shapes kept as separate parts, not fused. |

### Choices and counts

These are where the tree depends on values. The FreeCAD target settles them when it builds, so a change to the names they use needs a rebuild there. A reader evaluates them at every build.

| `op` | Fields | Shape |
|---|---|---|
| `choose` | `guard`; `then`; `otherwise` | `then` if `guard` is over 0, else `otherwise`. Only the chosen operation is built. |
| `series` | `count`; `index`: the name, `"i"`; `item`; `join`: `"fuse"` or `"compound"` | `item` built once for each i = 0, 1, … `count` − 1 (the count truncated), with `i` bound to it. The results are fused or kept as parts. A count of 1 is just the item. An operation under `item` that uses `i` is built once per i. |

The operations reached only through a `choose` or `series` are still in `ops`. A reader builds from `result`, following references, and builds only what it reaches.

## Recipes

A recipe (version 2, `"kind": "recipe"`) is a reusable pattern of primitives: a row of pieces by key, a length filled, a mirrored pair. Like a primitive it has `params`, `fixed`, `derived` and `checks`, and its keys are text names ([EXPRESSIONS.md](EXPRESSIONS.md#text)). In place of `ops` it has parts, placed:

```json
{
  "format": "primlib.prim", "version": 2, "kind": "recipe",
  "primitive": "edge_run", "title": "Edge run",
  "params": [...], "fixed": [], "derived": [...], "checks": [...],
  "slots": 7,
  "parts": [{"name": "F", "primitive": "box_edge", "bind": {"length": "fit_length", "size": "size"},
             "mirror": null, "colour": [0.8, 0.8, 0.78]}],
  "place": [{"id": 0, "op": "row", "name": "edge", "key": "use", "pieces": {"F": {"part": "F", "length": "fit_length"}},
             "at": ["0", "0", "0"], "along": "z", "gap": "gap", "lead": "gap", "turn": []}],
  "result": 0,
  "uses": {"box_edge": {"format": "primlib.prim", "version": 1, "primitive": "box_edge", "...": "..."}},
  "motion": []
}
```

| Key | What it holds |
|---|---|
| `kind` | `"recipe"`. A file without `kind` is a primitive. |
| `slots` | The longest key, and the most a `series` holds, that the FreeCAD target lays out: it makes that many places, as a sheet can't grow. Readers have no limit. |
| `parts` | Each a primitive at values: `bind` maps its params to expressions over the recipe's names (a param not bound keeps its default). `mirror` is `"x"`, `"y"` or `"z"`, the part mirrored across the plane through its origin normal to that axis, or null. `colour` is `[r, g, b]`, 0 to 1, or null. `pieces` is null (all of it) or a list of the names of a compound's pieces to take (a hinge's `side_a`). `print` is true for a part on the print list. A bind can't use a series' index: each part is built once, wherever it is placed. |
| `place` | The placements, each referring only to those before it. |
| `result` | The id of the placement that is the recipe. |
| `uses` | Each primitive the parts use, as a version 1 document at its defaults: the file needs nothing else. |

A recipe's checks include its parts': a part whose primitive's checks fail at its values fails the recipe, named by the part.

### Placements

Each gives a list of placed parts. A placed part is turned about its own origin, then moved; `turn` is a list of `{"axis", "angle"}` (degrees, anticlockwise seen from the axis' + end) applied in order.

| `op` | Fields | Places |
|---|---|---|
| `instance` | `part`; `at`: x, y, z; `turn` | The part, turned, at `at`. |
| `row` | `key`: text; `pieces`: letter → `{part, length}`; `at`; `along`: `"x"`, `"y"`, `"z"`, `"-x"`, …; `gap`; `lead`; `turn` | A piece for each letter of the key, in order, end to end along `along` from `at`: `lead` before the first, `gap` between. A piece starts where its part's origin is, and the next starts `length + gap` further on. A letter not in `pieces` is an error: a recipe checks its keys. Each is named `{name}_{slot from 1}{letter}`. |
| `series` | `count`; `index`: `"i"`; `item` | `item` placed for i = 0, 1, … `count` − 1 (truncated), with `i` bound. |
| `choose` | `guard`; `then`; `otherwise`: an id or null | `then` if `guard` is over 0, else `otherwise`, or nothing. |
| `group` | `of`: a list | All of them. |
| `move` | `base`; `by`: x, y, z; `turn` | `base`'s placed parts turned about the origin, then moved by `by`. |
| `joint` | `base`; `at`: x, y, z; `axis`: `"x"`, `"y"` or `"z"`; `angle` | `base`'s placed parts turned by `angle` degrees about the line through `at` along `axis`: a lid on its hinge. The angle is an expression, so a parameter opens it (and later, `motion`). |

Fill a length is a `row` whose key the recipe makes from its counts (`edge_fill`: `repeat(<<B>>; floor(bigs / 2)) + …`), with the odd pieces' length a derived name; `spacing()` in `primlib/spacing.py` is its reference (`tests/test_recipe.py`).

**In FreeCAD** (`primlib/recipe_freecad.py`, `make_recipe`) a recipe is compiled to what stock FreeCAD recomputes: its names as sheet cells, a master per part, and links per slot and letter whose `Visibility` and place are formulas, so a key, count or size changed on the sheet lays out again, up to `slots`. There a turn's angle must be a number, and a row, series or joint can't be inside a series.

`primlib/recipe.py` has the reference layout in plain Python (`layout(doc, values)`); recipes are in `primlib/recipes/`, and `primlib export` writes them as primitives are.

## Assemblies

An assembly (version 2, `"kind": "assembly"`) is a recipe whose parts may also be recipes or assemblies: `uses` holds each, as a whole document with its own `uses`. A part that is a recipe or assembly is bound as a primitive is, and its placed parts are placed as one, named `{placement}/{its name}`, with part `{part}/{its part}`: the hinged lid's lid run gives `lid_run/edge_1S`, part `edges/S`. A recipe or assembly part marked `print` puts all its primitives on the print list; `pieces` and `mirror` apply to primitives only.

**In FreeCAD** a recipe or assembly part has its own cells (`{name}_{part}_{x}`, bound to the outer ones) and masters, made once, and its placements laid out as links wherever it is placed. A joint is an App::Part whose `Roll`, `Pitch` or `Yaw` and base are formulas over its angle, as the hybrid case's lid is, holding the links it turns: the angle changed on the sheet opens it. Masters of parts to print go in the `{name} print list` group; a part of some pieces is a compound of those. `tools/recipe_check.py` compares every link's place, the Status cell and the print list with `layout`, before and after saving.

`primlib/assemblies/hinged_lid.py` is the example: two keyed edge runs, the hinge's side A with the lid run and its side B and pins with the base run, the lid side on a `joint` by `open_angle`. `leaf_parts(doc, values)` gives each primitive part by path with its values, pieces, colour and print mark.

## Readers and versions

**When a reader can't build an operation** (`text` without a font, say), it says which, by `op` and `name`. It doesn't show a part half built.

**Version changes:**
- A new operation or field that older readers may ignore keeps the version, and an older reader reports the new operation as unknown.
- A change in what an existing field means, or a new kind of document, is a new version. Version 2 brought recipes and assemblies; primitives are still written as version 1.

**What later versions add:**
- `motion`: view4d M6;
- part colours.
