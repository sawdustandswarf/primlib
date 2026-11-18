"""DOVETAIL -- the rails' dovetail section, as a path any primitive can draw."""

import re

from primlib.core import Param, Path, total

PROFILE = (
    Param("width", "15", "the outside width, between vertical tangents to the tip radii, "
                         "what calipers read"),
    Param("angle", "60", "the slope of the sides, flank to the tip face, deg"),
    Param("depth", "4", "root to tip, down v: how far the tongue goes into its slot"),
    Param("tip_radius", "1", "the radius of the two tip corners"),
    Param("root_radius", "0.2", "the radius of the two root corners, where the flanks "
                                "turn onto the base"),
    Param("base_width", "15", "the base above the root: its width, centred"),
    Param("base_height", "1", "the base's height, up from the root line"),
)
# Worked in from the width.
SHAPE = (
    ("t_tip", "tip_radius / tan(angle / 2)", "tip radius's tangent length"),
    ("t_root", "root_radius / tan(angle / 2)", "root radius's tangent length, into a "
                                               "base wider than the root"),
    ("tip_hw", "width / 2 + t_tip - tip_radius", "tip half-width, sharp"),
    ("root_hw", "tip_hw - depth / tan(angle)", "root half-width, sharp"),
    ("width_check", "2 * (tip_hw - t_tip + tip_radius)", "the width, worked back from "
                                                         "the sharp corners"),
)
CHECKS = (
    ("angle", "angle must be more than 0"),
    ("90 - angle", "angle must be less than 90"),
    ("tip_radius >= 0 ? 1 : 0", "tip_radius can't be negative"),
    ("root_radius >= 0 ? 1 : 0", "root_radius can't be negative"),
    ("0.000001 - abs(width_check - width)", "the tip radii don't come to the width"),
    ("root_hw", "depth leaves no root"),
    ("depth / sin(angle) - t_tip - t_root", "depth is too small: the flanks are too "
                                            "short for their radii"),
    ("base_width / 2 - root_hw - t_root", "base_width is narrower than the root and its "
                                          "radius"),
    ("base_height", "base_height must be more than 0"),
)
GROOVE = (
    Param("groove_width", "6", "the width of the centre groove at the tip face"),
    Param("groove_depth", "0.6", "the depth of the centre groove, up from the tip face"),
    Param("groove_angle", "45", "the slope of the groove's sides to the tip face, deg"),
)
GROOVE_CHECKS = (
    ("groove_depth", "groove_depth must be more than 0"),
    ("depth - groove_depth", "the groove is deeper than the dovetail"),
    ("groove_angle", "groove_angle must be more than 0"),
    ("90 - groove_angle >= 0 ? 1 : 0", "groove_angle can't be more than 90"),
    ("groove_width / 2 - groove_depth / tan(groove_angle)",
     "the groove's sides meet before its top (groove_width or groove_depth)"),
    ("tip_hw - t_tip - groove_width / 2", "the groove and the tip radii leave no tip "
                                          "face between them"),
)


def _neg(expr):
    return f"-{expr}" if re.fullmatch(r"[A-Za-z_]\w*", expr) else f"-({expr})"


def groove_points(g):
    """The groove's four corners, (u, v) from the left, its faces moved
    `g` normal to themselves away from the dovetail (into the groove):
    the same offset as the rest of the outline."""
    foot_u = total("groove_width / 2", ("+", g, "tan(groove_angle)"),
                   ("-", g, "sin(groove_angle)"))
    top_u = total("groove_width / 2 - groove_depth / tan(groove_angle)",
                  ("+", g, "tan(groove_angle)"), ("-", g, "sin(groove_angle)"))
    foot_v, top_v = total("-depth", ("-", g, None)), total("-depth + groove_depth", ("-", g, None))
    return [(_neg(foot_u), foot_v), (_neg(top_u), top_v), (top_u, top_v), (foot_u, foot_v)]


class Dovetail(Path):
    """The dovetail section of the rails and their housings: a tongue
    `depth` deep whose flanks lean out at `angle` to its tip face, so it
    is wider at the tip than at the root and can't pull out of its slot.
    It is `width` across where calipers read it (between vertical
    tangents to the tip radii), and everything else is worked from that.
    The tip corners are rounded `tip_radius`, the root corners
    `root_radius`.

    **Frame** (`docs/GLOSSARY.md`): u across, centred on u = 0, sizes
    along it widths; v up, sizes along it heights. The root line is v = 0,
    the base above it and the tongue below, its tip at v = -`depth` (a
    rail hangs down from its support; `depth` is how far the tongue goes
    into its slot). A primitive maps (u, v) to its own plane: a rail's (y, z),
    or (r, z) about an axis for a revolved dovetail.

    **The outline is closed** by a base: a rectangle `base_width` across
    and `base_height` high, standing on the root line (a rail's support,
    or the part of an object the tongue joins). It runs from the left
    root corner down the left flank, across the tip face, up the right
    flank to the right root corner, then round the base: anticlockwise,
    the tongue on its left. The root corners are rounded `root_radius`
    where the flanks turn onto the base's underside, so the base must be
    wider than the root and its rounds.

    **One offset gives every mate.** `points(grow, face)` moves the flanks
    and the tip face `grow` normal to themselves (outwards when positive),
    and the base's faces `face` (its underside, the root line, down; its
    sides out; its top up), keeping the rounds concentric: the tip radius
    becomes `tip_radius` + `grow`, the root radius `root_radius` - `face`.
    A round of 0 or less is a sharp corner. So:

    - the tongue itself: `grow` 0, `face` 0;
    - its slot, the tongue grown by a clearance `c` normal to every face,
      base and all: `grow` = `face` = c (the mating face moves down by c);
    - a lead-in, the dovetail shrunk by `e` while its base stays:
      `grow` = -e, `face` 0; a slot's lead-in, c + e and c.

    `widen` is added to every u but the groove's, half to each side: a
    printer's width offset.

    **Option `groove`:** a centre groove in the tip face, `groove_width`
    at the tip face, `groove_depth` deep, its sides at `groove_angle`. It
    takes the same offset (a slot's guide is the groove shrunk by c).
    """

    title = "Dovetail"
    params = PROFILE
    derived = SHAPE
    checks = CHECKS
    options = {"groove": (GROOVE, (), GROOVE_CHECKS)}

    @classmethod
    def points(cls, grow="0", face=None, widen="0", groove=False):
        """The closed outline, from the left root corner anticlockwise:
        (u, v, radius) at the dovetail's four rounded corners, (u, v) at
        the sharp ones: the groove's and the base's."""
        g = str(grow)
        f = g if face is None else str(face)
        tip_u = total("tip_hw", ("+", g, "tan(angle / 2)"), ("+", widen, None))
        root_u = total("root_hw", ("+", g, "sin(angle)"), ("+", f, "tan(angle)"),
                       ("+", widen, None))
        tip_v, root_v = total("-depth", ("-", g, None)), "0" if f == "0" else _neg(f)
        base_u = total("base_width / 2", ("+", f, None), ("+", widen, None))
        top_v = total("base_height", ("+", f, None))
        tip_r = total("tip_radius", ("+", g, None))
        middle = groove_points(g) if groove else []
        root_r = total("root_radius", ("-", f, None))
        return ([(_neg(root_u), root_v, root_r), (_neg(tip_u), tip_v, tip_r)] + middle
                + [(tip_u, tip_v, tip_r), (root_u, root_v, root_r),
                   (base_u, root_v), (base_u, top_v), (_neg(base_u), top_v),
                   (_neg(base_u), root_v)])
