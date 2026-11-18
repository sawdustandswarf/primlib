"""Targets: where a primitive's operations go.

- `freecad`: FreeCAD objects bound to the parameter sheet (fc_lib's Builder).
- `record`: the operations kept as a tree, sizes left as expressions over the
  primitive's names, for writing to a file another program (view4d) builds.

A primitive's build() asks for `Builder(doc, ...)`; `doc` says which.
"""


def target_for(doc):
    """The builder class for `doc`: a Recording records, anything else is a
    FreeCAD document."""
    from primlib.targets.record import Recording, RecordBuilder

    if isinstance(doc, Recording):
        return RecordBuilder
    from primlib.targets.freecad import FreeCADBuilder

    return FreeCADBuilder
