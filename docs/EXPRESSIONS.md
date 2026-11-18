# Expressions

Every size in a primitive is an expression over its names: `pitch / 2`, `max(wall; 2 * line_w)`, `end_taper > 0 ? 1 : 0`. It is written once, in the primitive, and every target uses it as written:

- **FreeCAD** binds it to the parameter sheet unchanged, so FreeCAD evaluates it.
- **The record target** keeps it in the operation tree, for a reader such as view4d to evaluate.

The language is the part of FreeCAD's expression language that primlib uses, and nothing else, so an expression means the same in both. `primlib/expr.py` is the reference evaluator, in plain Python. `tools/expr_check.py` checks it against FreeCAD on every expression of every recorded primitive, and `tests/test_expr.py` covers the edge cases.

## Values

- **Numbers** are plain: lengths in mm, angles in degrees, counts, and 0/1 switches. There are no units, except as written below.
- **Literals:** `2`, `0.5`, `.5`, `1.`, `1e-6`.
  - `deg` or `mm` may follow a literal (`180 deg`, `1deg`, `2 mm`). Each means × 1. They are there because FreeCAD wants them in places, for example `asin(x) / 1deg` for a plain number.
- **Names:** the primitive's parameters, fixed values and derived values. Inside a `series` operation, its index `i` (0, 1, …) is a name too.
- **Constant:** `pi`.
- **Text:** a parameter whose default starts with `'` is text, as FreeCAD writes a text cell (`'OAK`): a font path, a line of text, a key (`'SFMF`). In an expression a text literal is written `<<SFMF>>`, as FreeCAD writes it. Text is worked with as [below](#text), and never mixed with numbers: `<<a>> + 1` is an error.

## Operators

From loosest to tightest:

| Operators | Meaning |
|---|---|
| `c ? a : b` | `a` if `c` is not 0, else `b`. Only the chosen side is evaluated. It nests to the right, but write nested conditionals with parentheses: FreeCAD has dropped them on save. |
| `<` `>` `<=` `>=` `==` `!=` | 1 if true, else 0. Only one per level: write `(a < b) == c`. |
| `+` `-` | Add and subtract, left to right. |
| `*` `/` | Multiply and divide, left to right. Dividing by 0 is an error. |
| `-a`, `+a` | Negation. The unary plus does nothing. The library writes `+(c ? a : b)` so that FreeCAD keeps the parentheses. |
| `s[a:b]`, `s[k]` | A slice of text, or one letter of it (see [Text](#text)). |
| `( … )` | Grouping. |

## Functions

Arguments are separated by `;`, as FreeCAD writes them. `,` is also accepted.

| Function | Value |
|---|---|
| `sin(a)`, `cos(a)`, `tan(a)` | `a` in degrees. |
| `asin(x)`, `acos(x)`, `atan(x)` | In degrees. |
| `atan2(y; x)` | In degrees. |
| `sqrt(x)`, `abs(x)` | |
| `floor(x)`, `ceil(x)` | |
| `min(a; b; …)`, `max(a; b; …)` | One argument or more. |
| `mod(a; b)` | The remainder of a / b, with a's sign, as C's `fmod`: `mod(-7; 3)` is −1. |

### Bounds of another operation (record target only)

`xmin(@3)`, `xmax(@3)`, `ymin(@3)`, `ymax(@3)`, `zmin(@3)` and `zmax(@3)` give the bounding box of operation 3's result, as built. stencil uses them to size its bridges to the text.

In FreeCAD the same expression is written `Obj.Shape.BoundBox.XMin`. A reader has to build operation 3 before it can evaluate one.

## Text

For keys such as `'SFMF'` (a row of pieces, a letter each: [FORMAT.md](FORMAT.md)):

| Written | Value |
|---|---|
| `a + b` | The two joined, when both are text. |
| `a == b`, `a != b` | 1 or 0, when both are text. Text has no `<` or `>`. |
| `c ? a : b` | Either side may be text. |
| `s[a:b]` | The letters from `a` up to, not including, `b`, as Python slices: a negative index counts from the end, and the slice is clipped to the text (`<<SF>>[1:9]` is `F`, past the end is empty). Both ends are written: FreeCAD gives `s[1:]` as empty. |
| `s[k]` | Letter `k` (negative from the end). Past the end is an error; `s[k:k + 1]` is the safe form, empty past the end. |

Indices are whole numbers. Only a name is sliced or indexed, as in FreeCAD: `key[0:1]`, not `(key)[0:1]`.

### Text functions (record target; written out for FreeCAD)

FreeCAD has no function for a text's length, so these three are evaluated by the record target and readers, and written out for FreeCAD by `primlib.expr.freecad(text, slots)` over a fixed number of places (`slots`, a recipe's longest key):

| Function | Value | For FreeCAD |
|---|---|---|
| `len(s)` | How many letters. | A name's slots counted (`key[k:k + 1] != <<>>`), through `+`, `repeat` and `?:`. |
| `count(s; t)` | How many times `t` is in `s`, not overlapping. | One letter only: `t` of more letters is an error there. |
| `repeat(s; n)` | `s` `n` times; `n` whole, 0 or more. | `slots` conditionals joined. |

They hold in FreeCAD only for text up to `slots` letters long. A recipe checks its keys' lengths.

## Names and their order

The record of a primitive (`primlib/targets/record.py`) lists its names in the order they are evaluated:

1. **`params`:** each one's value, or its `default`.
   - A default that starts with `=` is a formula over the parameters before it.
   - One that starts with `'` is a string.
2. **`fixed`:** fixed values, as expressions over the parameters.
3. **`derived`:** derived values, in order. Each may use any name before it. A value may be text: an expression that comes out as text (`key + <<F>>`), or one written `'text`.

A **check** passes when its expression is over 0. Its message says what to change.

`primlib.expr.names(tree, values)` evaluates them, and `failed_checks(tree, env)` lists the checks that fail.

## What isn't in it

FreeCAD's units (other than the two above), `^` and `%`, slices with an end left out, references to cells and other objects (except the bounds above), and FreeCAD's other functions.

Something added here must also be added to `primlib/expr.py` and to view4d's reader. Add a test, and run `tools/expr_check.py`.
