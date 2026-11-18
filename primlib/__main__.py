"""primlib on the command line, in plain Python (no FreeCAD):

    python3 -m primlib list
    python3 -m primlib export KEY [--set NAME=VALUE ...] [-o FILE.prim]
    python3 -m primlib check FILE.prim [--set NAME=VALUE ...]
"""

import argparse
import sys

from primlib.prim import PrimError, check, dumps, export, load, save
from primlib.primitives import available
from primlib.targets.record import NotRecordable


def _values(pairs):
    out = {}
    for pair in pairs or ():
        name, sep, value = pair.partition("=")
        if not sep or not name:
            raise PrimError(f"--set takes NAME=VALUE, not {pair!r}")
        out[name.strip()] = value.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="primlib", description="primlib primitives as .prim files")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the primitives (whether each exports) and recipes")
    ex = sub.add_parser("export", help="write a primitive or recipe as a .prim file")
    ex.add_argument("key")
    ex.add_argument("--set", action="append", metavar="NAME=VALUE", help="a parameter's value")
    ex.add_argument("-o", "--output", help="the file (default: standard output)")
    ck = sub.add_parser("check", help="a .prim file's checks at its values, or these")
    ck.add_argument("file")
    ck.add_argument("--set", action="append", metavar="NAME=VALUE")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "list":
            from primlib.targets.record import record
            for key, cls in available().items():
                try:
                    record(cls)
                    print(f"{key:22} {cls.title}")
                except NotRecordable as e:
                    print(f"{key:22} {cls.title}  (doesn't export: {e})")
            from primlib.assemblies import available as assemblies
            from primlib.recipes import available as recipes
            for key, cls in recipes().items():
                print(f"{key:22} {cls.title}  (recipe)")
            for key, cls in assemblies().items():
                print(f"{key:22} {cls.title}  (assembly)")
        elif args.cmd == "export":
            tree = export(args.key, _values(args.set))
            if args.output:
                save(tree, args.output)
            else:
                sys.stdout.write(dumps(tree))
        elif args.cmd == "check":
            tree = load(args.file)
            values = dict(tree.get("values", {}), **_values(args.set))
            failed = check(tree, values)
            for message in failed:
                print(f"{tree['primitive']}: {message}")
            return 1 if failed else 0
    except (PrimError, NotRecordable, OSError) as e:
        print(f"primlib: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
