"""SLEEVE -- hollow barrel that rides a retained pin."""

from primlib.core import Mate, Param, Revolved


class Sleeve(Revolved):
    """**Deprecated: part of the old ring hinge (`hinge_deprecated`), used only
    by `latch`.** Don't use it for new work; it goes when the latch moves to
    `hinge`.

    A hollow barrel that wraps a retained pin with a uniform running
    clearance: the bore is the pin's clearance envelope, every pin face
    offset by `tolerance` along its own normal, so the gap measured normal
    to the faces is `tolerance` everywhere -- flanks and shaft alike.

    Bore: the envelope's flank cones, at the pin's flank `angle`, open from
    the ridge ring down into the throat (diam / 2 + tolerance). A pin flare
    cannot pass the throat, which is what retains the sleeve on the pin.

    Outside: a cylinder `diam_outer` whose ends are 45-degree W flanks
    rising from the ridge ring, where the bore flank meets the end face.
    Two stacked sleeves meet only along that ring.

    `end_gap` shortens the sleeve by end_gap / 2 at each end, so sleeves
    stacked on pin segments of the same `height` stand `end_gap` apart at
    their ridge rings (needed for print-in-place). The bore is still the
    pin's envelope, so the ridge ring moves in to where that envelope
    crosses the shortened end face.
    """

    title = "Sleeve"
    params = (
        Param("height", "10", "sleeve height, one pin segment"),
        Param("diam", "6", "pin shaft diameter"),
        Param("diam_end", "10", "pin flare diameter"),
        Param("angle", "45 deg", "pin flare flank angle to the end face"),
        Param("diam_outer", "13", "sleeve outside diameter"),
        Param("tolerance", "0.1", "running clearance, normal to every pin face"),
        Param("end_gap", "0", "gap to the next stacked sleeve (half at each end)"),
    )
    derived = (
        ("outer_r", "diam_outer / 2", "outside radius"),
        ("throat_r", "diam / 2 + tolerance", "bore radius at the waist"),
        ("flare_r", "diam_end / 2 + tolerance / tan(angle / 2)",
         "envelope flare radius (at z = -tolerance)"),
        ("bottom", "end_gap / 2", "lowest point (bottom ridge ring)"),
        ("top", "height - end_gap / 2", "highest point (top ridge ring)"),
        ("ridge_r", "flare_r - (tolerance + bottom) / tan(angle)",
         "ridge ring: envelope flank at the end face"),
        ("valley_z", "(ridge_r - throat_r) * tan(angle)",
         "height of each bore flank cone"),
        ("rim_h", "outer_r - ridge_r", "height of each outer flank"),
    )
    checks = (
        ("diam_end - diam", "diam_end must exceed diam"),
        ("outer_r - ridge_r", "diam_outer leaves no wall around the pin flare"),
        ("end_gap < 0 ? 0 : 1", "end_gap must not be negative"),
        ("valley_z", "end_gap is too large: the end face misses the bore flank"),
        ("top - bottom - 2 * rim_h", "height is too small for the outer flanks"),
        ("top - bottom - 2 * valley_z", "height is too small for the bore flanks"),
    )
    mates = (
        Mate("pin", {"height": "height", "diam": "diam", "diam_end": "diam_end",
                     "angle": "angle"},
             "the retained pin the sleeve rides, one segment long",
             details=((2, "flare cone meets the shaft"),)),
    )

    @staticmethod
    def walls(x):
        outer = [
            (x.ridge_r, x.bottom),                     # bottom ridge
            (x.outer_r, f"{x.bottom} + {x.rim_h}"),    # flank -> outer wall
            (x.outer_r, f"{x.top} - {x.rim_h}"),       # outer wall -> flank
            (x.ridge_r, x.top),                        # top ridge
        ]
        inner = [
            (x.ridge_r, x.bottom),                       # bottom ridge
            (x.throat_r, f"{x.bottom} + {x.valley_z}"),  # bore flank -> throat
            (x.throat_r, f"{x.top} - {x.valley_z}"),     # throat -> bore flank
            (x.ridge_r, x.top),                          # top ridge
        ]
        return outer, inner
