---
name: fc-configurator
description: >
  DRAFT, not yet used. How to refine a primlib composite in FreeCAD (a recipe or assembly
  compiled by make_recipe, such as the hybrid case) with a dialog inside FreeCAD that sets
  up a particular configuration: the user picks sizes, keys and options in a form, and the
  dialog writes the composite's sheet cells and recomputes. Use when asked to make or change
  such a dialog or configurator, or to add a configuration to one.
---

# Configuring a composite with a dialog

**Status: draft.** No configurator has been built yet. These are the principles
it must keep, and the questions to settle with the author when the first one is
built. After that, rewrite this skill from what worked.

A composite (`fc-composite`) compiled for FreeCAD is already tailored by editing
its sheet: every name is a cell aliased `{name}_{x}`, and the `Status` cell says
OK or what to change. A configurator is a dialog in FreeCAD that makes this
easier: it shows the choices that matter, checks them, and writes the cells.

## Principles

1. **The file still stands on its own.** The dialog is a convenience, not a
   dependency:
   - It only writes sheet cells and recomputes. It never creates or deletes
     the objects the model depends on.
   - Without it, the file opens, recomputes, and can be configured by hand.
     `tools/check_portable.py` must still report stock FreeCAD only.
2. **The sheet is the configuration.** Everything the dialog sets lives in sheet
   cells, so it is saved with the file and visible without the dialog. The
   dialog keeps no hidden state of its own.
3. **Parameter importance sets the layout.**
   - First order values (the composite's own sizes, then each part's first
     order cells) come first.
   - Second order values sit under an "Advanced" section, closed by default.
   - Fixed values are shown read only, or not at all.
   - Build the fields from the composite's declaration (its `params`, notes
     and `groups`) or the sheet's aliases rather than by hand, so a new
     parameter turns up without the dialog changing.
4. **It shows the model's own checks.**
   - After each change, recompute and show the `Status` cell (`OK`, or what to
     change).
   - Don't copy the rules into the dialog's code, because they would drift
     from the composite's checks.
5. **Configurations can be named.** A named configuration is a set of cell
   values (for example "Commuter, 350 × 260"). Store them in the document
   (a Configurations sheet: a column per configuration, a row per alias), so
   they travel with the file.
6. **It writes only what the user changed.** Typed cells the user didn't touch
   stay as they are. Apply the changes as one recompute, and the user can undo
   them (an open/commit transaction).

## Likely shape (to confirm)

- A FreeCAD task panel (`FreeCADGui.Control.showDialog`), using PySide
  (`from PySide import QtGui, QtCore`), so it docks beside the model rather than
  covering it.
- It ships as an `.FCMacro` beside the composite's file, or as a command on
  primlib's toolbar (`primlib/gui.py`) if it is general enough to drive any
  compiled composite from its sheet.
- Each field is chosen by the cell's type: a number with its unit, a key typed
  as letters with the letters it allows, a switch for a 0/1 option, and a list
  for a named configuration.

## Open questions for the author

- Should there be one dialog per composite (a macro beside the file), or one
  general configurator in primlib that reads any compiled composite's sheet?
- Which values does the user set in it? Only the composite's own sizes, or each
  part's keys and options too?
- Should named configurations live in the file, in separate files, or both?
- Should it also export what a configuration needs: STLs of the pieces shown, a
  cut list, a parts count?

## Testing

- Test on a copy of the composite in a scratch folder.
- The dialog needs the GUI, so test its logic (reading aliases, writing cells,
  reading the Status) as plain functions run with `tools/run.sh`, and the
  dialog itself by opening it in FreeCAD with the author.
- After using it, the file must recompute with no errors, the Status must read
  `OK`, and `tools/check_portable.py` must report stock FreeCAD only.
