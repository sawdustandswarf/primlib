"""Record every primitive with the record target and say which can be kept
as a tree today, and why the rest can't (docs/PLAN.md 1.1, 1.2).

    tools/run.sh tools/record_check.py      # RECORD_OUT=dir also writes KEY.json there
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import primlib as lib  # noqa: E402
from primlib.targets.record import NotRecordable, record  # noqa: E402

out = os.environ.get("RECORD_OUT")
kept, not_kept = [], []
for key, cls in sorted(lib.available().items()):
    try:
        tree = record(cls)
    except NotRecordable as e:
        not_kept.append((key, str(e)))
        continue
    kept.append((key, len(tree["ops"])))
    if out:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, f"{key}.json"), "w") as f:
            json.dump(tree, f, indent=1)

lines = [f"recorded {len(kept)} of {len(kept) + len(not_kept)}:"]
lines += [f"  {k}: {n} operations" for k, n in kept]
lines += ["not yet:"] + [f"  {k}: {why}" for k, why in not_kept]
os.write(1, ("\n".join(lines) + "\n").encode())
