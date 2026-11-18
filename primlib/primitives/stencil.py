"""STENCIL -- a pair of text templates for a board, registered on its edges by fences that switch on or off."""

from primlib.core import Builder, Param, Primitive, grouped

FONT = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
LINES = 6            # the most lines of text

TEXT = (
    Param("lines", "2", "lines of text in use: 1 to 6"),
    Param("text_size", "40", "capital height of the letters (each line's default)"),
    Param("font", f"'{FONT}", "the font file (each line's default); it must be installed where the file is opened"),
    Param("line_gap", "12", "between the lines, capital to capital, y (for the default line positions)"),
    Param("origin_x", "0", "the text's origin from the template's centre, x"),
    Param("origin_y", "0", "the text's origin from the template's centre, y"),
)
PLATE = (
    Param("length", "160", "the template's overall size, x, fences included"),
    Param("width", "120", "the template's overall size, y, fences included"),
    Param("thickness", "6", "the plate's thickness, z: at least the guide bearing's height for a router"),
    Param("bit_d", "6.35", "the router's guide bearing (or bit) diameter; 0 for a pencil or paint"),
    Param("clearance", "0.2", "between the fences and the board's edges"),
)
FENCES = (
    Param("fence_top", "0", "1: a fence along the top edge (+y), hooking over the board's edge; 0: none"),
    Param("fence_bottom", "1", "1: a fence along the bottom edge (-y); 0: none"),
    Param("fence_left", "1", "1: a fence along the left edge (-x); 0: none"),
    Param("fence_right", "0", "1: a fence along the right edge (+x); 0: none"),
    Param("fence_t", "3", "each fence's thickness"),
    Param("fence_depth", "6", "how far each fence reaches down the board's edge"),
)
WORDS = ("OAK", "48", "LINE 3", "LINE 4", "LINE 5", "LINE 6")


def line_params(i):
    """Line i's text, font, size, place and justification."""
    return (
        Param(f"text{i}", f"'{WORDS[i - 1]}", f"line {i}'s text"),
        Param(f"font{i}", "=font", f"line {i}'s font file"),
        Param(f"size{i}", "=text_size", f"line {i}'s capital height"),
        Param(f"line{i}_x", "0", f"line {i}'s anchor from the origin, x"),
        Param(f"line{i}_y", f"=(lines - 1) / 2 * (text_size + line_gap) - {i - 1} * (text_size + line_gap)",
              f"line {i}'s anchor from the origin, y (default: the lines stacked, centred on the origin)"),
        Param(f"h{i}", "1", f"line {i}'s horizontal justification on its anchor: 0 left, 1 centre, 2 right"),
        Param(f"v{i}", "1", f"line {i}'s vertical justification on its anchor: 0 top, 1 middle, 2 bottom "
                            "(the baseline), of the capital height"),
    )


DETAIL = (
    Param("bridges", "1", "1: bridges hold the letters' centres; 0: none, for a stencil font"),
    Param("bridge_w", "1.5", "each bridge's width, y"),
    Param("bar_a1", "0.19", "template A's lower bridge, as a fraction of the capital height"),
    Param("bar_a2", "0.62", "template A's upper bridge"),
    Param("bar_b1", "0.41", "template B's lower bridge"),
    Param("bar_b2", "0.82", "template B's upper bridge"),
)


def line_derived(i):
    return (
        (f"ax{i}", f"origin_x + line{i}_x", f"line {i}'s anchor, x"),
        (f"ay{i}", f"origin_y + line{i}_y", f"line {i}'s anchor, y"),
        (f"az{i}", f"lines > {i} - 0.5 ? -1 : -1000",
         f"line {i}'s text, z: just under the plate, or well below it when not in use"),
        (f"zb{i}", f"bridges > 0.5 ? (lines > {i} - 0.5 ? -1 : -1000) : -1000",
         f"line {i}'s bridges: in the plate, or below it (no bridges, or the line not in use)"),
        (f"lo{i}", f"ay{i} - (v{i} < 0.5 ? size{i} : (v{i} < 1.5 ? size{i} / 2 : 0))",
         f"line {i}'s baseline (the bottom of its capitals), y"),
    )


