"""Paths in plain Python: python3 -m unittest discover tests

The dovetail path, base included, must give the outlines the rails and
housings draw today, number for number, at the defaults and with lead-ins and other
clearances: the proof that they can move onto it without a change.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from primlib.core import total  # noqa: E402
from primlib.expr import evaluate, names  # noqa: E402
from primlib.paths import available as paths  # noqa: E402
from primlib.paths.dovetail import Dovetail  # noqa: E402
from primlib.primitives import available  # noqa: E402
from primlib.targets.record import record  # noqa: E402


def sections(tree, name):
    """Every outline the op `name` draws: a prism's, then a loft's
    sections, in the order recorded (choose keeps both branches)."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("name") == name and o.get("op") == "prism":
                found.append(o["points"])
            if o.get("name") == name and o.get("op") == "loft":
                found.extend(s["points"] for s in o["sections"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tree["ops"])
    return found


def numbers(pts, env):
    return [tuple(round(evaluate(c, env), 9) for c in p) for p in pts]


# (key, op name, groove, clearance in the offset, e of each loft section)
CASES = (
    ("rail15", "rail", False, False),
    ("topeak_rail", "rail", True, False),
    ("rail15_housing", "slot", False, True),
    ("topeak_rail_housing", "slot", True, True),
)


class MatchesTheRails(unittest.TestCase):
    def check(self, key, op, groove, housing, values):
        tree = record(available()[key])
        env = names(tree, values)
        et = env["end_taper"]
        past = et + 0.2 if housing else et   # a slot's lead-in carries on past its ends
        found = sections(tree, op)
        self.assertGreaterEqual(len(found), 5)  # a prism and a loft's four sections, or more
        face = "clearance" if housing else "0"
        # The base each primitive closes the dovetail with, as the path's
        # base_width and base_height: a rail's support (drawn 1 wider each
        # side when base_width is -1, then trimmed), a slot's reach to
        # lip_end and 1 above the mating face.
        if housing:
            c = env["clearance"]
            bases = [(2 * (env["lip_end"] - c), 1 - 2 * c)]
        else:
            bases = [(2 * env["base_hw"], env["base_depth"]),
                     (2 * (env["base_hw"] + 1), env["base_depth"])]
        chains = {}
        for e in (0, past):
            g = f"clearance + {e}" if housing else f"-{e}"
            for bw, bh in bases:
                chains[(e, bw)] = numbers(Dovetail.points(g, face, "printer_width_offset / 2",
                                                          groove),
                                          dict(env, base_width=bw, base_height=bh))
        hits = {0: 0, past: 0}
        for pts in found:
            # recorded from the left tip: the left root is the last point
            got = numbers([pts[-1]] + pts[:-1], env)
            with self.subTest(key=key, values=values):
                match = [e for (e, _), chain in chains.items() if chain == got]
                self.assertTrue(match, f"no offset of the dovetail gives {got}")
                hits[match[0]] += 1
        # the prism and the loft's middle sections at 0, the loft's ends at the lead-in
        self.assertGreaterEqual(hits[0], 3)
        if et:
            self.assertGreaterEqual(hits[past], 2)

    def test_defaults(self):
        for case in CASES:
            self.check(*case, {})

    def test_lead_ins_offsets_and_clearances(self):
        for values in ({"end_taper": "0.5"},
                       {"end_taper": "0.3", "printer_width_offset": "0.4"},
                       {"clearance": "0.1"}, {"clearance": "0.35", "end_taper": "0.4"}):
            for key, op, groove, housing in CASES:
                vals = {k: v for k, v in values.items()
                        if k != "clearance" or housing}
                self.check(key, op, groove, housing, vals)


class Offsets(unittest.TestCase):
    ENV = {"width": 15, "angle": 60, "depth": 4, "tip_radius": 1, "root_radius": 0.2,
           "base_width": 15, "base_height": 1}

    def env(self):
        env = dict(self.ENV)
        for name, expr, _ in Dovetail.derived:
            env[name] = evaluate(expr, env)
        return env

    def test_defaults_pass_their_checks(self):
        for key, cls in paths().items():
            d = cls.declare(**{o: True for o in cls.options})
            env = {p.name: float(p.default) for p in d.params}
            for name, expr, _ in d.derived:
                env[name] = evaluate(expr, env)
            for expr, msg in d.checks:
                with self.subTest(path=key, check=msg):
                    self.assertGreater(evaluate(expr, env), 0)

    def test_width_is_what_calipers_read(self):
        env = self.env()
        (_, _, _), (lu, _, r), (ru, _, _), *_ = numbers(Dovetail.points(), env)
        self.assertAlmostEqual(2 * (ru - env["t_tip"] + r), 15)

    def test_grow_keeps_rounds_concentric(self):
        # the tip round's centre doesn't move with grow, nor the root's with
        # grow = face; the radii change by the offset
        env = self.env()
        import math
        a = math.radians(60)

        def centres(g, f):
            (u0, v0, r0), _, (u1, v1, r1), _ = [p for i, p in enumerate(
                numbers(Dovetail.points(str(g), str(f)), env)) if i in (0, 1, 2, 3)]
            # right tip: the centre is r1 up and r1 / tan(a/2) in from the sharp corner
            tip = (u1 - r1 / math.tan(a / 2), v1 + r1)
            # left root (u0 < 0): r0 below the face, inwards by r0 / tan(a/2)
            root = (u0 - r0 / math.tan(a / 2), v0 - r0)
            return tip, root, r1, r0
        t0, s0, rt0, rr0 = centres(0, 0)
        t1, s1, rt1, rr1 = centres(0.15, 0.15)
        for p, q in ((t0, t1), (s0, s1)):
            self.assertAlmostEqual(p[0], q[0])
            self.assertAlmostEqual(p[1], q[1])
        self.assertAlmostEqual(rt1 - rt0, 0.15)
        self.assertAlmostEqual(rr0 - rr1, 0.15)

    def test_face_moves_the_base(self):
        env = self.env()
        pts = numbers(Dovetail.points("0.3", "0.2"), env)
        self.assertEqual(pts[-4], (7.7, -0.2))       # base_width / 2 + face, the root line
        self.assertEqual(pts[-3], (7.7, 1.2))        # base_height + face
        self.assertEqual(pts[-1], (-7.7, -0.2))
        self.assertEqual(pts[0][1], -0.2)            # the root corner on the moved root line

    def test_unknown_option(self):
        with self.assertRaises(ValueError):
            Dovetail.declare(grooves=True)

    def test_total(self):
        self.assertEqual(total("a", ("+", "0", "x")), "a")
        self.assertEqual(total("a", ("+", "-(b + c)", "s")), "a - (b + c) / s")
        self.assertEqual(total("a", ("-", "-b", None)), "a + b")
        self.assertEqual(total("a", ("+", "b / 2", None)), "a + b / 2")


if __name__ == "__main__":
    unittest.main()
