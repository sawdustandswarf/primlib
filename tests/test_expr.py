"""primlib/expr.py, in plain Python: python3 -m unittest discover tests"""

import importlib.util
import math
import os
import unittest

_path = os.path.join(os.path.dirname(__file__), "..", "primlib", "expr.py")
_spec = importlib.util.spec_from_file_location("expr", _path)
expr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(expr)  # without primlib/__init__, which needs FreeCAD
ev = expr.evaluate


class Evaluate(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(ev("1 + 2 * 3", {}), 7)
        self.assertEqual(ev("(1 + 2) * 3", {}), 9)
        self.assertEqual(ev("8 / 4 / 2", {}), 1)
        self.assertEqual(ev("10 - 4 - 3", {}), 3)
        self.assertEqual(ev("-2 * -3", {}), 6)
        self.assertEqual(ev("+(1 + 1) * 2", {}), 4)

    def test_comparisons_are_one_or_zero(self):
        self.assertEqual(ev("2 > 1", {}), 1)
        self.assertEqual(ev("2 >= 3", {}), 0)
        self.assertEqual(ev("1 + 1 == 2", {}), 1)
        self.assertEqual(ev("a != a", {"a": 1}), 0)

    def test_conditional(self):
        self.assertEqual(ev("a > 0 ? 1 : 2", {"a": 1}), 1)
        self.assertEqual(ev("a > 0 ? 1 : 2", {"a": 0}), 2)
        # right associative: a ? b : (c ? d : e)
        self.assertEqual(ev("0 ? 1 : 0 ? 2 : 3", {}), 3)
        self.assertEqual(ev("1 ? 0 ? 5 : 6 : 7", {}), 6)
        # only the chosen branch is evaluated
        self.assertEqual(ev("1 ? 2 : 1 / 0", {}), 2)

    def test_degrees(self):
        self.assertAlmostEqual(ev("sin(30)", {}), 0.5)
        self.assertAlmostEqual(ev("cos(60 deg)", {}), 0.5)
        self.assertAlmostEqual(ev("tan(45deg)", {}), 1)
        self.assertAlmostEqual(ev("asin(0.5) / 1deg", {}), 30)
        self.assertAlmostEqual(ev("atan2(1; 1)", {}), 45)
        self.assertAlmostEqual(ev("180 deg / 4", {}), 45)
        self.assertAlmostEqual(ev("pi", {}), math.pi)

    def test_functions(self):
        self.assertEqual(ev("max(1; 3; 2)", {}), 3)
        self.assertEqual(ev("min(4, 2)", {}), 2)
        self.assertEqual(ev("floor(-1.5) + ceil(1.2)", {}), 0)
        self.assertEqual(ev("abs(-2) * sqrt(9)", {}), 6)

    def test_numbers(self):
        self.assertEqual(ev("1e-3 * 1000", {}), 1)
        self.assertEqual(ev(".5 + 1.", {}), 1.5)
        self.assertEqual(ev("2 mm", {}), 2)

    def test_extents(self):
        box = {(3, "x", "min"): -1.0, (3, "x", "max"): 4.0}
        self.assertEqual(ev("xmax(@3) - xmin(@3)", {}, lambda i, a, e: box[(i, a, e)]), 5)
        with self.assertRaises(expr.ExprError):
            ev("xmin(@3)", {})

    def test_errors(self):
        for bad in ("1 +", "(1", "1 2", "foo(1)", "sin(1; 2)", "a", "1 / 0", "@2", "1 $ 2"):
            with self.subTest(bad=bad), self.assertRaises(expr.ExprError):
                ev(bad, {})


class Text(unittest.TestCase):
    ENV = {"key": "SFMF", "k": 2.0}

    def test_text(self):
        for text, want in [("key[k - 1:k]", "F"), ("key[-1]", "F"), ("key[0:9]", "SFMF"), ("key[2:1]", ""),
                           ("<<ab>> + key[0:1]", "abS"), ("(k > 1 ? <<x>> : <<y>>) + <<z>>", "xz"),
                           ("key == <<SFMF>>", 1), ("key != <<SFMF>>", 0), ("len(key)", 4),
                           ("count(key; <<F>>)", 2), ("count(key; <<>>)", 0), ("repeat(<<ab>>; 2)", "abab"),
                           ("repeat(<<ab>>; 0)", ""), ("mod(-7; 3)", -1), ("mod(7.5; 2)", 1.5), ("<<>>", "")]:
            with self.subTest(text=text):
                self.assertEqual(ev(text, self.ENV), want)

    def test_text_errors(self):
        for bad in ("key[4]", "key[0.5:1]", "<<a>> + 1", "1 + <<a>>", "<<a>> < <<b>>", "<<a>> == 1", "-key",
                    "sin(key)", "len(1)", "repeat(<<a>>; -1)", "repeat(<<a>>; 1.5)", "(key)[0:1]", "<<ab>>[0]",
                    "len(key; key)", "key ? 1 : 0"):
            with self.subTest(bad=bad), self.assertRaises(expr.ExprError):
                ev(bad, self.ENV)

    def test_for_freecad(self):
        # Unchanged without the text functions; written out over the slots with them.
        self.assertEqual(expr.freecad("key[0:1] == <<S>> ? a : b", 4), "key[0:1] == <<S>> ? a : b")
        self.assertEqual(expr.freecad("len(key)", 2),
                         "((key[0:1] != <<>> ? 1 : 0) + (key[1:2] != <<>> ? 1 : 0))")
        self.assertEqual(expr.freecad("repeat(<<B>>; n)", 2), "(((n) >= 1 ? <<B>> : <<>>) + ((n) >= 2 ? <<B>> : <<>>))")
        with self.assertRaises(expr.ExprError):
            expr.freecad("count(key; <<FF>>)", 4)
        with self.assertRaises(expr.ExprError):
            expr.freecad("len(key[0:2])", 4)


class Names(unittest.TestCase):
    TREE = {
        "params": [{"name": "w", "default": "10"}, {"name": "h", "default": "=w / 2"},
                   {"name": "label", "default": "'OAK"}],
        "fixed": [{"name": "t", "expr": "2"}],
        "derived": [{"name": "area", "expr": "w * h"}, {"name": "inner", "expr": "w - 2 * t"}],
        "checks": [{"expr": "inner", "message": "w is too small"}],
    }

    def test_defaults_formulas_strings(self):
        env = expr.names(self.TREE)
        self.assertEqual((env["w"], env["h"], env["area"], env["inner"]), (10, 5, 50, 6))
        self.assertEqual(env["label"], "OAK")
        self.assertEqual(expr.failed_checks(self.TREE, env), [])

    def test_values(self):
        env = expr.names(self.TREE, {"w": "4", "h": 1})
        self.assertEqual((env["h"], env["area"]), (1, 4))
        self.assertEqual(expr.failed_checks(self.TREE, env), ["w is too small"])


if __name__ == "__main__":
    unittest.main()
