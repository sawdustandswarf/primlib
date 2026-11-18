# FreeCAD add-on entry point: the primlib workbench.
# FreeCAD exec()s this file (no __file__); the add-on folder is on sys.path,
# so the primlib package imports directly.

import FreeCADGui as Gui


class PrimlibWorkbench(Gui.Workbench):
    MenuText = "primlib"
    ToolTip = "Spreadsheet-driven parametric primitives"

    def Initialize(self):
        from primlib import gui
        commands = gui.register()
        self.appendToolbar("primlib", commands)
        self.appendMenu("primlib", commands)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(PrimlibWorkbench())
