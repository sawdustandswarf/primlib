"""HINGED_LID -- a small example of an assembly: two runs of box edge, one
on a hinge's lid side that turns with it, the other with the hinge's base
side and pins."""

from primlib.recipe import Assembly, Param, Part


class HingedLid(Assembly):
    """Two edge runs (the `edge_run` recipe, keyed) along x, `width` apart in
    y, the hinge between them along x: side A's leaf goes with the lid run,
    side B's and the pins with the base run. The lid side turns by
    `open_angle` about the hinge's axis. An example of what assemblies hold:
    a recipe as a part, a compound taken in pieces, a joint, the print list."""

    title = "Hinged lid (example)"
    params = (
        Param("run", "120", "each edge run's length"),
        Param("key", "'SFS", "the runs' key"),
        Param("hinge_length", "40", "the hinge's length, along x"),
        Param("width", "60", "between the runs' axes"),
        Param("open_angle", "0", "how far the lid side is open, degrees"),
    )
    derived = (("hinge_x", "(run - hinge_length) / 2", "the hinge's start, centred on the runs"),)
    checks = (("run - hinge_length", "the hinge is longer than the runs"),)
    parts = (
        Part("edges", "edge_run", {"run": "run", "key": "key"}, to_print=True),
        Part("lid_leaf", "hinge", {"length": "hinge_length", "rings": "4"}, pieces=("side_a",),
             colour=(0.93, 0.66, 0.18), to_print=True),
        Part("base_leaf", "hinge", {"length": "hinge_length", "rings": "4"}, pieces=("side_b", "pins"),
             colour=(0.10, 0.62, 0.62)),
    )

    @classmethod
    def place(cls, r):
        along_x = [("y", "90")]          # the run's z, and the hinge's axis, along x
        # The hinge's axis along x, side A's leaf (its +x) along +y to the lid, its faces (+y) up.
        hinge = [("y", "90"), ("x", "90")]
        base = r.instance("base_run", "edges", at=("0", "-width / 2", "0"), turn=along_x)
        hinge_base = r.instance("hinge_base", "base_leaf", at=("hinge_x", "0", "0"), turn=hinge)
        lid = r.group("lid", [r.instance("lid_run", "edges", at=("0", "width / 2", "0"), turn=along_x),
                              r.instance("hinge_lid", "lid_leaf", at=("hinge_x", "0", "0"), turn=hinge)])
        return r.group("all", [base, hinge_base, r.joint("open", lid, ("0", "0", "0"), "x", "open_angle")])
