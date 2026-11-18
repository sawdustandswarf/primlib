"""SLEEVE_CLEARANCE -- the space a sleeve needs: its outside, grown, solid."""

from primlib.core import Mate, Param
from primlib.primitives.sleeve import Sleeve


class SleeveClearance(Sleeve):
    """**Deprecated: part of the old ring hinge (`hinge_deprecated`), used only
    by `latch`.** Don't use it for new work; it goes when the latch moves to
    `hinge`.

    The clearance envelope of a sleeve, used as a cutting tool to make
    the pocket a sleeve turns in. Only the sleeve's outside counts: the
    outer wall and the 45-degree W flanks are each offset by `clearance`
    along their own normal, and the inside -- bore and pin -- is filled
    solid to the axis.

    The flanks meet the offset ends in sharp corners (as the pin's clearance
    envelope does), so the gap is `clearance` normal to every face. The
    ends are flat, `clearance` beyond the sleeve's ridge rings; a stack of
    these overlaps its neighbours there, which is harmless for a pocket
    cut. Takes every sleeve parameter, so it stays in step with the sleeve
    it clears.
    """

    title = "Sleeve clearance"
    params = Sleeve.params + (
        Param("clearance", "0.2", "gap around the sleeve, normal to every face"),
    )
    derived = Sleeve.derived + (
        ("corner", "clearance * tan(22.5 deg)",
         "shift of each 45-degree flank corner"),
    )
    mates = (
        Mate("sleeve", {p.name: p.name for p in Sleeve.params},
             "the sleeve this envelope clears",
             details=((0, "bottom ridge ring"),
                      (1, "flank meets the outer wall")),
             fit="inside"),
    )

    @staticmethod
    def walls(x):
        c, k = x.clearance, x.corner
        outer = [
            (f"{x.ridge_r} + {k}", f"{x.bottom} - {c}"),             # bottom end, flank
            (f"{x.outer_r} + {c}", f"{x.bottom} + {x.rim_h} - {k}"),  # flank -> wall
            (f"{x.outer_r} + {c}", f"{x.top} - {x.rim_h} + {k}"),     # wall -> flank
            (f"{x.ridge_r} + {k}", f"{x.top} + {c}"),                # top end, flank
        ]
        return outer, None
