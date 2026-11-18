#!/usr/bin/env bash
# Run one of primlib's FreeCAD scripts by its path:  tools/run.sh make_docs.py
#
# freecadcmd loads a script by its module name, and the add-on folders come
# first on its path: if another installed add-on has a make_docs.py,
# `freecadcmd make_docs.py` runs that one, whatever the path given. runpy runs this file.
set -euo pipefail
script="$(realpath "$1")"
exec freecadcmd -c "import runpy, sys; sys.argv = ['$script']; runpy.run_path('$script', run_name='__main__')"
