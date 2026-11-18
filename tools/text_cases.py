"""Text expressions (docs/EXPRESSIONS.md#text) checked three ways: against
FreeCAD (tools/expr_check.py, written out by expr.freecad), and in view4d's
reader (tools/view4d_fixtures.py puts them in cases.json)."""

TEXT_ENV = {"key": "SFMF", "k": 2.0, "n": 3.0, "bigs": 3.0, "littles": 2.0}
TEXT_CASES = [
    "key[k - 1:k]", "key[-1]", "key[0:9]", "key[2:1]", "key[-2:4]", "<<ab>> + key[0:1] + <<c>>",
    "(k > 1 ? <<x>> : <<y>>) + <<z>>", "key == <<SFMF>>", "key != <<SF>>", "mod(-7; 3)", "mod(7.5; 2)",
    "len(key)", "count(key; <<F>>)", "repeat(<<ab>>; n)", "key[0:2] + repeat(<<O>>; k)", "len(key + <<X>>) * 2",
    "count(<<FAF>> + key; <<F>>)", "len(k > 1 ? key : <<ab>>)", "count(key; <<F>>) > 1 ? 1 : 0",
    "len(repeat(<<B>>; floor(bigs / 2)))",
    "repeat(<<L>>; littles / 2) + repeat(<<B>>; floor(bigs / 2)) + (mod(bigs; 2) == 1 ? <<OBO>> : <<O>>)"
    " + repeat(<<B>>; floor(bigs / 2)) + repeat(<<L>>; littles / 2)",
]
# Refused by the evaluator (as tests/test_expr.py's).
TEXT_ERRORS = ["key[4]", "key[0.5:1]", "<<a>> + 1", "1 + <<a>>", "<<a>> < <<b>>", "<<a>> == 1", "-key",
               "sin(key)", "len(1)", "repeat(<<a>>; -1)", "repeat(<<a>>; 1.5)", "(key)[0:1]", "<<ab>>[0]",
               "len(key; key)", "key ? 1 : 0", "<<open"]
