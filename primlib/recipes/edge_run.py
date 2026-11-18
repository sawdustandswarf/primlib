"""EDGE_RUN -- a run of box edge pieces by key, as the hybrid case lays its
edges: fixed lengths S, M and L, and fit pieces F sharing what's left."""

from primlib.recipe import Param, Part, Recipe

SECTION = ("size", "panel_t", "skin", "panel_gap", "bevel", "chamfer", "glue", "glue_ridge")
SCREWS = ("drill_inset", "nominal_spacing", "min_spacing", "screw_r", "head_r", "head_h", "screw_len")
LETTERS = "SMLF"


def fit(key):
    """The fit length for `key`: the run less its gaps (between the pieces,
    and `lead_gap` and `end_gap` at the ends) and fixed pieces, over its F's."""
    return (f"count({key}; <<F>>) > 0 ? (run - (len({key}) - 1 + lead_gap + end_gap) * gap"
            f" - count({key}; <<S>>) * small"
            f" - count({key}; <<M>>) * medium - count({key}; <<L>>) * large) / count({key}; <<F>>) : 0")


class EdgeRun(Recipe):
    """A run `run` long between two corners, along z, filled by `key`:
    a letter per piece in order, S, M and L the fixed lengths `small`,
    `medium` and `large`, and F a fit piece; the fit pieces share what's
    left after the fixed pieces and a `gap` before, between and after the
    pieces. A key whose fit piece would be under `min_fit` falls back to
    `fallback` (F: one fit piece), so a shorter run still lays out.

    `lead_gap` and `end_gap` (1 or 0) say whether there is a gap before the
    first piece and after the last: none where a run ends flush, as the
    hybrid case's Z edges do at the lid's split. The section and screws are
    box_edge's, passed through."""

    title = "Edge run"
    params = (
        Param("run", "300", "the length between the corners"),
        Param("key", "'SFMF", "the pieces in order: S, M, L fixed, F fit"),
        Param("fallback", "'F", "the key used when `key`'s fit piece is under min_fit"),
        Param("small", "30", "an S piece's length"),
        Param("medium", "60", "an M piece's length"),
        Param("large", "90", "an L piece's length"),
        Param("gap", "0.2", "between pieces, and between a piece and a corner"),
        Param("min_fit", "10", "the shortest fit piece"),
        Param("lead_gap", "1", "1: a gap before the first piece (at a corner); 0: flush"),
        Param("end_gap", "1", "1: a gap after the last piece (at a corner); 0: flush"),
        Param("size", "27", "the edge's section, each way"),
        Param("panel_t", "6.5", "the panels' thickness"),
        Param("skin", "5", "the wall over the panels"),
        Param("panel_gap", "3", "the web's width"),
        Param("bevel", "15", "the outside bevel's width"),
        Param("chamfer", "0.5", "on the outward square edges"),
        Param("glue", "0", "the glue line's pockets behind the ridges; 0 for none"),
        Param("glue_ridge", "0.6", "the ridges the panels sit on"),
        Param("drill_inset", "6", "the screw rows from the inside corner, past the web"),
        Param("nominal_spacing", "30", "the longest pitch along a screw row"),
        Param("min_spacing", "7", "under this between the end holes, one middle hole"),
        Param("screw_r", "1.4", "the screw hole"),
        Param("head_r", "2.75", "the countersink at the outside face"),
        Param("head_h", "2.7", "the countersink's depth"),
        Param("screw_len", "20", "the hole's length from the outside face"),
    )
    groups = (("Run", ("run", "key", "fallback", "small", "medium", "large", "gap", "min_fit", "lead_gap",
                       "end_gap")),
              ("Section", SECTION), ("Screws", SCREWS))
    derived = (
        ("raw_fit", fit("key"), "the fit length with the key as typed"),
        ("use", "raw_fit < min_fit ? fallback : key", "the key in use: as typed, or the fallback"),
        ("fit_length", fit("use"), "each fit piece's length"),
    )
    slots = 7
    checks = tuple(
        (f"len({k}) <= 7", f"{k} is longer than 7 letters") for k in ("key", "fallback")
    ) + tuple(
        (" + ".join(f"count({k}; <<{c}>>)" for c in LETTERS) + f" == len({k})",
         f"{k} has a letter other than {' '.join(LETTERS)}") for k in ("key", "fallback")
    ) + (
        ("count(fallback; <<F>>)", "fallback needs an F"),
        ("fit_length >= min_fit", "the run is too short, even with the fallback key"),
    )
    parts = tuple(Part(name, "box_edge", dict({"length": length}, **{n: n for n in SECTION + SCREWS}),
                       colour=colour)
                  for name, length, colour in (("S", "small", (0.10, 0.62, 0.62)),
                                               ("M", "medium", (0.93, 0.66, 0.18)),
                                               ("L", "large", (0.78, 0.30, 0.42)),
                                               ("F", "fit_length", (0.80, 0.80, 0.78))))

    @classmethod
    def place(cls, r):
        return r.row("edge", "use", {c: (c, {"S": "small", "M": "medium", "L": "large", "F": "fit_length"}[c])
                                     for c in LETTERS}, along="z", gap="gap", lead="lead_gap * gap")
