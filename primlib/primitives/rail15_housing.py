"""15 MM RAIL HOUSING -- a block with the slot a 15 mm rail slides in."""

from primlib.core import Machined, Param, grouped
from primlib.primitives.rail15 import (DEPTH, FIXED, LENGTH, SHAPE, SHAPE_CHECKS, TAPER, TAPER_CHECKS,
                                     along, left, right)

HOUSING = (
    Param("clearance", "0.20", "the gap between the printed rail and housing, normal to "
                               "every face, per side"),
    LENGTH,
    DEPTH,
    Param("block_width", "25", "across, y"),
    Param("block_depth", "6", "down from the mating face, z"),
    TAPER,
    Param("printer_width_offset", "0", "added to the slot's width in the model, half to "
                                       "each side, so that the slot prints at its design "
                                       "width; the housing's own value, not part of the fit"),
)
REACH = "1"  # mm, how far the slot as a cut tool reaches above the mating face
PAST = "0.2"  # mm, how far a tapered slot carries on past the ends, still at 45 deg


class Rail15Housing(Machined):
    """The receiver for a `rail15`: a block `block_width` (y) by
    `block_depth` (z) by `length` (x) with the slot cut along it, through
    both ends. It shares the rail's four fixed parameters, and its `depth`
    must match the rail's. The full dimensioned specification, with the
    working, is `rail15_spec.html`.

    The rail has no tolerance, so the fit is all here: the slot is the rail
    grown by `clearance`, normal to every flat face. At the floor the radius
    is `tip_radius` + `clearance`, concentric with the rail's. The slot's
    widest point is therefore 15 + 2 x `clearance`.

    **The mouth's lip is sharp at the default clearance.** Its radius is
    `root_radius` - `clearance`, concentric with the rail's root radius,
    which is 0 at a clearance of 0.20 and can't be less. So from 0.20 up the
    lip is a sharp corner, chosen when the part is built; below that it's
    rounded. Either way the gap stays `clearance`: rebuild after moving the
    clearance across 0.20.

    **The frame is the rail's, not the block's:** the housing is centred on
    y = 0 and runs along x from 0 to `length`, with the rail's root at z =
    0, so its mating face is at z = -`clearance` and its floor at z =
    -`depth` - `clearance`. A `rail15` built at the same origin sits in it,
    mated, whatever the clearance.

    `end_taper` is an option, 0 (off) by default: lead-ins at both ends of
    the slot. Over the last `end_taper` of its length the slot grows by
    `end_taper`, normal to its faces, so at 45 degrees along x; the mating
    face stays where it is. Between the lead-ins the profile is exact, and
    that's where to measure the mouth. The choice of on or off is fixed when
    the part is built: rebuild after changing it.

    `printer_width_offset` is added to the slot's width, half to each side,
    across y only, and is the housing's own value: a printer needn't move a
    slot as it moves a rail. The block's outside doesn't change. With
    different offsets the two models don't show the printed gap, and may
    overlap as models.

    For an assembly, `body()` returns the block and, as a cut tool, the
    slot, reaching 1 above the face and past both ends.
    """

    title = "15 mm rail housing"
    params, groups = grouped(("Variable", HOUSING))
    fixed = FIXED
    derived = SHAPE + (
        ("grow", "clearance / tan(angle / 2)", "how far clearance moves the sharp corners"),
        ("floor_hw", "tip_hw + grow", "slot floor half-width, sharp"),
        ("mouth_hw", "root_hw + grow", "slot mouth half-width, sharp"),
        ("lip_end", "mouth_hw + t_root + 3", "past the lip, over the mating face"),
    )
    derived_on_page = False
    checks = SHAPE_CHECKS + TAPER_CHECKS + (
        ("clearance", "clearance must be positive"),
        ("block_depth - depth - end_taper", "block_depth leaves no floor under the lead-ins"),
        ("depth / sin(angle) - t_tip - t_root", "depth is too small: the flanks are too "
                                                "short for their radii"),
        ("block_width / 2 - floor_hw - end_taper / tan(angle / 2) - printer_width_offset / 2",
         "block_width leaves no wall beside the slot"),
        ("block_depth - depth", "block_depth leaves no floor under the slot"),
    )
    fits = (("rail15", "a rail slid in, built at the same origin"),)
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
            return [(left(floor_y), floor_z, floor_r), (right(floor_y), floor_z, floor_r),
                    (right(mouth_y), "-clearance") + lip,
                    (right("lip_end"), "-clearance"), (right("lip_end"), f"-clearance + {REACH}"),
                    (left("lip_end"), f"-clearance + {REACH}"), (left("lip_end"), "-clearance"),
                    (left(mouth_y), "-clearance") + lip]

        slot = b.choose(
            "end_taper > 0",
            lambda: b.loft("slot", along(
                points, (f"end_taper + {PAST}", f"-{PAST}"), ("0", "end_taper"),
                ("0", "length - end_taper"), (f"end_taper + {PAST}", f"length + {PAST}")), "yz"),
            lambda: b.prism("slot", points("0"), "yz", (f"-({REACH})", f"length + {REACH}")))
        return None if slot is None else (block, [slot])
