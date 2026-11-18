"""The expression language of primlib sizes (docs/EXPRESSIONS.md): a parser
and evaluator in plain Python, no FreeCAD. The FreeCAD target hands
expressions to FreeCAD unchanged; this is the reference other targets
(view4d's Rust reader) are tested against.

    evaluate("max(a; b) / 2", {"a": 3, "b": 5})        # 2.5
    names(tree, {"width": "30"})                       # every name's value
"""

import math
import re

# -- tokens --------------------------------------------------------------------

_TOKEN = re.compile(r"""
    \s*(?:
      (?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?:\s*(?P<unit>deg|mm)\b)?
    | <<(?P<text>(?:(?!>>).)*)>>
    | (?P<ref>@\d+)
    | (?P<name>[A-Za-z_][A-Za-z_0-9]*)
    | (?P<op>>=|<=|==|!=|[-+*/()?:;,<>\[\]])
    )""", re.VERBOSE)


class ExprError(ValueError):
    """An expression that doesn't parse or can't be evaluated."""


def tokens(text):
    out, pos = [], 0
    text = str(text)
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = _TOKEN.match(text, pos)
        if not m:
            raise ExprError(f"unexpected {text[pos:].strip()[:10]!r} in {text!r}")
        pos = m.end()
        if m.group("text") is not None:
            out.append(("text", m.group("text")))
        elif m.group("num"):
            out.append(("num", float(m.group("num"))))  # deg and mm are both 1
        elif m.group("ref"):
            out.append(("ref", int(m.group("ref")[1:])))
        elif m.group("name"):
            out.append(("name", m.group("name")))
        else:
            out.append(("op", m.group("op")))
    return out


# -- parser: a tree of tuples ----------------------------------------------------
#
#   ("num", x)  ("text", s)  ("name", n)  ("ref", id)  ("neg", a)
#   ("bin", op, a, b)  ("cmp", op, a, b)  ("if", c, a, b)  ("call", f, [args])
#   ("index", s, k)  ("slice", s, a, b)

FUNCTIONS = {
    # FreeCAD's trigonometry is in degrees: sin(30) is 0.5, asin(0.5) is 30.
    "sin": (1, lambda a: math.sin(math.radians(a))),
    "cos": (1, lambda a: math.cos(math.radians(a))),
    "tan": (1, lambda a: math.tan(math.radians(a))),
    "asin": (1, lambda a: math.degrees(math.asin(a))),
    "acos": (1, lambda a: math.degrees(math.acos(a))),
    "atan": (1, lambda a: math.degrees(math.atan(a))),
    "atan2": (2, lambda y, x: math.degrees(math.atan2(y, x))),
    "sqrt": (1, math.sqrt),
    "abs": (1, abs),
    "floor": (1, lambda a: float(math.floor(a))),
    "ceil": (1, lambda a: float(math.ceil(a))),
    "min": (None, min),
    "max": (None, max),
    # FreeCAD's mod is C's fmod: the remainder takes the dividend's sign.
    "mod": (2, math.fmod),
}
# Text functions FreeCAD hasn't: the record target only. The FreeCAD target
# writes each out over a number of slots (`freecad`).
TEXT_FUNCTIONS = {"len", "count", "repeat"}
EXTENTS = {f"{a}{end}" for a in "xyz" for end in ("min", "max")}
CONSTANTS = {"pi": math.pi}


class _Parser:
    def __init__(self, text):
        self.text, self.toks, self.i = text, tokens(text), 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, op=None):
        tok = self.peek()
        if op is not None and tok != ("op", op):
            raise ExprError(f"expected {op!r} in {self.text!r}")
        self.i += 1
        return tok

    def parse(self):
        node = self.conditional()
        if self.i != len(self.toks):
            raise ExprError(f"unexpected {self.peek()[1]!r} in {self.text!r}")
        return node

    def conditional(self):
        cond = self.comparison()
        if self.peek() == ("op", "?"):
            self.take()
            a = self.conditional()
            self.take(":")
            return ("if", cond, a, self.conditional())
        return cond

    def comparison(self):
        a = self.additive()
        kind, op = self.peek()
        if kind == "op" and op in ("<", ">", "<=", ">=", "==", "!="):
            self.take()
            return ("cmp", op, a, self.additive())
        return a

    def additive(self):
        a = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            a = ("bin", self.take()[1], a, self.term())
        return a

    def term(self):
        a = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            a = ("bin", self.take()[1], a, self.unary())
        return a

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return ("neg", self.unary())
        if self.peek() == ("op", "+"):
            self.take()
            return self.unary()
        start = self.i
        node = self.atom()
        if self.peek() == ("op", "[") and (node[0] != "name" or self.i != start + 1):
            raise ExprError(f"only a name is indexed, as FreeCAD has it, in {self.text!r}")
        if self.peek() == ("op", "["):
            self.take()
            a = self.additive()
            if self.peek() == ("op", ":"):
                self.take()
                node = ("slice", node, a, self.additive())
            else:
                node = ("index", node, a)
            self.take("]")
        return node

    def atom(self):
        kind, v = self.take()
        if kind == "num":
            return ("num", v)
        if kind == "text":
            return ("text", v)
        if kind == "ref":
            return ("ref", v)
        if kind == "op" and v == "(":
            node = self.conditional()
            self.take(")")
            return node
        if kind == "name":
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.conditional())
                    while self.peek() in (("op", ";"), ("op", ",")):
                        self.take()
                        args.append(self.conditional())
                self.take(")")
                if v not in FUNCTIONS and v not in EXTENTS and v not in TEXT_FUNCTIONS:
                    raise ExprError(f"unknown function {v}() in {self.text!r}")
                return ("call", v, args)
            return ("name", v)
        raise ExprError(f"unexpected {v!r} in {self.text!r}" if kind else f"{self.text!r} ends early")


