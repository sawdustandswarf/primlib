"""Compare two baseline.py results: exit 0 if every primitive came out the
same, else list what differs and exit 1.

    python3 tools/baseline_diff.py before.json after.json
"""

import json
import sys


def main(a_path, b_path):
    with open(a_path) as f:
        a = json.load(f)
    with open(b_path) as f:
        b = json.load(f)
    differ = []
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            differ.append(f"{key}:\n  before {a.get(key)}\n  after  {b.get(key)}")
    print("\n".join(differ) if differ else f"same: {len(a)} primitives")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
