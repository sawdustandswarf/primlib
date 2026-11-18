"""HINGE -- the library's hinge: VerticalHinge3 / 3b, print in place, with leaves to screw on."""

import math

from primlib.core import Builder, Param, Primitive, grouped

MAIN = (
    Param("length", "40", "along the axis"),
    Param("rings", "4", "rings, side A's the first and every other; at least 2"),
    Param("side_a", "18", "side A's side plate, beyond the tab (VerticalHinge3 18, 3b 7.5)"),
    Param("side_b", "=side_a", "side B's side plate: shorter to clear something on that side"),
)
RINGS = (
    Param("pin_d", "6", "pin shaft diameter"),
    Param("pin_gap", "0.5", "pin to ring, radial"),
    Param("ring_wall", "3", "ring wall"),
    Param("ring_gap", "0.1", "between rings, along the axis"),
    Param("shear", "0.05", "width of a ring's pointed end"),
)
LEAVES = (
    Param("plate", "14", "the two tabs' width together, across the axis"),
    Param("plate_t", "5", "leaf thickness"),
    Param("plate_gap", "1", "between the two leaves' tabs"),
    Param("backset", "1", "added to the rings' outside radius: the axis to the mounting face"),
    Param("chamfer", "0.5", "45 degree chamfer on the leaves' square edges"),
    Param("head_r", "3.05", "countersink radius and depth, at the leaf's outer face"),
    Param("screw_r", "1.7", "screw hole radius"),
    Param("screw_len", "20", "screw hole tool's length"),
)
S = 1 / math.sqrt(2)


