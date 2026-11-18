"""SUPPORT_RECT -- a print support filling a rectangle with concentric
rectangular walls between two sparse interface layers."""

from primlib.core import Builder, Param, Primitive


class SupportRect(Primitive):
    """A print support under your own control, filling a rectangle
    `length` (x) by `width` (y), its corner at the origin, from the face
    below at z = 0 to the face it holds up at z = `height`.

    Concentric rectangular walls, each `wall_lines` lines wide with
    `gap_lines` lines between them, stand between two interface layers,
    one `layer_h` layer each. As many rings as fit the short side are
    laid in from the outside, the innermost leaving at least a gap across
    the middle; when the middle is wider than a gap and a line, a middle
    line runs along the long side, so no span is much wider than a gap.

    Each interface layer is single-line strips across the short side,
    `interface_density` of the area (0.33: a line in every three), laid in
    from both ends, with a middle strip when the middle gap is wider than
    the strip spacing, and a line round the outside joining the strips'
    ends. The top layer stops `interface_gap` under the
    supported face, and the bottom layer starts `bottom_gap` above z = 0
    (0 on the bed), so the support breaks away after printing.

    Built from the rings' sides, mitred at the corners: a Draft array of
    stripes in from each end, kept where that end is the nearest side of
    the rectangle (two triangles per direction), plus the middle line,
    which lies on the innermost ring when there is none; the interface
    strips are Draft arrays in from each end the same way.
    """

    title = "Rectangle support"
    params = (
        Param("length", "20", "length of the support, along x"),
        Param("width", "10", "width of the support, along y"),
        Param("height", "3", "face below (z = 0) to the supported face, along z"),
        Param("line_w", "0.44", "print line width"),
        Param("layer_h", "0.2", "print layer height: each interface layer's thickness"),
        Param("wall_lines", "1", "wall width, in line widths"),
        Param("gap_lines", "4", "gap between walls, in line widths"),
        Param("interface_density", "0.33", "interface layers' strips, as a share of their area"),
        Param("interface_gap", "0.1", "top interface layer to the supported face"),
        Param("bottom_gap", "=interface_gap", "face below to the bottom interface layer (0 on the bed)"),
    )
    derived = (
        ("wall", "wall_lines * line_w", "wall width"),
        ("gap", "gap_lines * line_w", "gap between walls"),
        ("pitch", "wall + gap", "ring spacing"),
        ("long_x", "(length >= width ? 1 : 0)", "1 if the long side is along x"),
        ("short", "(long_x > 0 ? width : length)", "short side"),
        ("long", "(long_x > 0 ? length : width)", "long side"),
        ("rings", "max(1; floor((short / 2 - wall - gap / 2) / pitch) + 1)",
         "number of rings: as many as leave a gap across the middle"),
        ("inset", "(rings - 1) * pitch", "innermost ring in from the outside"),
        ("hollow", "short - 2 * (inset + wall)", "middle, across the short side"),
        ("middle", "(hollow > gap + wall ? 1 : 0)", "1 if there is a middle line"),
        ("mid_lo", "(middle > 0 ? (short - wall) / 2 : inset)",
         "middle line's side, across the short side"),
        ("wall_lo", "bottom_gap + layer_h", "walls' bottom, on the bottom interface layer"),
        ("wall_hi", "height - interface_gap - layer_h", "walls' top, under the top interface layer"),
        ("strip_pitch", "line_w / interface_density", "interface strip spacing"),
        ("strip_gap", "strip_pitch - line_w", "gap between interface strips"),
        ("strips", "max(1; floor((long / 2 - line_w - strip_gap / 2) / strip_pitch) + 1)",
         "interface strips in from each end: as many as leave a gap across the middle"),
        ("strip_in", "(strips - 1) * strip_pitch", "innermost strip in from its end"),
        ("strip_mid", "(long - 2 * (strip_in + line_w) > strip_pitch ? (long - line_w) / 2 : strip_in)",
         "middle strip's side along the long side (on the innermost strip if none)"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        span = ("wall_lo", "wall_hi")
        stripes_x = [b.array(f"stripes_x_{end}", b.box(
            f"stripe_x_{end}", ("0", "wall"), ("0", "width"), span),
            "x", "rings", start, step)
            for end, start, step in (("lo", "0", "pitch"),
                                     ("hi", "length - wall", "-pitch"))]
        stripes_y = [b.array(f"stripes_y_{end}", b.box(
            f"stripe_y_{end}", ("0", "length"), ("0", "wall"), span),
            "y", "rings", start, step)
            for end, start, step in (("lo", "0", "pitch"),
                                     ("hi", "width - wall", "-pitch"))]
        # Where each end is the nearest side: a triangle on it, apex at the
        # 45 deg mitre lines' meeting point (outside the rectangle if need be).
        near_x = [b.prism("near_x_lo", [("0", "0"), ("width / 2", "width / 2"),
                                         ("0", "width")], "xy", span),
                  b.prism("near_x_hi", [("length", "0"), ("length", "width"),
                                         ("length - width / 2", "width / 2")], "xy", span)]
        near_y = [b.prism("near_y_lo", [("0", "0"), ("length", "0"),
                                         ("length / 2", "length / 2")], "xy", span),
                  b.prism("near_y_hi", [("0", "width"), ("length / 2", "width - length / 2"),
                                         ("length", "width")], "xy", span)]
        if None in near_x + near_y:
            return None
        sides = [b.common(f"sides_{a}", [b.fuse(f"stripes_{a}", stripes),
                                          b.fuse(f"near_{a}", near)])
                 for a, stripes, near in (("x", stripes_x, near_x), ("y", stripes_y, near_y))]
        line = b.box("middle_line",
                     ("long_x > 0 ? inset + wall : mid_lo",
                      "long_x > 0 ? length - inset - wall : mid_lo + wall"),
                     ("long_x > 0 ? mid_lo : inset + wall",
                      "long_x > 0 ? mid_lo + wall : width - inset - wall"), span)
        layers = [interface(b, "bottom", ("bottom_gap", "wall_lo")),
                  interface(b, "top", ("wall_hi", "height - interface_gap"))]
        return b.finish(b.fuse(None, sides + [line] + layers))


def interface(b, side, span):
    """An interface layer over `span`: strips across the short side, in
    from both ends along the long side, the middle strip, and a line round
    the outside joining them."""
    # Each strip in x and y; the arrays run along whichever is the long side.
    strip_x = ("0", "long_x > 0 ? line_w : length")
    strip_y = ("0", "long_x > 0 ? width : line_w")
    ends = []
    for end, start, step in (("lo", "0", "strip_pitch"),
                             ("hi", "long - line_w", "-strip_pitch")):
        ends.append(b.grid(f"{side}_strips_{end}", b.box(f"{side}_strip_{end}", strip_x, strip_y, span), {
            "x": ("long_x > 0 ? strips : 1", f"long_x > 0 ? {start} : 0", step),
            "y": ("long_x > 0 ? 1 : strips", f"long_x > 0 ? 0 : {start}", step)}))
    mid = b.box(f"{side}_strip_mid",
                ("long_x > 0 ? strip_mid : 0", "long_x > 0 ? strip_mid + line_w : length"),
                ("long_x > 0 ? 0 : strip_mid", "long_x > 0 ? width : strip_mid + line_w"), span)
    # A line round the outside, joining the strips' ends.
    border = b.cut(f"{side}_border", b.box(f"{side}_border_out", ("0", "length"), ("0", "width"), span),
                   [b.box(f"{side}_border_in", ("line_w", "length - line_w"),
                          ("line_w", "width - line_w"), ("-1", "height + 1"))])
    return b.fuse(f"{side}_interface", ends + [mid, border])