_parsed = {}


def parse(text):
    """The expression's tree (cached)."""
    text = str(text)
    if text not in _parsed:
        _parsed[text] = _Parser(text).parse()
    return _parsed[text]


# -- evaluation ----------------------------------------------------------------

def _number(v, what):
    if isinstance(v, str):
        raise ExprError(f"{what}: {v!r} is text, not a number")
    return v


def _text(v, what):
    if not isinstance(v, str):
        raise ExprError(f"{what}: {v:g} is a number, not text")
    return v


def _whole(v, what):
    v = _number(v, what)
    if v != math.floor(v):
        raise ExprError(f"{what}: {v:g} is not a whole number")
    return int(v)


def _eval(node, env, extent):
    kind = node[0]
    if kind in ("num", "text"):
        return node[1]
    if kind == "name":
        name = node[1]
        if name in env:
            return env[name]
        if name in CONSTANTS:
            return CONSTANTS[name]
        raise ExprError(f"unknown name {name}")
    if kind == "neg":
        return -_number(_eval(node[1], env, extent), "-")
    if kind == "bin":
        a, b = _eval(node[2], env, extent), _eval(node[3], env, extent)
        op = node[1]
        if op == "+" and isinstance(a, str) and isinstance(b, str):
            return a + b
        a, b = _number(a, op), _number(b, op)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise ExprError("division by zero")
        return a / b
    if kind == "cmp":
        a, b = _eval(node[2], env, extent), _eval(node[3], env, extent)
        if isinstance(a, str) or isinstance(b, str):
            if node[1] not in ("==", "!=") or not (isinstance(a, str) and isinstance(b, str)):
                raise ExprError(f"{node[1]}: text is compared only with text, by == and !=")
            return float((a == b) == (node[1] == "=="))
        return float({"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b,
                      "==": a == b, "!=": a != b}[node[1]])
    if kind == "if":
        return _eval(node[2] if _number(_eval(node[1], env, extent), "?") else node[3], env, extent)
    if kind == "index":
        s = _text(_eval(node[1], env, extent), "[]")
        k = _whole(_eval(node[2], env, extent), "[]")
        if not -len(s) <= k < len(s):
            raise ExprError(f"[{k}]: past the end of {s!r}")
        return s[k]
    if kind == "slice":
        s = _text(_eval(node[1], env, extent), "[:]")
        return s[_whole(_eval(node[2], env, extent), "[:]"):_whole(_eval(node[3], env, extent), "[:]")]
    if kind == "call":
        f, args = node[1], node[2]
        if f in EXTENTS:
            if len(args) != 1 or args[0][0] != "ref":
                raise ExprError(f"{f}() takes an operation, @id")
            if extent is None:
                raise ExprError(f"{f}(@{args[0][1]}) needs the operation's shape")
            return extent(args[0][1], f[0], f[1:])
        if f in TEXT_FUNCTIONS:
            vals = [_eval(a, env, extent) for a in args]
            if len(vals) != {"len": 1, "count": 2, "repeat": 2}[f]:
                raise ExprError(f"{f}() takes {'one argument' if f == 'len' else '2 arguments'}, not {len(vals)}")
            s = _text(vals[0], f"{f}()")
            if f == "len":
                return float(len(s))
            if f == "count":
                return float(s.count(_text(vals[1], "count()"))) if vals[1] else 0.0
            n = _whole(vals[1], "repeat()")
            if n < 0:
                raise ExprError(f"repeat(): {n} times")
            return s * n
        n, fn = FUNCTIONS[f]
        if n is not None and len(args) != n:
            raise ExprError(f"{f}() takes {n} argument{'s' * (n > 1)}, not {len(args)}")
        vals = [_number(_eval(a, env, extent), f"{f}()") for a in args]
        try:
            return float(fn(*vals))
        except (ValueError, TypeError) as e:
            raise ExprError(f"{f}({', '.join(f'{v:g}' for v in vals)}): {e}") from e
    if kind == "ref":
        raise ExprError(f"@{node[1]} is an operation, not a number")
    raise ExprError(f"bad node {node!r}")


def evaluate(text, env, extent=None):
    """The value of expression `text`, its names from `env` (name -> value).
    `extent(id, axis, "min" or "max")` gives xmin(@id) and the like."""
    return _eval(parse(text), env, extent)


