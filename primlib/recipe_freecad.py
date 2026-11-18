"""Recipes in FreeCAD (docs/FORMAT.md#recipes): a recipe document compiled
to what stock FreeCAD recomputes by itself, as the hybrid case is built.

- Every name of the recipe is a cell on the sheet, aliased `{name}_{x}`
  (FreeCAD slices only a name, so a key must be a cell), and a `Status`
  cell says OK or the first check that fails, the parts' included.
- Each part is a master: its primitive made bound to the cells
  (Primitive.make), mirrored by a Part::Mirroring if the part is.
- Each placement is App::Links to the masters: a row is one per slot and
  letter, its `Visibility` whether that slot holds that letter and its
  place from a cell per slot; a series is one per slot up to `slots`,
  shown while the count is over it; a choice shows one side or the other.
- An assembly's part that is a recipe or assembly has its own cells
  (`{name}_{part}_{x}`, bound to the outer ones) and masters, made once;
  its placements are laid out wherever the part is placed, links labelled
  `{placed}/{its name}` as layout names them.
- A joint is an App::Part turned by formulas over its angle about its
  line, as the hybrid case's lid is, holding what it turns; a joint inside
  a move or turn sits in an App::Part placed as that is.
- Masters of parts marked to print go in the `{name} print list` group,
  the rest in `{name} parts`.

So a key, a count, a size or a joint's angle changed on the sheet lays out
again on recompute, up to `slots` pieces, without primlib. A turn's angle
must be a number here (links are turned when they are made); everything
else follows the sheet.

    make_recipe(load("edge_run.prim"), doc, "Run", key="'SMF")
"""

from primlib.core import _hide, add_parameter, add_section, document_sheet, expand, qualify
from primlib.expr import ExprError, evaluate, freecad
from primlib.recipe import AXES, IDENTITY, RecipeError, _mul, compound_pieces, is_recipe, turn_matrix


def _alias(prefix, name):
    return f"{prefix}{name}"


class _Shared:
    """What a recipe and the recipes inside it build into together."""

    def __init__(self):
        self.checks = []         # (fails-when expression, message)
        self.top = []            # the objects of the result group
        self.container = None    # the App::Part links go in, or None for the top
        self.label = ""          # put before link labels: "lid_run/"
        self.parts_group = self.print_group = None

    def add(self, obj):
        if self.container is not None:
            self.container.addObject(obj)
        else:
            self.top.append(obj)


