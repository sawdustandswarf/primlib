"""SUPPORT_PAIR -- a half-cylinder support and its mirror image: a whole
round support in two halves that break away apart."""

from primlib.recipe import Param, Part, Recipe

SHARED = ("radius", "height", "line_w", "layer_h", "gap_lines", "interface_gap")


class SupportPair(Recipe):
    """Two half-cylinder supports, the second the first mirrored across the
    xz plane, `split` apart along y: under a round part, each half breaks
    away on its own side."""

    title = "Support pair"
    params = (
        Param("radius", "5", "the supported circle's radius"),
        Param("height", "3", "from the face below to the face it holds up"),
        Param("split", "0.4", "between the halves' flat sides"),
        Param("line_w", "0.44", "the printer's line width"),
        Param("layer_h", "0.2", "the printer's layer height"),
        Param("gap_lines", "4", "lines between the rings"),
        Param("interface_gap", "0.1", "under the supported face"),
    )
    checks = (("split >= 0", "split can't be negative"),)
    parts = (Part("half", "support_half", {n: n for n in SHARED}, colour=(0.10, 0.62, 0.62)),
             Part("mirrored", "support_half", {n: n for n in SHARED}, mirror="y", colour=(0.93, 0.66, 0.18)))

    @classmethod
    def place(cls, r):
        return r.group("pair", [r.instance("a", "half", at=("0", "split / 2", "0")),
                                r.instance("b", "mirrored", at=("0", "-split / 2", "0"))])
