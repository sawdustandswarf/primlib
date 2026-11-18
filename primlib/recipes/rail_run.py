"""RAIL_RUN -- a run of Topeak rail sections by key, as the hybrid case lays
its rail between the end pieces: fixed lengths S, M and L, and fit pieces F
sharing what's left."""

from primlib.recipe import Param, Part, Recipe

RAIL = ("base_depth", "printer_width_offset")
SCREWS = ("screws", "screw_y", "drill_inset", "nominal_spacing", "min_spacing", "screw_r", "head_r", "head_h")
LETTERS = "SMLF"


def fit(key):
    """The fit length for `key`: the run less its gaps (one more than the
    pieces: the end pieces' at both ends) and fixed pieces, over its F's."""
    return (f"count({key}; <<F>>) > 0 ? (run - (len({key}) + 1) * gap - count({key}; <<S>>) * small"
            f" - count({key}; <<M>>) * medium - count({key}; <<L>>) * large) / count({key}; <<F>>) : 0")


class RailRun(Recipe):
    """A run `run` long of topeak_rail sections along x, filled by `key`: a
    letter per section in order, S, M and L the fixed lengths `small`,
    `medium` and `large`, and F a fit section; the fit sections share
    what's left after the fixed ones and a `gap` before, between and after
    them. A key whose fit section would be under `min_fit` falls back to
    `fallback` (F: one fit section). The sections are topeak_rail's at
    `base_depth`, its support as wide as the root, no lead-ins, with their
    screw rows."""

    title = "Rail run"
    params = (
        Param("run", "300", "the length between the end pieces"),
        Param("key", "'F", "the sections in order: S, M, L fixed, F fit"),
        Param("fallback", "'F", "the key used when `key`'s fit section is under min_fit"),
        Param("small", "20", "an S section's length"),
        Param("medium", "35", "an M section's length"),
        Param("large", "50", "an L section's length"),
        Param("gap", "0.2", "between sections, and at each end"),
        Param("min_fit", "10", "the shortest fit section"),
        Param("base_depth", "2", "the support on the root, up from it"),
        Param("printer_width_offset", "0.2", "topeak_rail's: added to its width in the model"),
        Param("screws", "1", "1 for two rows of screws up through each section; 0 none"),
        Param("screw_y", "18.4", "each row's line off the centre line"),
        Param("drill_inset", "6", "the rows' first and last holes from the ends"),
        Param("nominal_spacing", "30", "the longest pitch along a row"),
        Param("min_spacing", "7", "under this between the end holes, a single middle hole"),
        Param("screw_r", "1.4", "the screw hole"),
        Param("head_r", "2.75", "the countersink at the tip face"),
        Param("head_h", "2.7", "the countersink's depth"),
    )
    groups = (("Run", ("run", "key", "fallback", "small", "medium", "large", "gap", "min_fit")),
              ("Rail", RAIL), ("Screws", SCREWS))
    derived = (
        ("raw_fit", fit("key"), "the fit length with the key as typed"),
        ("use", "raw_fit < min_fit ? fallback : key", "the key in use: as typed, or the fallback"),
        ("fit_length", fit("use"), "each fit section's length"),
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
    parts = tuple(Part(name, "topeak_rail", dict({"length": length, "base_width": "-1", "end_taper": "0"},
                                                 **{n: n for n in RAIL + SCREWS}), colour=colour)
                  for name, length, colour in (("S", "small", (0.10, 0.62, 0.62)),
                                               ("M", "medium", (0.93, 0.66, 0.18)),
                                               ("L", "large", (0.78, 0.30, 0.42)),
                                               ("F", "fit_length", (0.80, 0.80, 0.78))))

    @classmethod
    def place(cls, r):
        return r.row("rail", "use", {c: (c, {"S": "small", "M": "medium", "L": "large", "F": "fit_length"}[c])
                                     for c in LETTERS}, along="x", gap="gap", lead="gap")
