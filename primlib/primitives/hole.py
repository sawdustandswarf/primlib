"""HOLE -- screw hole cutting tool: plain, countersunk or counterbored."""

from primlib.core import Param, Revolved


class Hole(Revolved):
    """**Deprecated: part of the old ring hinge (`hinge_deprecated`), used only
    by `latch`.** Don't use it for new work; it goes when the latch moves to
    `hinge`.

    The cutting tool for one screw hole through a plate `thickness`
    thick, axis on z, plate bottom at z = 0 and the screw head at the top.
    `hole_type` picks the shape: 0 none, 1 plain, 2 countersunk, 3
    counterbored. It is an ordinary spreadsheet cell -- change it and
    recompute; the profile keeps the same four wall points for every type
    and only their positions change.

    Every face is grown by `tolerance` along its own normal: the shank
    radius by `tolerance`, the countersink cone so its flank stands
    `tolerance` off the head's (radius + tolerance / sin of the flank
    angle), the counterbore radius by `tolerance` and its floor
    `tolerance` deeper than `head_height`. The tool overshoots both plate
    faces by `over` so the cut is clean. Type 0 builds the plain shape; a
    plate moves its holes clear of the material instead.
    """

    title = "Screw hole"
    params = (
        Param("hole_type", "2",
              "0 none, 1 plain, 2 countersunk, 3 counterbored"),
        Param("thickness", "5", "plate thickness"),
        Param("screw_diam", "3", "screw shank diameter"),
        Param("head_diam", "6", "screw head diameter"),
        Param("head_angle", "90 deg", "countersink included angle"),
        Param("head_height", "3", "counterbore depth (screw head height)"),
        Param("tolerance", "0.1", "clearance, normal to every face"),
    )
    derived = (
        ("over", "0.5", "overshoot past each plate face"),
        ("r_s", "screw_diam / 2 + tolerance", "shank hole radius"),
        ("alpha", "90 deg - head_angle / 2", "countersink flank to the face"),
        ("cs_r", "head_diam / 2 + tolerance / sin(alpha)",
         "countersink radius at the top face"),
        ("cs_depth", "(cs_r - r_s) * tan(alpha)", "countersink depth"),
        ("cb_r", "head_diam / 2 + tolerance", "counterbore radius"),
        ("cb_depth", "head_height + tolerance", "counterbore depth"),
        ("r_b", "hole_type == 2 ? cs_r : (hole_type == 3 ? cb_r : r_s)",
         "radius at the top face"),
        ("z_a", "hole_type == 2 ? thickness - cs_depth : "
                "(hole_type == 3 ? thickness - cb_depth : thickness / 3)",
         "top of the shank"),
        ("z_b", "hole_type == 2 ? thickness : "
                "(hole_type == 3 ? thickness - cb_depth : 2 * thickness / 3)",
         "bottom of the full-width part"),
    )
    checks = (
        ("hole_type < 0 ? 0 : (hole_type > 3 ? 0 : 1)",
         "hole_type must be 0, 1, 2 or 3"),
        ("thickness", "thickness must be positive"),
        ("screw_diam", "screw_diam must be positive"),
        ("head_diam - screw_diam", "head_diam must exceed screw_diam"),
        ("hole_type == 2 ? thickness - cs_depth : 1",
         "the countersink is deeper than the plate"),
        ("hole_type == 3 ? thickness - cb_depth : 1",
         "the counterbore is deeper than the plate"),
    )
    variants = (
        ("plain", {"hole_type": "1"}),
        ("countersunk", {"hole_type": "2"}),
        ("counterbored", {"hole_type": "3"}),
    )

    @staticmethod
    def walls(x):
        outer = [
            (x.r_s, f"-{x.over}"),                   # shank, below the plate
            (x.r_s, x.z_a),                          # top of the shank
            (x.r_b, x.z_b),                          # head: cone or step
            (x.r_b, f"{x.thickness} + {x.over}"),    # above the plate
        ]
        return outer, None
