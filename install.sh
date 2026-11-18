#!/usr/bin/env bash
# Link this folder into FreeCAD's user add-on directory (Mod/primlib).
# Edits here are live after a FreeCAD restart; remove the link to uninstall.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
data="$(freecadcmd -c 'import FreeCAD; print("DATADIR=" + FreeCAD.getUserAppDataDir())' \
        2>/dev/null | sed -n 's/^DATADIR=//p')"
[ -n "$data" ] || { echo "could not ask freecadcmd for the user data dir" >&2; exit 1; }

mkdir -p "$data/Mod"
ln -sfn "$here" "$data/Mod/primlib"
echo "linked $data/Mod/primlib -> $here"
