"""License audit script for F-2 and F-3."""

import importlib.metadata as md
import sys

dists = list(md.distributions())
seen = set()
results = []
for d in dists:
    name = d.metadata["Name"]
    if name in seen:
        continue
    seen.add(name)
    version = d.metadata["Version"]
    lic = (d.metadata.get("License", "") or "")[:80].replace("\n", " ")
    lic_expr = d.metadata.get("License-Expression", "") or ""
    classifiers = [c for c in (d.metadata.get_all("Classifier") or []) if "License" in c]
    cls_short = classifiers[0][:80] if classifiers else ""
    effective = lic_expr or lic or cls_short or "UNKNOWN"
    results.append((name, version, effective))

results.sort(key=lambda x: x[0].lower())

with open("/tmp/license_audit.txt", "w") as f:
    f.write(f"Total packages: {len(results)}\n\n")
    for name, ver, eff in results:
        f.write(f"{name}=={ver} | {eff}\n")

sys.stdout.write(f"Wrote {len(results)} entries to /tmp/license_audit.txt\n")
sys.stdout.flush()
