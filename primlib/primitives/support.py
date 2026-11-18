"""SUPPORT -- a wall pierced by a row of diamonds, holding up a part and
cut away after printing."""

from primlib.core import Machined, Param


class Support(Machined):
    """A print support under your own control: a wall `length` (x) by
    `width` (y) by `thickness` (z), its corner at the origin, pierced by a
    row of diamond holes. Put it between the bed (or a lower part) at z = 0
    and the part it holds up at z = `thickness`; after printing, cut
    through the necks to separate them.

    Sizes are in print units, from `line_w` and `layer_h`. Between the
    holes the wall is a row of hourglasses, narrowing at mid-height to a
    neck `neck_lines` lines wide -- the cut points. At 0 the hourglasses
    meet in lines, and the result is two solids, above and below the
    necks, touching only there. The holes are at least `gap_lines` lines
    wide at the necks: as many hourglasses as fit share `length` evenly.
    A skin of `skin_layers`
    layers along the bottom and top ties them into one wall and gives the
    part above a full face to print on.

    The flanks are at 45 deg and meet at the neck, so a hole is a square
    diamond, as tall as it is wide; the wall is at least a hole and both
    skins tall,
    and the top skin takes whatever height is left, so the wall is exactly
    `thickness` tall.

    Built as a box minus a fused Draft array of `count` + 1 diamond holes,
    each a sketch in the xz plane extruded along y; the first and last are
    centred on the ends, so the wall ends in half holes.
    """

    title = "Support"
    params = (
        Param("length", "30", "length of the wall, along x"),
        Param("width", "1.2", "width of the wall, along y"),
        Param("thickness", "1.4", "bed (or lower part) to the supported face, along z"),
        Param("line_w", "0.44", "print line width"),
        Param("layer_h", "0.2", "print layer height"),
        Param("neck_lines", "0", "neck width at mid-height, in line widths (where it is cut)"),
        Param("gap_lines", "2", "least hole width at mid-height, in line widths"),
        Param("skin_layers", "1", "bottom skin, and least top skin, in layers"),
    )
    derived = (
        ("neck", "neck_lines * line_w", "neck width"),
        ("skin", "skin_layers * layer_h", "bottom skin thickness"),
        ("count", "floor(length / (neck + gap_lines * line_w))",
         "number of hourglasses: as many as fit with the least gap"),
        ("pitch", "length / count", "hourglass width and hole spacing"),
        ("half_w", "(pitch - neck) / 2", "half width of a hole at mid-height"),
        ("hole_h", "2 * half_w", "hole height, its flanks at 45 deg"),
        ("min_thickness", "2 * skin + hole_h", "thinnest wall: a hole and both skins"),
        ("mid", "skin + hole_h / 2", "height of the necks' middle"),
        ("hole_top", "skin + hole_h", "top tip of the holes"),
        ("top_skin", "thickness - hole_top", "top skin thickness"),
    )
    checks = (
        ("length", "length must be positive"),
        ("width", "width must be positive"),
        ("line_w", "line_w must be positive"),
        ("layer_h", "layer_h must be positive"),
        ("neck_lines + 0.000001", "neck_lines must not be negative"),
        ("gap_lines", "gap_lines must be positive"),
        ("skin_layers", "skin_layers must be positive"),
        ("count", "length is too short for one neck and gap"),
        ("thickness - min_thickness + 0.000001",
         "thickness is less than a 45 deg hole and both skins (min_thickness); "
         "make it thicker, or reduce gap_lines or skin_layers"),
    )

    @classmethod
    def body(cls, b):
        wall = b.box("wall", ("0", "length"), ("0", "width"), ("0", "thickness"))
        # The first hole, centred on x = 0; the "zx" plane takes (z, x) points.
        hole = b.prism("hole", [
            ("skin", "0"), ("mid", "half_w"), ("hole_top", "0"), ("mid", "-half_w"),
        ], "zx", ("-1", "width + 1"))
        if hole is None:
            return None
        return wall, [b.array("holes", hole, "x", "count + 1", "0", "pitch")]
