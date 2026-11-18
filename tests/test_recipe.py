"""Recipes in plain Python (primlib/recipe.py): python3 -m unittest discover tests"""

import itertools
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from primlib.prim import PrimError, dumps, export, loads  # noqa: E402
from primlib.recipe import RecipeError, layout, leaf_parts, part_values, recipe_checks, turn_matrix  # noqa: E402
from primlib.assemblies import available as assemblies  # noqa: E402
from primlib.recipes import available  # noqa: E402
from primlib.spacing import spacing  # noqa: E402


def close(a, b):
    return abs(a - b) < 1e-9


class EdgeFill(unittest.TestCase):
    """spacing() is the reference: the same pieces, starts and lengths."""

    def test_as_spacing_lays_it_out(self):
        doc = export("edge_fill")
        n = 0
        for span, bigs, littles, end_spacers in itertools.product((200, 300, 517.5), range(0, 8), (0, 2, 4), (0, 1)):
            values = {"span": str(span), "bigs": str(bigs), "littles": str(littles), "end_spacers": str(end_spacers),
                      "min_part": "-1000", "max_part": "1000"}
            want = spacing(span, 50, 10, bigs, littles, 20, end_spacers)
            if len(want) > 15 or recipe_checks(doc, values):
                continue  # too many, or an odd piece too short for a box edge
            got = layout(doc, values)
            lengths = {k: float(v["length"]) for k, v in part_values(doc, values).items()}
            kinds = {"B": "big", "O": "odd", "L": "little"}
            with self.subTest(values=values):
                self.assertEqual([kinds[p.name[-1]] for p in got], [k for k, _, _ in want])
                for p, (kind, start, length) in zip(got, want):
                    self.assertEqual(p.part, kind)
                    self.assertTrue(close(p.at[2], start), (p.at, start))
                    self.assertTrue(close(lengths[p.part], length), (lengths[p.part], length))
            n += 1
        self.assertGreater(n, 80)

    def test_checks(self):
        doc = export("edge_fill")
        self.assertEqual(recipe_checks(doc), [])
        self.assertIn("littles must be even", recipe_checks(doc, {"littles": "1"}))
        self.assertIn("the odd piece is too short: fewer bigs, littles or spacers",
                      recipe_checks(doc, {"bigs": "5"}))
        with self.assertRaises(RecipeError):
            layout(doc, {"bigs": "5"})


class EdgeRun(unittest.TestCase):
    def test_key_and_fit(self):
        doc = export("edge_run")
        got = layout(doc)
        self.assertEqual([p.name for p in got], ["edge_1S", "edge_2F", "edge_3M", "edge_4F"])
        fit = (300 - 5 * 0.2 - 30 - 60) / 2
        self.assertTrue(close(float(part_values(doc)["F"]["length"]), fit))
        starts = [0.2, 0.2 + 30 + 0.2, 0.2 + 30 + 0.2 + fit + 0.2, 0.2 + 30 + 0.2 + fit + 0.2 + 60 + 0.2]
        for p, s in zip(got, starts):
            self.assertTrue(close(p.at[2], s), (p.name, p.at, s))

    def test_falls_back(self):
        doc = export("edge_run")
        got = layout(doc, {"run": "100"})       # SFMF's fit would be negative
        self.assertEqual([p.name for p in got], ["edge_1F"])
        self.assertTrue(close(float(part_values(doc, {"run": "100"})["F"]["length"]), 100 - 0.4))

    def test_bad_keys(self):
        doc = export("edge_run")
        self.assertIn("key has a letter other than S M L F", recipe_checks(doc, {"key": "'SXF"}))
        self.assertIn("key is longer than 7 letters", recipe_checks(doc, {"key": "'FFFFFFFF"}))
        self.assertIn("fallback needs an F", recipe_checks(doc, {"fallback": "'S"}))


class SupportPair(unittest.TestCase):
    def test_pair(self):
        doc = export("support_pair")
        got = layout(doc, {"split": "1"})
        self.assertEqual([(p.part, p.at) for p in got], [("half", (0, 0.5, 0)), ("mirrored", (0, -0.5, 0))])
        self.assertEqual([p["mirror"] for p in doc["parts"]], [None, "y"])


