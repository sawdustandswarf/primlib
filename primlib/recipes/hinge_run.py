"""HINGE_RUN -- a row of hinges by key, as the hybrid case hangs its lid: fixed
lengths S, M and L, a little corner hinge T, and fit hinges F sharing what's
left; each hinge's lid half on a joint of its own."""

from primlib.recipe import Param, Part, Recipe

LETTERS = "SMLFT"
SIZED = {"S": "small", "M": "medium", "L": "large", "T": "little"}
# The hinge's frame (axis along z, side A's leaf +x, mounting faces +y) to the row's:
# the axis along +x, side A (the lid's) up, the mounting faces towards -y.
TURN = [("x", "180"), ("y", "-90")]


def fit(key):
    """The fit length for `key`: the run less its gaps (one more than the
    hinges) and fixed hinges, over its F's."""
    fixed = "".join(f" - count({key}; <<{c}>>) * {SIZED[c]}" for c in "SMLT")
    return (f"count({key}; <<F>>) > 0 ? (run - (len({key}) + 1) * gap{fixed}) / count({key}; <<F>>) : 0")


def _hinge(length, little):
    """A hinge's values: its rings at the pitch, at least 2; the T hinge's
    pitch and side plates its own."""
    pitch, (a, b) = ("pitch_little", ("side_a_little", "side_b_little")) if little else ("pitch", ("side", "side"))
    return {"length": length, "rings": f"max(2; floor({length} / {pitch} + 0.5))", "side_a": a, "side_b": b}


class HingeRun(Recipe):
    """A row `run` long of hinges along x, their axis the x axis, filled by
    `key`: a letter per hinge in order, S, M and L the fixed lengths
    `small`, `medium` and `large`, T the little corner hinge (`little`
    long, its own ring pitch and side plates), and F a fit hinge; the fit
    hinges share what's left after the others and a `gap` before, between
    and after them. A key whose fit hinge would be under `min_fit` falls
    back to `fallback`.

    Each hinge is placed in two halves: side B's leaf and the pins, and
    side A's leaf, which turns by `open_angle` about the axis (a joint), so
    a lid on side A opens with it. Side A's leaf stands up (+z), side B's
    hangs down; the mounting faces are towards -y. The rings are the
    length over the pitch, at least 2."""

    title = "Hinge run"
    params = (
        Param("run", "300", "the length of the row"),
        Param("key", "'TFT", "the hinges in order: S, M, L fixed, T the little one, F fit"),
        Param("fallback", "'TFT", "the key used when `key`'s fit hinge is under min_fit"),
        Param("small", "20", "an S hinge's length"),
        Param("medium", "35", "an M hinge's length"),
        Param("large", "50", "an L hinge's length"),
        Param("little", "13", "the T hinge's length"),
        Param("gap", "0.2", "between hinges, and at each end"),
        Param("min_fit", "10", "the shortest fit hinge"),
        Param("pitch", "10", "the ring pitch"),
        Param("pitch_little", "6.5", "the T hinge's ring pitch"),
        Param("side", "18", "each leaf beyond its tab"),
        Param("side_a_little", "18", "the T hinge's side A leaf beyond its tab"),
        Param("side_b_little", "18", "the T hinge's side B leaf beyond its tab"),
        Param("open_angle", "0", "side A's leaves turned about the axis, degrees: up is +"),
    )
    groups = (("Run", ("run", "key", "fallback", "small", "medium", "large", "little", "gap", "min_fit")),
              ("Hinges", ("pitch", "pitch_little", "side", "side_a_little", "side_b_little", "open_angle")))
    derived = (
        ("raw_fit", fit("key"), "the fit length with the key as typed"),
        ("use", "raw_fit < min_fit ? fallback : key", "the key in use: as typed, or the fallback"),
        ("fit_length", fit("use"), "each fit hinge's length"),
        ("fit_hinge", "max(fit_length; 7)", "the fit hinge built: at least 7"),
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
    parts = tuple(
        Part(f"{c}{tail}", "hinge", _hinge("fit_hinge" if c == "F" else SIZED[c], c == "T"), pieces=pieces)
        for c in LETTERS for tail, pieces in (("", ("side_b", "pins")), ("_lid", ("side_a",)))
    )

    @classmethod
    def place(cls, r):
        lengths = {c: "fit_length" if c == "F" else SIZED[c] for c in LETTERS}
        base = r.row("hinge", "use", {c: (c, lengths[c]) for c in LETTERS}, along="x", gap="gap", lead="gap",
                     turn=TURN)
        lid = r.row("lidhinge", "use", {c: (f"{c}_lid", lengths[c]) for c in LETTERS}, along="x", gap="gap",
                    lead="gap", turn=TURN)
        return r.group("row", [base, r.joint("open", lid, ("0", "0", "0"), "x", "open_angle")])