class _Compiler:
    def __init__(self, tree, doc, name, sheet, shared, title=None, check_prefix="", printed=False):
        self.tree, self.doc, self.name, self.sheet = tree, doc, name, sheet
        self.shared = shared
        self.prefix = f"{name}_"
        self.title = title if title is not None else f"{name} "   # master labels: "{title}{part}"
        self.check_prefix = check_prefix
        self.printed = printed
        self.slots = tree["slots"]
        self.names = {}        # recipe name -> alias
        self.made = {}         # placement id -> the cells made for it (a row's, a series')
        self.inner = {}        # part name -> _Compiler of a recipe or assembly part

    def check(self, test, message):
        self.shared.checks.append((test, self.check_prefix + message))

    # -- expressions ---------------------------------------------------------------

    def x(self, text, extra=None):
        """`text` over the recipe's names, as FreeCAD writes it on the sheet."""
        return freecad(text, self.slots, dict(self.names, **(extra or {})))

    def cell(self, name, formula, note=""):
        alias = _alias(self.prefix, name)
        add_parameter(self.sheet, alias, formula, note)
        self.names[name] = alias
        return alias

    def number(self, text, what):
        """A number the FreeCAD target needs when it builds (a turn's angle)."""
        try:
            v = evaluate(text, {})
        except ExprError as e:
            raise RecipeError(f"{what}: {text}: the FreeCAD target turns links when it makes them, "
                              f"so an angle is a number") from e
        return float(v)

    # -- the sheet -----------------------------------------------------------------

    def sheet_rows(self, values, bound=None):
        """The recipe's names as cells, at `values`; `bound` (param -> a
        FreeCAD formula over the outer cells) for a recipe inside another."""
        t = self.tree
        bound = bound or {}
        add_section(self.sheet, f"{self.name}: {t['title'] or t['primitive']}")
        group = None
        for p in t["params"]:
            if p.get("group") != group and p.get("group"):
                group = p["group"]
                add_section(self.sheet, group, style="italic")
            v = str(values.get(p["name"], p["default"]))
            if p["name"] in bound:
                v = "=" + bound[p["name"]]
            elif v.startswith("="):
                v = "=" + self.x(v[1:])
            elif not v.startswith("'"):
                v = "=" + self.x(v)
            self.cell(p["name"], v, p.get("note", ""))
        if t["fixed"] or t["derived"]:
            add_section(self.sheet, "Derived", style="italic")
        for d in t["fixed"] + t["derived"]:
            e = d["expr"]
            self.cell(d["name"], e if e.startswith("'") else "=" + self.x(e), d.get("note", ""))
        for c in t["checks"]:
            self.check(f"+({self.x(c['expr'])}) <= 0", c["message"])

    def status(self):
        """`Status`: OK or the first check that fails, eight checks a cell
        (FreeCAD can't parse conditionals nested much deeper), each cell
        falling through to the next."""
        checks = self.shared.checks
        chunks = [checks[k:k + 8] for k in range(0, len(checks), 8)] or [[]]
        names = [_alias(self.prefix, "Status")] + [_alias(self.prefix, f"Status_{k + 1}") for k in
                                                   range(1, len(chunks))]
        # From the last: each cell refers to one above it (FreeCAD has left a cell
        # referring to one below it stale when that one changed).
        for k, chunk in reversed(list(enumerate(chunks))):
            formula = names[k + 1] if k + 1 < len(chunks) else "<<OK>>"
            for test, message in reversed(chunk):
                formula = f"{test} ? <<{message.replace('>>', '> >')}>> : ({formula})"
            add_parameter(self.sheet, names[k], "=" + formula,
                          "OK, or the first check that fails" if k == 0 else "the checks, continued")

    # -- the masters -------------------------------------------------------------

    def masters(self):
        from primlib.prim import primitive

        sh = self.shared
        if sh.parts_group is None:
            sh.parts_group = self.doc.addObject("App::DocumentObjectGroup", f"{self.name}_parts")
            sh.parts_group.Label = f"{self.name} parts"
            sh.print_group = self.doc.addObject("App::DocumentObjectGroup", f"{self.name}_print")
            sh.print_group.Label = f"{self.name} print list"
        self.master = {}
        for part in self.tree["parts"]:
            used = self.tree["uses"][part["primitive"]]
            bind = {k: self.x(v) for k, v in part["bind"].items()}
            printed = self.printed or part.get("print", False)
            if is_recipe(used):
                # Its own cells bound to these, its masters; laid out where it's placed.
                inner = _Compiler(used, self.doc, f"{self.name}_{part['name']}", self.sheet, sh,
                                  title=f"{self.title}{part['name']}/",
                                  check_prefix=f"{self.check_prefix}part {part['name']}: ", printed=printed)
                inner.sheet_rows({}, bind)
                self.doc.recompute()
                inner.masters()
                self.inner[part["name"]] = inner
                continue
            cls = primitive(used)
            # The primitive's checks over the recipe's cells, its unbound params at their
            # defaults, for the Status cell.
            full = {}
            for p in cls.params:
                d = str(p.default)
                full[p.name] = bind.get(p.name) or (expand(d[1:], full) if d.startswith("=") else
                                                    f"<<{d[1:]}>>" if d.startswith("'") else d)
            for test, message in cls.nested_checks(full):
                self.check(f"+({test}) <= 0", f"part {part['name']}: {message}")
            obj = cls.make(self.doc, f"{self.name}_{part['name']}", self.sheet,
                           prefix=f"{self.name}_{part['name']}_", bind=bind)
            if obj is None:
                raise RecipeError(f"part {part['name']}: its checks fail (see the report view)")
            obj.Label = f"{self.title}{part['name']}"
            group = sh.print_group if printed else sh.parts_group
            if part.get("pieces"):
                # Some of the compound's pieces: a compound of those, the whole one kept hidden.
                names = compound_pieces(used)
                taken = self.doc.addObject("Part::Compound", f"{self.name}_{part['name']}_pieces")
                taken.Links = [obj.Links[names.index(n)] for n in part["pieces"]]
                label, obj.Label = obj.Label, f"{self.title}{part['name']} (whole)"
                taken.Label = label
                _hide(obj)
                sh.parts_group.addObject(obj)
                obj = taken
            if part["mirror"]:
                mirrored = self.doc.addObject("Part::Mirroring", f"{self.name}_{part['name']}_mirrored")
                mirrored.Source = obj
                mirrored.Normal = tuple(1.0 if a == part["mirror"] else 0.0 for a in AXES)
                mirrored.Label = f"{self.title}{part['name']} mirrored"
                _hide(obj)
                sh.parts_group.addObject(obj)
                obj = mirrored
            group.addObject(obj)
            if part.get("colour") and getattr(obj, "ViewObject", None) is not None:
                obj.ViewObject.ShapeColor = tuple(part["colour"])
            _hide(obj)
            self.master[part["name"]] = obj

    # -- the placements ------------------------------------------------------------

    def turns(self, node, what):
        m = IDENTITY
        for t in node["turn"]:
            m = _mul(turn_matrix(t["axis"], self.number(t["angle"], what)), m)
        return m

    @staticmethod
    def linear(m, v, t):
        """Each axis of m · v + t, as expressions: m constant, v and t
        expressions (t's may be None for 0)."""
        out = []
        for i in range(3):
            terms = []
            for k in range(3):
                c = m[i][k]
                if abs(c) < 1e-12:
                    continue
                terms.append(f"({v[k]})" if c == 1 else f"-({v[k]})" if c == -1 else f"{c!r} * ({v[k]})")
            if t[i] is not None:
                terms.append(f"({t[i]})")
            out.append(" + ".join(terms) if terms else "0")
        return out

    @staticmethod
    def shown(vis, test):
        return test if vis is None else f"{vis} ? ({test}) : 0"

    def put(self, label, part, rotation, at, vis):
        """`part` turned by `rotation`, at `at` (expressions over aliases),
        shown when `vis` (or always): a link to its master, or a recipe
        part's placements laid out there."""
        inner = self.inner.get(part)
        if inner is None:
            self.link(label, part, rotation, at, vis)
            return
        sh = self.shared
        before = sh.label
        sh.label = f"{before}{label}/"
        inner.place(inner.tree["result"], (rotation, tuple(at)), vis, None)
        sh.label = before

    def link(self, label, part, rotation, at, vis):
        """A link to `part`'s master turned by `rotation`, at `at` (expressions
        over aliases), shown when `vis` (or always)."""
        import FreeCAD as App

        label = self.shared.label + label
        obj = self.doc.addObject("App::Link", f"{self.name}_{label.replace('/', '_')}")
        obj.Label = label
        obj.LinkedObject = self.master[part]
        r = App.Matrix()
        for i in range(3):
            for j in range(3):
                setattr(r, f"A{i + 1}{j + 1}", rotation[i][j])
        obj.Placement = App.Placement(App.Vector(), App.Rotation(r))
        for axis, e in zip(AXES, at):
            obj.setExpression(f".Placement.Base.{axis}", qualify(self.sheet, e))
        if vis is not None:
            obj.setExpression("Visibility", qualify(self.sheet, vis))
        self.shared.add(obj)

    def container(self, label, rotation, base):
        """An App::Part in the current container, turned by `rotation` (a
        matrix) and at `base` (expressions, or None for 0); links made
        after go in it until it is left."""
        import FreeCAD as App

        part = self.doc.addObject("App::Part", f"{self.name}_{label.replace('/', '_')}")
        part.Label = label
        r = App.Matrix()
        for i in range(3):
            for j in range(3):
                setattr(r, f"A{i + 1}{j + 1}", rotation[i][j])
        part.Placement = App.Placement(App.Vector(), App.Rotation(r))
        for axis, e in zip(AXES, base):
            if e is not None:
                part.setExpression(f".Placement.Base.{axis}", qualify(self.sheet, e))
        self.shared.add(part)
        return part

    def joint(self, i, node, outer, vis, what):
        """The joint's App::Part: turned by its angle about the line through
        `at` along its axis (Roll, Pitch or Yaw: about x, y or z), so its
        base is at - R at; what it turns placed in it as at the origin."""
        sh = self.shared
        m_out, t_out = outer
        label = sh.label + (node["name"] or "joint")
        before = sh.container
        if m_out != IDENTITY or any(e is not None for e in t_out):
            sh.container = self.container(f"{label} (placed)", m_out, t_out)
        ax = AXES.index(node["axis"])
        if i in self.made:
            pass
        elif node["angle"] in self.names:     # a name: its cell
            self.made[i] = self.names[node["angle"]]
        else:
            self.made[i] = self.cell(f"{node['name'] or 'joint'}_turned", "=" + self.x(node["angle"]),
                                     f"{node['name'] or 'joint'}: how far it turns, degrees")
        angle = self.made[i]
        a = [self.x(e) for e in node["at"]]
        c, s = f"cos({angle})", f"sin({angle})"
        # R's rows about x, y, z (as turn_matrix), over c and s.
        rows = {0: [["1", "0", "0"], ["0", c, f"-{s}"], ["0", s, c]],
                1: [[c, "0", s], ["0", "1", "0"], [f"-{s}", "0", c]],
                2: [[c, f"-{s}", "0"], [s, c, "0"], ["0", "0", "1"]]}[ax]
        base = []
        for i in range(3):
            ra = " + ".join(f"{r} * ({v})" for r, v in zip(rows[i], a) if r != "0")
            base.append(f"({a[i]}) - ({ra or '0'})")
        part = self.container(label, IDENTITY, base)
        part.setExpression(f".Placement.Rotation.{('Roll', 'Pitch', 'Yaw')[ax]}", qualify(self.sheet, angle))
        sh.container = part
        self.place(node["base"], (IDENTITY, (None, None, None)), vis, None)
        sh.container = before

    def place(self, i, outer, vis, index):
        """Placement `i` under the outer transform (rotation, (tx, ty, tz)
        expressions), shown when `vis`; `index` the series' i, or None."""
        node = self.tree["place"][i]
        kind, name = node["op"], node["name"]
        what = f"placement {i} ({kind} {name})"
        extra = {} if index is None else {"i": index}
        m_out, t_out = outer
        if kind == "instance":
            m = _mul(m_out, self.turns(node, what))
            at = self.linear(m_out, [self.x(e, extra) for e in node["at"]], t_out)
            label = name or node["part"]
            if index is not None:
                label = f"{label}_{index + 1}"
            self.put(label, node["part"], m, at, vis)
        elif kind == "row":
            if index is not None:
                raise RecipeError(f"{what}: a row inside a series isn't laid out in FreeCAD yet")
            self.row(i, node, outer, vis, what)
        elif kind == "joint":
            if index is not None:
                raise RecipeError(f"{what}: a joint inside a series isn't laid out in FreeCAD yet")
            self.joint(i, node, outer, vis, what)
        elif kind == "series":
            if index is not None:
                raise RecipeError(f"{what}: a series inside a series isn't laid out in FreeCAD yet")
            if i not in self.made:
                self.made[i] = self.cell(f"{name}_count", "=" + self.x(node["count"]), f"{name}: how many")
                self.check(f"{self.made[i]} >= {self.slots + 1}", f"{name}: more than {self.slots}")
            count = self.made[i]
            for k in range(self.slots):
                self.place(node["item"], outer, self.shown(vis, f"{count} >= {k + 1}"), k)
        elif kind == "choose":
            guard = f"+({self.x(node['guard'], extra)})"
            self.place(node["then"], outer, self.shown(vis, f"{guard} > 0"), index)
            if node["otherwise"] is not None:
                self.place(node["otherwise"], outer, self.shown(vis, f"{guard} <= 0"), index)
        elif kind == "group":
            for j in node["of"]:
                self.place(j, outer, vis, index)
        elif kind == "move":
            m = self.turns(node, what)
            by = [self.x(e, extra) for e in node["by"]]
            # p' = m (m_out p + t_out) + by: the move is outside what it moves.
            t = self.linear(m, [e if e is not None else "0" for e in t_out], by) if any(
                e is not None for e in t_out) else by
            self.place(node["base"], (_mul(m, m_out), t), vis, index)
        else:
            raise RecipeError(f"{what}: unknown placement")

    def row(self, i, node, outer, vis, what):
        name = node["name"] or "row"
        m_out, t_out = outer
        sign = -1 if node["along"].startswith("-") else 1
        axis = AXES.index(node["along"].lstrip("-"))
        m = _mul(m_out, self.turns(node, what))
        if i not in self.made:
            self.made[i] = self.row_cells(node, name)
        key, starts = self.made[i]
        for k in range(self.slots):
            at = [self.x(e) for e in node["at"]]
            at[axis] = f"({at[axis]}) {'+' if sign > 0 else '-'} {starts[k]}"
            at = self.linear(m_out, at, t_out)
            for c, piece in node["pieces"].items():
                self.put(f"{name}_{k + 1}{c}", piece["part"], m, at,
                         self.shown(vis, f"{key}[{k}:{k + 1}] == <<{c}>>"))

    def row_cells(self, node, name):
        """A row's key and each slot's start, as cells: (key, [starts])."""
        key = node["key"]
        if key in self.names:
            key = self.names[key]
        else:
            key = self.cell(f"{name}_key", "=" + self.x(key), f"{name}: the key")
        self.check(f"{key}[{self.slots}:{self.slots + 1}] != <<>>", f"{name}: the key is longer than {self.slots}")
        gap, lead = self.x(node["gap"]), self.x(node["lead"])
        starts = []
        for k in range(self.slots):
            if k == 0:
                formula = f"={lead}"
            else:
                letter = f"{key}[{k - 1}:{k}]"
                length = "0"
                for c, piece in reversed(list(node["pieces"].items())):
                    length = f"({letter} == <<{c}>> ? ({self.x(piece['length'])}) : {length})"
                formula = f"={starts[-1]} + +{length} + ({gap})"
            starts.append(self.cell(f"{name}_start{k + 1}", formula, f"{name}: slot {k + 1}'s start"))
        return key, starts