class Placements(unittest.TestCase):
    """series, choose, move and turns, on a recipe written by hand."""

    DOC = {
        "format": "primlib.prim", "version": 2, "kind": "recipe", "primitive": "t", "title": "",
        "params": [{"name": "n", "default": "3", "note": "", "group": None},
                   {"name": "on", "default": "1", "note": "", "group": None}],
        "fixed": [], "derived": [], "checks": [], "slots": 8,
        "parts": [{"name": "p", "primitive": "pin", "bind": {}, "mirror": None, "colour": None}],
        "place": [
            {"id": 0, "op": "instance", "name": "one", "part": "p", "at": ["10 * i", "0", "0"],
             "turn": [{"axis": "z", "angle": "90"}]},
            {"id": 1, "op": "series", "name": "row", "count": "n", "index": "i", "item": 0},
            {"id": 2, "op": "choose", "name": None, "guard": "on", "then": 1, "otherwise": None},
            {"id": 3, "op": "move", "name": "moved", "base": 2, "by": ["0", "0", "5"],
             "turn": [{"axis": "x", "angle": "180"}]},
        ],
        "result": 3, "uses": {}, "motion": [],
    }

    def setUp(self):
        self.doc = json.loads(json.dumps(self.DOC))
        self.doc["uses"]["pin"] = export("pin")

    def test_series_choose_move(self):
        got = layout(self.doc)
        self.assertEqual([p.at for p in got], [(0, 0, 5), (10, 0, 5), (20, 0, 5)])
        # Turned a quarter about z, then half about x: x -> y -> -y.
        self.assertEqual(got[0].rotation, ((0, -1, 0), (-1, 0, 0), (0, 0, -1)))
        self.assertEqual(layout(self.doc, {"on": "0"}), [])
        self.assertEqual(len(layout(self.doc, {"n": "2.9"})), 2)

    def test_quarter_turns_exact(self):
        self.assertEqual(turn_matrix("z", 90), ((0, -1, 0), (1, 0, 0), (0, 0, 1)))
        self.assertEqual(turn_matrix("y", -90), ((0, 0, -1), (0, 1, 0), (1, 0, 0)))


class HingedLid(unittest.TestCase):
    """An assembly: a recipe as a part (named outer/inner), pieces of a
    compound, the print list, and a joint."""

    def setUp(self):
        self.doc = export("hinged_lid")

    def test_flattened(self):
        got = layout(self.doc)
        names = [p.name for p in got]
        self.assertEqual(names[:3], ["base_run/edge_1S", "base_run/edge_2F", "base_run/edge_3S"])
        self.assertIn("hinge_base", names)
        self.assertIn("hinge_lid", names)
        self.assertEqual({p.part for p in got if p.name.startswith("lid_run/")}, {"edges/S", "edges/F"})

    def test_joint(self):
        shut = {p.name: p for p in layout(self.doc)}
        opened = {p.name: p for p in layout(self.doc, {"open_angle": "90"})}
        # Shut, the lid run lies at y = width / 2; a quarter open about x, it stands at z = width / 2.
        self.assertTrue(close(shut["lid_run/edge_1S"].at[1], 30))
        self.assertTrue(close(opened["lid_run/edge_1S"].at[1], 0), opened["lid_run/edge_1S"].at)
        self.assertTrue(close(opened["lid_run/edge_1S"].at[2], 30), opened["lid_run/edge_1S"].at)
        # The base side doesn't move.
        self.assertEqual(shut["hinge_base"].at, opened["hinge_base"].at)
        self.assertEqual(shut["base_run/edge_1S"].at, opened["base_run/edge_1S"].at)

    def test_leaves(self):
        leaves = leaf_parts(self.doc)
        self.assertEqual(leaves["lid_leaf"]["pieces"], ["side_a"])
        self.assertEqual(leaves["base_leaf"]["pieces"], ["side_b", "pins"])
        self.assertEqual({k for k, v in leaves.items() if v["print"]}, {"edges/S", "edges/M", "edges/L", "edges/F", "lid_leaf"})
        self.assertEqual(float(leaves["lid_leaf"]["values"]["length"]), 40)

    def test_checks(self):
        self.assertEqual(recipe_checks(self.doc), [])
        self.assertIn("the hinge is longer than the runs", recipe_checks(self.doc, {"hinge_length": "200"}))


class Files(unittest.TestCase):
    def test_every_recipe_writes_and_reads(self):
        for key in list(available()) + list(assemblies()):
            with self.subTest(key=key):
                doc = export(key)
                self.assertEqual(loads(dumps(doc)), doc)
                self.assertEqual(doc["version"], 2)
                self.assertEqual(set(doc["uses"]), {p["primitive"] for p in doc["parts"]})

    def test_refused(self):
        doc = export("support_pair")
        for change in ({"version": 3}, {"kind": "widget"}, {"uses": {}}):
            with self.subTest(change=change), self.assertRaises(PrimError):
                loads(json.dumps(dict(doc, **change)))


if __name__ == "__main__":
    unittest.main()
