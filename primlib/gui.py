"""FreeCAD GUI commands: one "insert" command per primitive, docs, reload.

insert() and reload() hold the logic and need no GUI, so they can be
scripted and tested headless; the command classes only wrap them for the
toolbar. The command objects live as long as FreeCAD, so they look up
primlib.gui afresh on every click (_current()): after Reload, a click runs
the newly loaded code, not the code FreeCAD started with.
"""

import importlib
import inspect
import os
import sys
import webbrowser

import FreeCAD as App

from primlib import available

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _current():
    """The primlib.gui module as currently loaded (fresh after reload())."""
    return importlib.import_module("primlib.gui")


def _selection():
    import FreeCADGui as Gui
    return Gui.Selection.getSelection()


def _unique_name(doc, base):
    name, i = base, 1
    while doc.getObject(name) or doc.getObject(f"{name}_sketch"):
        name, i = f"{base}{i:03d}", i + 1
    return name


def insert(key, doc=None, selection=()):
    """Insert primitive `key` into `doc` (default: the active document).

    The parameters are appended, under a title row, to a spreadsheet in
    `selection` or else to the document's shared `Params` sheet.
    """
    prims = available()
    if key not in prims:
        App.Console.PrintError(f"primlib: no primitive '{key}' any more.\n")
        return None
    cls = prims[key]
    doc = doc or App.ActiveDocument or App.newDocument()
    sheets = [o for o in selection if o.TypeId == "Spreadsheet::Sheet"]
    obj = cls.make(doc, _unique_name(doc, cls.__name__),
                   sheet=sheets[0] if sheets else None)
    doc.recompute()
    return obj


def reload():
    """Forget every loaded primlib module and import the library afresh.

    Edits to primitives, the core and these commands take effect on the
    next click. Returns the primitive keys now available.
    """
    for name in [m for m in sys.modules if m == "primlib" or m.startswith("primlib.")]:
        del sys.modules[name]
    importlib.invalidate_caches()        # see primitive files added since
    keys = list(_current().available())
    App.Console.PrintMessage(f"primlib reloaded: {', '.join(keys)}\n")
    return keys


def doc_path(key=None):
    """Path of a primitive's HTML page, or of the index."""
    if key is None:
        return os.path.join(ROOT, "index.html")
    return os.path.join(ROOT, "primlib", "primitives", f"{key}.html")


def open_docs(selection=()):
    """Open the page of the first selected primlib object, or the index."""
    # Objects made by fc_lib, this library's predecessor, carry the older tag.
    keys = [getattr(o, "PrimlibPrimitive", None) or getattr(o, "FcLibPrimitive", None) for o in selection]
    key = next((k for k in keys if k), None)
    webbrowser.open("file://" + doc_path(key))


class _Insert:
    def __init__(self, key, cls):
        self.key, self.cls = key, cls

    def GetResources(self):
        return {"MenuText": self.cls.title,
                "ToolTip": " ".join(inspect.getdoc(self.cls).split("\n\n")[0].split())}

    def Activated(self):
        gui = _current()
        gui.insert(self.key, selection=gui._selection())

    def IsActive(self):
        return True


class _Docs:
    def GetResources(self):
        return {"MenuText": "Documentation",
                "ToolTip": "Open the page of the selected primitive (or the index)"}

    def Activated(self):
        gui = _current()
        gui.open_docs(gui._selection())

    def IsActive(self):
        return True


class _Reload:
    def GetResources(self):
        return {"MenuText": "Reload",
                "ToolTip": "Reload primlib from disk so edits take effect "
                           "without restarting FreeCAD"}

    def Activated(self):
        _current().reload()

    def IsActive(self):
        return True


def register():
    """Register every command with FreeCADGui; returns their names."""
    import FreeCADGui as Gui
    names = []
    for key, cls in available().items():
        Gui.addCommand(f"Primlib_{key}", _Insert(key, cls))
        names.append(f"Primlib_{key}")
    Gui.addCommand("Primlib_Docs", _Docs())
    Gui.addCommand("Primlib_Reload", _Reload())
    return names + ["Separator", "Primlib_Docs", "Primlib_Reload"]