class Hinge(Primitive):
    """The library's hinge: VerticalHinge3 (and 3b, the same hinge 13 long with 2 rings and 7.5 side
    plates), the hinge printed and confirmed for the hybrid case. Print in place,
    standing on end: two sides of interleaved rings on a pin, each side with a
    leaf to screw to a panel.

    The axis runs along z from 0 to `length`. Side A's leaf runs along +x and
    side B's along -x; their mounting faces are at +y, `pin_d / 2 + pin_gap +
    ring_wall + backset` from the axis. Rings are `length / rings` apart, side A's
    the first and every other one. The pin is a stack of flared slices, one per
    ring. Each leaf is cut clear of the other side's rings over half a turn, so
    the hinge rolls from folded flat to open flat.

    The leaves' square edges carry a 45 degree `chamfer`, cut flat into the box,
    so it holds as the hinge resizes. `side_b` defaults to `side_a`; set it
    shorter where side B's leaf has to clear something (the T hinge under a
    corner).

    The result is a compound of three solids, `{name}_side_a`, `{name}_side_b`
    and the pins (labelled `{name}_pins`), so a project can place the sides apart.
    """

    title = "Hinge"
    params, groups = grouped(("Main", MAIN), ("Rings and pin", RINGS), ("Leaves and screws", LEAVES))
    derived = (
        ("pitch", "length / rings", "ring pitch"),
        ("r_pin", "pin_d / 2", "pin radius"),
        ("r_in", "pin_d / 2 + pin_gap", "ring bore radius"),
        ("r_out", "pin_d / 2 + pin_gap + ring_wall", "ring outside radius"),
        ("face", "pin_d / 2 + pin_gap + ring_wall + backset", "axis to the mounting faces"),
    )
    checks = (
        ("rings - 1.5", "a hinge needs at least two rings"),
        ("length / rings - ring_gap - ring_wall", "the rings are too short for their wall"),
        ("plate / 2 - plate_gap / 2 + side_a - 2 * chamfer", "side A's leaf is too short"),
        ("plate / 2 - plate_gap / 2 + side_b - 2 * chamfer", "side B's leaf is too short"),
        ("plate_t - 2 * chamfer", "the leaves are too thin for their chamfer"),
    )

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        pitch, r_pin, r_in, r_out = "(pitch)", "(r_pin)", "(r_in)", "(r_out)"
        r_mid = f"({r_in} + ring_wall / 2)"
        r_clear = f"({r_out} + pin_gap)"
        r_flare = f"({r_pin} + ring_wall / 2)"
        tip = "shear / 2"
        top = f"({pitch} - ring_gap)"
        rise = "(ring_wall / 2)"
        ring = b.revolve("ring", [(r_mid, "0"), (r_out, rise), (r_out, f"{top} - {rise} + {tip}"),
                                  (f"{r_mid} + {tip}", top), (f"{r_mid} - {tip}", top),
                                  (r_in, f"{top} - {rise} + {tip}"), (r_in, rise)], ("0", "360"))
        slice_ = b.revolve("pin", [("0", "0"), (r_flare, "0"), (r_pin, rise), (r_pin, f"{pitch} - {rise}"),
                                   (r_flare, pitch), ("0", pitch)], ("0", "360"))
        # The roll clearance round one ring, half way round: the other side's leaf.
        low, high = "(-pin_gap)", f"({top} + pin_gap)"
        flank = f"({r_clear} - {r_mid} + {tip})"
        clearance = [(f"{r_mid} - {tip}", low), (f"{r_mid} + {tip}", low), (r_clear, f"{low} + {flank}"),
                     (r_clear, f"{high} - {flank}"), (f"{r_mid} + {tip}", high), (f"{r_mid} - {tip}", high),
                     (r_pin, f"{high} - {flank}"), (r_pin, f"{low} + {flank}")]
        if None in (ring, slice_):
            return None
        two = f"2 * {pitch}"
        count_a, count_b = "ceil(rings / 2)", "floor(rings / 2)"
        rings_a = b.array("rings_a", ring, "z", count_a, "0", two)
        rings_b = b.array("rings_b", ring, "z", count_b, pitch, two)
        pins = b.array("pins", slice_, "z", "rings", "0", pitch)
        around_a = b.array("around_a", b.revolve("clear_a", clearance, ("90", "270")), "z", count_a, "0", two)
        around_b = b.array("around_b", b.revolve("clear_b", clearance, ("-90", "90")), "z", count_b, pitch, two)
        core = b.cylinder("core", "z", ("0", "0"), r_mid, ("0", "length"))
        tabs = {}
        for side, sign in (("a", 1), ("b", -1)):
            reach = f"(plate / 2 + side_{side})"
            x = ("plate_gap / 2", reach) if sign > 0 else (f"-{reach}", "-plate_gap / 2")
            y = ("face - plate_t", "face")
            leaf = b.box(f"leaf_{side}", x, y, ("0", "length"))
            screw_x = f"{'' if sign > 0 else '-'}(plate / 2 + side_{side} / 2)"
            y0 = "(face - plate_t)"
            screw = b.fuse(f"screw_{side}", [
                b.cylinder(f"screw_{side}_shank", "y", (screw_x, "0"), "screw_r", (y0, f"{y0} + screw_len")),
                b.cone(f"screw_{side}_head", "y", (screw_x, "0"), "head_r", "0", (y0, f"{y0} + head_r"))])
            holes = b.array(f"holes_{side}", screw, "z", "rings", f"{pitch} / 2", pitch)
            around = around_b if side == "a" else around_a
            tabs[side] = b.cut(f"tab_{side}", leaf, [core, around, holes] + chamfers(b, f"leaf_{side}", x, y))
        side_a = b.fuse("side_a", [rings_a, tabs["a"]])
        side_b = b.fuse("side_b", [rings_b, tabs["b"]])
        return b.finish(b.compound(None, [side_a, side_b, pins]))


def chamfers(b, name, x, y):
    """The 45 degree `chamfer` on the twelve edges of the box spanning `x`, `y`
    and z 0..length, as flat cuts."""
    spans = {"x": x, "y": y, "z": ("0", "length")}
    tools = []
    for first, second in (("x", "y"), ("y", "z"), ("x", "z")):
        for i, s1 in enumerate((-1, 1)):
            for j, s2 in enumerate((-1, 1)):
                f1, f2 = spans[first][i], spans[second][j]
                normal = [0.0, 0.0, 0.0]
                normal["xyz".index(first)] = s1 * S
                normal["xyz".index(second)] = s2 * S
                d = f"(({s1}) * ({f1}) + ({s2}) * ({f2}) - chamfer) * {S:.10f}"
                tools.append(b.beyond(f"{name}_chamfer_{first}{second}{i}{j}", normal, d, "1000"))
    return tools
