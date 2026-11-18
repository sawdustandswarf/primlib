"""SUPPORT_HALF -- a print support filling a half cylinder with concentric
half rings between two radial interface layers."""

from primlib.core import Builder, Param, Primitive


class SupportHalf(Primitive):
    """A print support under your own control for a round part: a half
    cylinder of `radius` on the +y side of the x axis, centred on the
    origin, from the face below at z = 0 to the face it holds up at
    z = `height`.

    Concentric half-ring walls, each `wall_lines` lines wide with
    `gap_lines` lines between them, are laid in from the rim, and a wall
    along the flat side ties them together. They stand between two
    interface layers, one `layer_h` layer each. Each interface layer is
    radial: single-line spokes from the centre, as many as make
    `interface_density` of the rim (0.33: a line in every three), joined by
    a line round the rim and one along the flat side. Cut off at x = `trim`, it keeps a wall along the cut, and each
    interface layer a line, so the boundary stays closed. The top layer
    stops `interface_gap` under the supported face,
    and the bottom layer starts `bottom_gap` above z = 0 (0 on the bed),
    so the support breaks away after printing.

    The spokes are a Draft polar array, so their number follows the
    sheet; the number of rings is fixed when the support is built (each
    ring is its own pair of cylinders), and rings that no longer fit
    shrink onto the innermost -- rebuild to lay them in again.
    """

    title = "Half-cylinder support"
    params = (
        Param("radius", "5", "radius of the half cylinder"),
        Param("height", "3", "face below (z = 0) to the supported face, along z"),
        Param("line_w", "0.44", "print line width"),
        Param("layer_h", "0.2", "print layer height: each interface layer's thickness"),
        Param("wall_lines", "1", "wall width, in line widths"),
        Param("gap_lines", "4", "gap between walls, in line widths"),
        Param("interface_density", "0.33", "interface layers' spokes, as a share of their area"),
        Param("interface_gap", "0.1", "top interface layer to the supported face"),
        Param("bottom_gap", "=interface_gap", "face below to the bottom interface layer (0 on the bed)"),
        Param("trim", "=-radius", "cut off at x = trim, keeping x >= trim, with a wall along the cut "
              "(-radius: the whole half)"),
    )
    derived = (
        ("wall", "wall_lines * line_w", "wall width"),
        ("gap", "gap_lines * line_w", "gap between walls"),
        ("pitch", "wall + gap", "ring spacing"),
        ("rings", "max(1; floor((radius - 2 * wall) / pitch) + 1)",
         "number of half rings, in from the rim"),
        ("wall_lo", "bottom_gap + layer_h", "walls' bottom, on the bottom interface layer"),
        ("wall_hi", "height - interface_gap - layer_h", "walls' top, under the top interface layer"),
        ("spokes", "max(2; floor(pi * radius * interface_density / line_w))",
         "interface spokes: lines covering interface_density of the rim"),
        ("spoke_step", "180 deg / spokes", "angle between spokes"),
        ("reach", "radius * 1.2", "spokes' length before they are trimmed to the rim"),
        ("keep_lo", "(trim > -radius ? trim : -radius - 1)", "the kept part's low x"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        span = ("wall_lo", "wall_hi")
        half = b.box("half", ("keep_lo", "radius + 1"), ("0", "radius + 1"),
                     ("-1", "height + 1"))
        disc = b.cylinder("disc", "z", ("0", "0"), "radius", ("-1", "height + 1"))

        def ring(i):
            outer = f"max(radius - {i} * pitch; 2 * wall)"
            return b.cut(f"ring{i}", b.cylinder(f"ring{i}_out", "z", ("0", "0"), outer, span),
                         [b.cylinder(f"ring{i}_in", "z", ("0", "0"), f"{outer} - wall",
                                     ("wall_lo - 1", "wall_hi + 1"))])

        rings = b.series("rings", "rings", ring)
        flat = b.box("flat", ("-radius", "radius"), ("0", "wall"), span)
        cut = b.box("cut_wall", ("trim", "trim + wall"), ("0", "radius"), span)
        walls = b.common("walls", [b.fuse("walls_all", [rings, flat, cut]), disc, half])
        layers = [interface(b, "bottom", ("bottom_gap", "wall_lo"), half, disc),
                  interface(b, "top", ("wall_hi", "height - interface_gap"), half, disc)]
        if None in layers:
            return None
        return b.finish(b.fuse(None, [walls] + layers))


def interface(b, side, span, half, disc):
    """A radial interface layer over `span`: single-line spokes from the centre,
    a line round the rim, one along the flat side and one along the cut,
    trimmed to the kept part of the half cylinder. None if the spoke's
    sketch fails."""
    # The first spoke, a line wide, at half a step from the flat side.
    c, s = "cos(spoke_step / 2)", "sin(spoke_step / 2)"
    spoke = b.prism(f"{side}_spoke", [
        (f"line_w / 2 * {s}", f"-line_w / 2 * {c}"),
        (f"reach * {c} + line_w / 2 * {s}", f"reach * {s} - line_w / 2 * {c}"),
        (f"reach * {c} - line_w / 2 * {s}", f"reach * {s} + line_w / 2 * {c}"),
        (f"-line_w / 2 * {s}", f"line_w / 2 * {c}")], "xy", span)
    if spoke is None:
        return None
    spokes = b.polar(f"{side}_spokes", spoke, "spokes", "180 deg - spoke_step")
    rim = b.cut(f"{side}_rim", b.cylinder(f"{side}_rim_out", "z", ("0", "0"), "radius", span),
                [b.cylinder(f"{side}_rim_in", "z", ("0", "0"), "radius - line_w",
                            ("-1", "height + 1"))])
    flat = b.box(f"{side}_flat", ("-radius", "radius"), ("0", "line_w"), span)
    cut = b.box(f"{side}_cut", ("trim", "trim + line_w"), ("0", "radius"), span)
    return b.common(f"{side}_interface", [b.fuse(f"{side}_parts", [spokes, rim, flat, cut]),
                                          disc, half])
