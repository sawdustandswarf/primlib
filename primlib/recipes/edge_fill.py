"""EDGE_FILL -- a length of box edge filled symmetrically, as spacing.py lays
it out: big pieces, little pieces at the ends, and the odd pieces that take
up what's left."""

from primlib.recipe import Param, Part, Recipe

SECTION = ("size", "panel_t", "skin", "panel_gap", "bevel")


class EdgeFill(Recipe):
    """`span` filled along z with box edge pieces and a spacer between
    neighbours (and at both ends, with `end_spacers`): `bigs` pieces
    `target` long, `littles` pieces `little_length` long (half at each
    end), and the odd pieces, which share what's left. An even number of
    bigs has one odd piece, in the middle; an odd number has two, either
    side of the middle big, so the row stays symmetric:

        little  big  big  ODD  big  big  little
        little  big  ODD  big  ODD  big  little

    The same layout as spacing.py's `spacing()`, which is its reference."""

    title = "Edge fill"
    params = (
        Param("span", "300", "the length to fill"),
        Param("target", "50", "a big piece's length"),
        Param("spacer", "10", "between pieces"),
        Param("bigs", "4", "how many big pieces: even gives one odd piece, odd two"),
        Param("littles", "0", "how many little pieces, half at each end: even"),
        Param("little_length", "20", "a little piece's length"),
        Param("end_spacers", "1", "1: a spacer at both ends too; 0: none"),
        Param("min_part", "20", "the shortest odd piece allowed"),
        Param("max_part", "80", "the longest odd piece allowed"),
        Param("size", "27", "the edge's section, each way"),
        Param("panel_t", "6.5", "the panels' thickness"),
        Param("skin", "5", "the wall over the panels"),
        Param("panel_gap", "3", "the web's width"),
        Param("bevel", "15", "the outside bevel's width"),
    )
    groups = (("Layout", ("span", "target", "spacer", "bigs", "littles", "little_length", "end_spacers",
                          "min_part", "max_part")),
              ("Section", SECTION))
    derived = (
        ("odds", "mod(bigs; 2) == 1 ? 2 : 1", "odd pieces: set by the bigs"),
        ("pieces", "bigs + littles + odds", "pieces in all"),
        ("spacers", "pieces - 1 + 2 * end_spacers", "spacers in all"),
        ("odd", "(span - bigs * target - littles * little_length - spacers * spacer) / odds",
         "each odd piece's length"),
        ("key", "repeat(<<L>>; floor(littles / 2)) + repeat(<<B>>; floor(bigs / 2))"
                " + (mod(bigs; 2) == 1 ? <<OBO>> : <<O>>) + repeat(<<B>>; floor(bigs / 2))"
                " + repeat(<<L>>; floor(littles / 2))", "the pieces in order: L little, B big, O odd"),
    )
    slots = 15
    checks = (
        ("mod(littles; 2) == 0", "littles must be even"),
        ("(bigs >= 0) * (floor(bigs) == bigs)", "bigs must be a whole number, 0 or more"),
        ("(littles >= 0) * (floor(littles) == littles)", "littles must be a whole number, 0 or more"),
        ("pieces <= 15", "too many pieces: 15 at most"),
        ("odd >= min_part", "the odd piece is too short: fewer bigs, littles or spacers"),
        ("odd <= max_part", "the odd piece is too long: more bigs or littles"),
    )
    parts = tuple(Part(name, "box_edge", dict({"length": length}, **{n: n for n in SECTION}), colour=colour)
                  for name, length, colour in (("big", "target", (0.93, 0.66, 0.18)),
                                               ("odd", "odd", (0.80, 0.80, 0.78)),
                                               ("little", "little_length", (0.10, 0.62, 0.62))))

    @classmethod
    def place(cls, r):
        return r.row("edge", "key", {"B": ("big", "target"), "O": ("odd", "odd"), "L": ("little", "little_length")},
                     along="z", gap="spacer", lead="end_spacers * spacer")
