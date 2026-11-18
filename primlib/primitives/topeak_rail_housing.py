"""TOPEAK RAIL HOUSING -- a block with the slot and centre guide a topeak_rail slides on."""

from primlib.core import Machined, Param, grouped
from primlib.primitives.rail15 import (LENGTH, SHAPE, SHAPE_CHECKS, TAPER, TAPER_CHECKS, along,
                                     left, right)
from primlib.primitives.topeak_rail import FIXED, GROOVE_CHECK, groove_points

HOUSING = (
    Param("clearance", "0.30", "the gap between the printed rail and housing, normal to "
                               "every face, per side"),
    LENGTH,
    Param("block_width", "80", "across, y"),
    Param("block_depth", "10", "down from the mating face, z"),
    TAPER,
    Param("printer_width_offset", "0", "added to the slot's width in the model, half to "
                                       "each side, so that the slot prints at its design "
                                       "width; the housing's own value, not part of the fit"),
)
REACH = "1"  # mm, how far the slot as a cut tool reaches above the mating face
PAST = "0.2"  # mm, how far a tapered slot carries on past the ends, still at 45 deg


class TopeakRailHousing(Machined):
    """The receiver for a `topeak_rail`: a block `block_width` (y) by
    `block_depth` (z) by `length` (x) with the slot cut along it, through both
    ends, and the centre guide left standing in it. It shares the rail's eight
    fixed parameters. The full dimensioned specification, with the working,
    is `topeak_rail_spec.html`. A real Topeak rack is not made to this part's
    numbers: this is the printed mate, for testing and for parts of our own.

    The rail has no tolerance, so the fit is all here: the slot is the rail
    grown by `clearance`, normal to every flat face, and the guide is the
    rail's groove shrunk by it. At the floor the radius is `tip_radius` +
    `clearance`, concentric with the rail's, so the slot's widest point is
    `width` + 2 x `clearance`.

    The mouth's lip has radius `root_radius` - `clearance`, concentric with
    the rail's root radius. It's rounded below a clearance of 1 and sharp from
    there up, chosen when the part is built. Either way the gap stays
    `clearance`: rebuild after moving the clearance across 1.

    **The frame is the rail's, not the block's:** the housing is centred on
    y = 0 and runs along x from 0 to `length`, with the rail's root at z = 0,
    so its mating face is at z = -`clearance` and its floor at z = -`depth` -
    `clearance`. A `topeak_rail` built at the same origin sits in it, mated,
    whatever the clearance.

    `end_taper` is an option, 0 (off) by default: lead-ins at both ends of the
    slot. Over the last `end_taper` of its length the slot grows by
    `end_taper`, normal to its faces, so at 45 degrees along x, and the guide
    shrinks by it; the mating face stays where it is. The choice of on or off
    is fixed when the part is built: rebuild after changing it.

    `printer_width_offset` is added to the slot's width, half to each side,
    across y only, and is the housing's own value. The guide and the block's
    outside don't change. With different offsets the two models don't show the
    printed gap, and may overlap as models.

    For an assembly, `body()` returns the block and, as a cut tool, the slot,
    reaching 1 above the face and past both ends.
    """

    title = "Topeak rail housing"
    params, groups = grouped(("Variable", HOUSING))
    fixed = FIXED
    derived = SHAPE + (
        ("grow", "clearance / tan(angle / 2)", "how far clearance moves the sharp corners"),
        ("floor_hw", "tip_hw + grow", "slot floor half-width, sharp"),
        ("mouth_hw", "root_hw + grow", "slot mouth half-width, sharp"),
        ("lip_end", "mouth_hw + t_root + 3", "past the lip, over the mating face"),
    )
    derived_on_page = False
    checks = SHAPE_CHECKS + TAPER_CHECKS + GROOVE_CHECK + (
        ("clearance", "clearance must be positive"),
        ("block_depth - depth - end_taper", "block_depth leaves no floor under the lead-ins"),
        ("block_width / 2 - floor_hw - end_taper / tan(angle / 2) - printer_width_offset / 2",
         "block_width leaves no wall beside the slot"),
        ("groove_depth - clearance - end_taper", "the guide is too low for its gap and lead-ins"),
    )
    fits = (("topeak_rail", "a rail slid in, built at the same origin"),)
    views = (
        ("front", "u", ("0", "-block_width / 2", "-clearance - block_depth"),
         ("0", "block_width / 2", "-clearance - block_depth"), 1, "block_width"),
        ("front", "v", ("0", "-block_width / 2", "-depth - clearance"),
         ("0", "-block_width / 2", "-clearance"), 1, "depth"),
        ("front", "v", ("0", "block_width / 2", "-clearance - block_depth"),
         ("0", "block_width / 2", "-clearance"), -1, "block_depth"),
        ("side", "u", ("0", "0", "-clearance - block_depth"),
         ("length", "0", "-clearance - block_depth"), 1, "length"),
    )

    @classmethod
    def body(cls, b):
        block = b.box("block", ("0", "length"), ("-block_width / 2", "block_width / 2"),
                      ("-clearance - block_depth", "-clearance"))
        lip = ("root_radius - clearance",)  # sharp from a clearance of root_radius up

        def points(e):
            floor_y, mouth_y = (f"floor_hw + ({e}) / tan(angle / 2)",
                                f"mouth_hw + ({e}) / sin(angle)")
            floor_z, floor_r = f"-depth - clearance - ({e})", f"tip_radius + clearance + ({e})"
            return ([(left(floor_y), floor_z, floor_r)] + groove_points(f"clearance + ({e})") + [
                (right(floor_y), floor_z, floor_r),
                (right(mouth_y), "-clearance") + lip,
                (right("lip_end"), "-clearance"), (right("lip_end"), f"-clearance + {REACH}"),
                (left("lip_end"), f"-clearance + {REACH}"), (left("lip_end"), "-clearance"),
                (left(mouth_y), "-clearance") + lip])

        slot = b.choose(
            "end_taper > 0",
            lambda: b.loft("slot", along(
                points, (f"end_taper + {PAST}", f"-{PAST}"), ("0", "end_taper"),
                ("0", "length - end_taper"), (f"end_taper + {PAST}", f"length + {PAST}")), "yz"),
            lambda: b.prism("slot", points("0"), "yz", (f"-({REACH})", f"length + {REACH}")))
        return None if slot is None else (block, [slot])