def line_checks(i):
    on = f"lines < {i} - 0.5 ? 1 : "
    return (
        (f"{on}(lo{i} - y_lo - bit_d / 2 - 1)", f"line {i} runs off the board's area at the bottom (y)"),
        (f"{on}(y_hi - lo{i} - size{i} - bit_d / 2 - 1)", f"line {i} runs off the board's area at the top (y)"),
        (f"{on}size{i}", f"line {i}'s size must be positive"),
        (f"(h{i} + 0.5) * (2.5 - h{i})", f"h{i} must be 0, 1 or 2"),
        (f"(v{i} + 0.5) * (2.5 - v{i})", f"v{i} must be 0, 1 or 2"),
    )


SIZES = "; ".join(f"size{i}" for i in range(1, LINES + 1))


class Stencil(Primitive):
    """Two templates for putting text on a board: up to six lines, each with
    its own font, size, place and justification, cut through a plate that
    lies on the board's face, registered by fences that hook over the
    board's edges, each switched on or off. Trace the letters with a pencil, paint through
    them, or rout them with a bearing-guided bit.

    The letters' centres (the middle of O, A, B, 4, 8 ...) are held by thin
    bridges across each line, as long as the line. **Template A** has its
    bridges at `bar_a1` and `bar_a2` of each line's capital height,
    **template B** at `bar_b1` and `bar_b2`, so each covers what the other's
    bridges hide: go over the letters with A, then again with B. Both
    register on the same fences, so they line up. With a stencil font, set
    `bridges` to 0 and use either. The result is a compound of `{name}_a`
    and `{name}_b`.

    **Frame:** the origin is the template's centre, on the board's face
    (z = 0), with the board below it. The plate lies on the face from z = 0
    to `thickness`, `length` along x and `width` along y, fences included;
    the text reads along +x, its tops towards +y.

    **Text:** `lines` lines (1 to 6) are placed from the text's origin,
    (`origin_x`, `origin_y`) from the template's centre, the centre itself by
    default. Line i's anchor is (`line{i}_x`, `line{i}_y`) from the origin;
    by default the lines are stacked down, `text_size` + `line_gap` apart,
    centred on the origin. `h{i}` sets where the anchor is along the line
    (0 left, 1 centre, 2 right) and `v{i}` where it is up the capitals (0
    top, 1 middle, 2 the baseline). Each line's `font{i}` and `size{i}`
    follow `font` and `text_size` unless set.

    **Fences:** `fence_top`, `fence_bottom`, `fence_left` and `fence_right`
    (1 on, 0 off) put a fence under the plate along that edge, `fence_t`
    thick, reaching `fence_depth` down the board's edge, `clearance` off it.
    Push the template against the fenced edges: two fences on adjacent
    sides locate it on a corner; one alone sets only its distance from that
    edge, as for text in the middle of a large board. The text must stay on
    the board, inside the fences (`x_lo` to `x_hi`, `y_lo` to `y_hi`).

    **Router:** the bearing rides the template's walls, so `thickness` must
    be at least the bearing's height, every stroke at least `bit_d` wide
    (the routed letters' inside corners are rounded to `bit_d` / 2), and
    each bridge of A at least `bridge_w` + `bit_d` from each of B's, so B
    can rout what A's bridges hid.

    **Print** each template top face down: the fences stand up, and nothing
    overhangs. The text, fonts
    and sizes are sheet cells: edit them and recompute. The build can't
    check what it can't see before the text is drawn: a line running off
    the plate's ends, and a letter whose centre the bridges don't hold (it
    shows as a separate solid in its template). The default bridge heights
    hold the capitals and digits of the default font.
    """

    title = "Stencil"
    params, groups = grouped(("Plate", PLATE), ("Fences", FENCES), ("Text", TEXT),
                             *((f"Line {i}", line_params(i)) for i in range(1, LINES + 1)),
                             ("Detail", DETAIL))
    derived = (
        ("x_lo", "-length / 2 + (fence_left > 0.5 ? fence_t + clearance : 0)",
         "the board's area under the template, left end: inside the left fence, if any"),
        ("x_hi", "length / 2 - (fence_right > 0.5 ? fence_t + clearance : 0)", "and its right end"),
        ("y_lo", "-width / 2 + (fence_bottom > 0.5 ? fence_t + clearance : 0)", "and its bottom edge"),
        ("y_hi", "width / 2 - (fence_top > 0.5 ? fence_t + clearance : 0)", "and its top edge"),
        ("sep", f"min(abs(bar_a1 - bar_b1); abs(bar_a1 - bar_b2); abs(bar_a2 - bar_b1); abs(bar_a2 - bar_b2))"
                f" * min({SIZES})", "the closest bridges of A and B, centre to centre, on the smallest line"),
    ) + tuple(d for i in range(1, LINES + 1) for d in line_derived(i))
    checks = (
        (f"(lines - 0.5) * ({LINES} + 0.5 - lines)", f"lines must be 1 to {LINES}"),
        ("sep - bridge_w - bit_d + 0.000001", "A's and B's bridges are closer than bridge_w + bit_d: "
                                               "B can't rout what A's bridges hide"),
        ("bridge_w", "bridge_w must be positive"),
        ("min(bar_a1; bar_a2; bar_b1; bar_b2) * (1 - max(bar_a1; bar_a2; bar_b1; bar_b2))",
         "each bridge must lie within the capital height (between 0 and 1)"),
        ("thickness", "thickness must be positive"),
        ("fence_t", "fence_t must be positive"),
        ("fence_depth", "fence_depth must be positive"),
        ("x_hi - x_lo - 2 * bit_d - 2", "the fences leave too little of the board's area"),
        ("y_hi - y_lo - 2 * bit_d - 2", "the fences leave too little of the board's area"),
    ) + tuple(c for i in range(1, LINES + 1) for c in line_checks(i))
    views = (
        ("front", "u", ("0", "-width / 2", "-fence_depth"), ("0", "width / 2", "-fence_depth"), 1, "width"),
        ("front", "v", ("0", "width / 2", "0"), ("0", "width / 2", "thickness"), -1, "thickness"),
        ("front", "v", ("0", "-width / 2", "-fence_depth"), ("0", "-width / 2", "0"), 1, "fence_depth"),
        ("side", "u", ("-length / 2", "0", "-fence_depth"), ("length / 2", "0", "-fence_depth"), 1, "length"),
        ("top", "u", ("origin_x + line1_x", "lo1", "thickness"),
         ("origin_x + line1_x", "lo1 + size1", "thickness"), -1, "text_size"),
        ("top", "mark", ("origin_x", "origin_y", "thickness"), None, 0, ""),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        body = b.fuse("body", [
            b.box("plate", ("-length / 2", "length / 2"), ("-width / 2", "width / 2"), ("0", "thickness")),
            # each fence under its edge, or (off) a sliver inside the plate, which the fuse absorbs
            b.box("fence_top", ("-length / 2", "length / 2"), ("width / 2 - fence_t", "width / 2"),
                  ("fence_top > 0.5 ? -fence_depth : 0.001", "0.01")),
            b.box("fence_bottom", ("-length / 2", "length / 2"), ("-width / 2", "-width / 2 + fence_t"),
                  ("fence_bottom > 0.5 ? -fence_depth : 0.001", "0.01")),
            b.box("fence_left", ("-length / 2", "-length / 2 + fence_t"), ("-width / 2", "width / 2"),
                  ("fence_left > 0.5 ? -fence_depth : 0.001", "0.01")),
            b.box("fence_right", ("length / 2 - fence_t", "length / 2"), ("-width / 2", "width / 2"),
                  ("fence_right > 0.5 ? -fence_depth : 0.001", "0.01"))])
        strings = [b.shapestring(f"line{i}_string", f"text{i}", f"font{i}", f"size{i}",
                                 (f"ax{i}", f"ay{i}", f"az{i}"), f"v{i} * 3 + h{i}")
                   for i in range(1, LINES + 1)]
        letters = b.fuse("letters", [b.extrude(f"line{i}", s, "thickness + 2")    # z -1 to thickness + 1
                                     for i, s in enumerate(strings, 1)])
        # each template: the plate less the letters, less its bridges
        parts = []
        for t in ("a", "b"):
            bars = []
            for i, s in enumerate(strings, 1):
                lo, hi = b.extent(s, "x")
                x = (f"{lo} - 0.2", f"{hi} + 0.2")
                for j in (1, 2):
                    y = f"lo{i} + bar_{t}{j} * size{i}"
                    bars.append(b.box(f"{t}_bar{i}{j}", x, (f"{y} - bridge_w / 2", f"{y} + bridge_w / 2"),
                                      (f"zb{i}", f"zb{i} + thickness + 2")))
            parts.append(b.cut(t, body, [b.cut(f"{t}_cutter", letters, bars)]))
        return b.finish(b.compound(None, parts))
