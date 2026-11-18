"""PIN -- retained pin: a shaft with a conical flare at both ends."""

from primlib.core import Param, Revolved


class Pin(Revolved):
    """**Deprecated: part of the old ring hinge (`hinge_deprecated`), used only
    by `latch`.** Don't use it for new work; it goes when the latch moves to
    `hinge`.

    A straight shaft of diameter `diam` capped at each end by a conical
    flare that opens out to `diam_end`, the flanks at `angle` to the end
    faces. A sleeve snapped over the shaft is trapped between the flares.

    `clearance` grows every face along its own outward normal, giving the
    envelope the pin must clear in a bore. The grown flares keep the flank
    angle, so the flare diameter grows by 2c / tan(angle / 2), and the
    envelope stays centred on the nominal pin: it spans z = -c .. height + c.
    """

    title = "Retained pin"
    params = (
        Param("height", "10", "overall height, end face to end face"),
        Param("diam", "6", "shaft diameter"),
        Param("diam_end", "10", "flare diameter at each end face"),
        Param("angle", "45 deg", "flare flank angle to the end face"),
        Param("clearance", "0", "growth normal to every face"),
    )
    derived = (
        ("shaft_r", "diam / 2 + clearance", "shaft radius, grown"),
        ("flare_r", "diam_end / 2 + clearance / tan(angle / 2)",
         "flare radius, grown"),
        ("cone", "(flare_r - shaft_r) * tan(angle)", "flare height"),
        ("bottom", "-clearance", "lowest face"),
        ("top", "height + clearance", "highest face"),
    )
    checks = (
        ("diam", "diam must be positive"),
        ("diam_end - diam", "diam_end must exceed diam"),
        ("top - bottom - 2 * cone", "height is too small for the flares"),
    )

    @staticmethod
    def walls(x):
        outer = [
            (x.flare_r, x.bottom),                  # bottom flare rim
            (x.shaft_r, f"{x.bottom} + {x.cone}"),  # flank -> shaft
            (x.shaft_r, f"{x.top} - {x.cone}"),     # shaft -> flank
            (x.flare_r, x.top),                     # top flare rim
        ]
        return outer, None
