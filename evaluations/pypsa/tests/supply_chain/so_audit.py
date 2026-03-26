"""Audit compiled .so extensions for F-4."""

import importlib.metadata as md
import sys

dists = list(md.distributions())
seen = set()
so_counts = {}
for d in dists:
    name = d.metadata["Name"]
    if name in seen:
        continue
    seen.add(name)
    if d.files:
        so_files = [str(f) for f in d.files if str(f).endswith(".so")]
        if so_files:
            so_counts[name] = len(so_files)

with open("/tmp/so_audit.txt", "w") as f:
    for name, count in sorted(so_counts.items()):
        f.write(f"{name}: {count} .so files\n")
    f.write(f"\nTotal: {sum(so_counts.values())} .so files across {len(so_counts)} packages\n")

sys.stdout.flush()
