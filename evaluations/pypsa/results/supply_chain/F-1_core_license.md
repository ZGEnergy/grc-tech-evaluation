---
test_id: F-1
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: c0a27872
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-1: Core License

## Result: PASS

## Finding

PyPSA v1.1.2 is licensed under the **MIT License** (permissive, OSI-approved). No copyleft or proprietary restrictions on the core package.

## Evidence

- **Package metadata** (`importlib.metadata`): `License: MIT License`
- **PyPI classifiers**: `License :: OSI Approved :: MIT License`
- **`pyproject.toml`**: `license = { file = "LICENSE" }` with MIT classifier
- **GitHub repository**: LICENSE file contains standard MIT text with copyright held by "PyPSA Contributors"
- **SPDX headers**: Source files contain `SPDX-License-Identifier: MIT`

### License Flags

| Flag | Status |
|------|--------|
| Copyleft | No |
| Proprietary | No |
| Commercial use | Permitted without restriction |
| Modification | Permitted without restriction |
| Distribution | Permitted with attribution (copyright notice) |

### Note on Dependency Chain

While PyPSA itself is MIT, the `levenshtein` direct dependency is GPL-2.0-or-later (see F-3 for full analysis). This creates a potential copyleft propagation concern in the dependency chain but does not affect the core package license classification.

## Implications

MIT license is fully compatible with commercial deployment, redistribution, and modification. No supply chain license risk from the core package itself.