def make_recipe(tree, doc, name, sheet=None, **values):
    """Recipe document `tree` (load() or export()) built into FreeCAD
    document `doc` as `name`: its sheet rows (at its values, or these),
    masters and links. Returns the group of links. Raises RecipeError if a
    check fails at the values, or a placement can't be laid out here."""
    from primlib.recipe import recipe_checks

    values = dict(tree.get("values", {}), **{k: str(v) for k, v in values.items()})
    failed = recipe_checks(tree, values)
    if failed:
        raise RecipeError(f"{name}: " + "; ".join(failed))
    sheet = sheet or document_sheet(doc)
    shared = _Shared()
    c = _Compiler(tree, doc, name, sheet, shared)
    c.sheet_rows(values)
    doc.recompute()
    c.masters()
    c.place(tree["result"], (IDENTITY, (None, None, None)), None, None)
    c.status()
    group = doc.addObject("App::DocumentObjectGroup", name)
    group.Label = name
    for obj in shared.top:
        group.addObject(obj)
    doc.recompute()
    return group


def _links(objs):
    for obj in objs:
        if obj.TypeId == "App::Part":
            yield from _links(obj.Group)
        elif obj.TypeId == "App::Link":
            yield obj


def placed(group):
    """The links of `group` (in App::Parts too) that are shown, placed in
    the document: [(label, part's master label, rotation rows, (x, y, z))],
    to compare with recipe.layout."""
    out = []
    for link in _links(group.Group):
        if not link.Visibility:
            continue
        p, parent = link.Placement, link.getParentGeoFeatureGroup()
        while parent is not None:                 # through the App::Parts it is in
            p = parent.Placement.multiply(p)
            parent = parent.getParentGeoFeatureGroup()
        m = p.Rotation.toMatrix()
        rot = tuple(tuple(round(getattr(m, f"A{i + 1}{j + 1}"), 12) for j in range(3)) for i in range(3))
        out.append((link.Label, link.LinkedObject.Label, rot, (p.Base.x, p.Base.y, p.Base.z)))
    return out


def print_list(doc, name):
    """The labels of the masters in recipe `name`'s print list."""
    return sorted(o.Label for o in doc.getObject(f"{name}_print").Group)


__all__ = ["make_recipe", "placed", "print_list"]
