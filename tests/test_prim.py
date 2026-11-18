""".prim files in plain Python: python3 -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from primlib.prim import PrimError, canonical, dumps, export, loads, primitive  # noqa: E402
from primlib.primitives import available  # noqa: E402
from primlib.targets.record import NotRecordable, record  # noqa: E402


def exportable():
    for key, cls in available().items():
        try:
            yield key, record(cls)
        except NotRecordable:
            pass


class RoundTrip(unittest.TestCase):
    def test_every_primitive_records_again_the_same(self):
        n = 0
        for key, tree in exportable():
            with self.subTest(key=key):
                again = record(primitive(loads(dumps(tree))))
                self.assertEqual(canonical(again), canonical(tree))
                for k in ("params", "fixed", "derived", "checks"):
                    self.assertEqual(again[k], tree[k])
                n += 1
        self.assertGreaterEqual(n, 19)

    def test_values_become_defaults(self):
        tree = export("pin", {"height": "12"})
        self.assertEqual(tree["values"], {"height": "12"})
        self.assertEqual(primitive(tree).params[0].default, "12")


class Refusals(unittest.TestCase):
    def test_bad_exports(self):
        for key, values in (("nope", {}), ("pin", {"nope": "1"}), ("pin", {"diam": "-1"})):
            with self.subTest(key=key, values=values), self.assertRaises(PrimError):
                export(key, values)

    def test_bad_files(self):
        good = dumps(export("pin"))
        for text in ("[", "{}", good.replace('"version": 1', '"version": 99'),
                     good.replace('"id": 0', '"id": 5')):
            with self.subTest(text=text[:40]), self.assertRaises(PrimError):
                loads(text)


if __name__ == "__main__":
    unittest.main()