def is_string(value):
    """A string value is written as FreeCAD writes a text cell: 'text."""
    return isinstance(value, str) and value.startswith("'")


def names(tree, values=None):
    """Every name of recorded primitive `tree` (params, fixed, derived) ->
    its value, the params from `values` (name -> expression or number) or
    their defaults. A default "=expr" is a formula over the params before
    it; a string ('text) stays a string, without its quote."""
    values = values or {}
    env = {}
    for p in tree["params"]:
        v = values.get(p["name"], p["default"])
        if isinstance(v, (int, float)):
            env[p["name"]] = float(v)
        elif is_string(v):
            env[p["name"]] = v[1:]
        else:
            env[p["name"]] = evaluate(v[1:] if v.startswith("=") else v, env)
    for d in tree["fixed"] + tree["derived"]:
        env[d["name"]] = d["expr"][1:] if is_string(d["expr"]) else evaluate(d["expr"], env)
    return env


def failed_checks(tree, env):
    """The messages of the checks that fail (value not over 0) at `env`."""
    return [c["message"] for c in tree["checks"] if not evaluate(c["expr"], env) > 0]


# -- written for FreeCAD -----------------------------------------------------------

def _uses_text_functions(node):
    if node[0] == "call" and node[1] in TEXT_FUNCTIONS:
        return True
    return any(_uses_text_functions(a) for a in node[1:] if isinstance(a, tuple)) or \
        any(_uses_text_functions(a) for a in (node[2] if node[0] == "call" else ()))


def freecad(text, slots, names=None):
    """Expression `text` as FreeCAD can evaluate it: unchanged, unless it
    uses len(), count() or repeat(), which FreeCAD hasn't. Those are written
    out over `slots` places, so they hold for text up to `slots` letters
    long (and a count() for one letter at a time). With `names` (name ->
    what to write for it: an alias, or a number), it is always written
    out, each name replaced."""
    node = parse(text)
    if names is None and not _uses_text_functions(node):
        return str(text)
    return _Writer(slots, names or {}).write(node)


def _num(v):
    v = float(v)
    return repr(int(v)) if v == int(v) and abs(v) < 1e15 else repr(v)


class _Writer:
    def __init__(self, slots, names):
        self.slots, self.names = slots, names

    def name(self, n):
        return str(self.names.get(n, n))

    def write(self, node):
        kind = node[0]
        w = self.write
        if kind == "num":
            return _num(node[1])
        if kind == "text":
            return f"<<{node[1]}>>"
        if kind == "name":
            return self.name(node[1])
        if kind == "ref":
            return f"@{node[1]}"
        if kind == "neg":
            return f"-({w(node[1])})"
        if kind in ("bin", "cmp"):
            return f"({w(node[2])}) {node[1]} ({w(node[3])})"
        if kind == "if":
            return f"({w(node[1])} ? {w(node[2])} : {w(node[3])})"
        if kind == "index":
            return f"{self.name(node[1][1])}[{w(node[2])}]"
        if kind == "slice":
            return f"{self.name(node[1][1])}[{w(node[2])}:{w(node[3])}]"
        f, args = node[1], node[2]
        if f == "len":
            return self.length(args[0], None)
        if f == "count":
            if args[1][0] == "text" and len(args[1][1]) != 1:
                raise ExprError(f"count(): FreeCAD counts one letter, not {args[1][1]!r}")
            return self.length(args[0], w(args[1]))
        if f == "repeat":
            s, n = w(args[0]), w(args[1])
            return "(" + " + ".join(f"(({n}) >= {j + 1} ? {s} : <<>>)" for j in range(self.slots)) + ")"
        return f"{f}({'; '.join(w(a) for a in args)})"

    def length(self, node, letter):
        """len(node), or count(node; letter) for one letter, for FreeCAD:
        over the slots of a name, through the joins, repeats and choices
        that make other text (FreeCAD slices only a name)."""
        kind = node[0]
        if kind == "text":
            if letter is None or not node[1]:
                return _num(len(node[1]) if letter is None else 0)
            return "(" + " + ".join(f"(<<{c}>> == {letter} ? 1 : 0)" for c in node[1]) + ")"
        if kind == "name":
            test = "!= <<>>" if letter is None else f"== {letter}"
            n = self.name(node[1])
            return "(" + " + ".join(f"({n}[{k}:{k + 1}] {test} ? 1 : 0)" for k in range(self.slots)) + ")"
        if kind == "bin" and node[1] == "+":
            return f"({self.length(node[2], letter)} + {self.length(node[3], letter)})"
        if kind == "if":
            return f"({self.write(node[1])} ? {self.length(node[2], letter)} : {self.length(node[3], letter)})"
        if kind == "call" and node[1] == "repeat":
            return f"(({self.write(node[2][1])}) * {self.length(node[2][0], letter)})"
        if kind == "index" and letter is None:
            return "1"
        raise ExprError(f"{'len' if letter is None else 'count'}() of this for FreeCAD: give the text a name first")
