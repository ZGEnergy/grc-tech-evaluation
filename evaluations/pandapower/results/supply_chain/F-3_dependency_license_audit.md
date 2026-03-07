---
test_id: F-3
tool: pandapower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# F-3: Dependency License Audit

## Result: PASS

## Finding

All direct and transitive runtime dependencies are released under permissive, OSI-approved
licenses. No copyleft, proprietary, or unknown-license packages were found. The two weakest
copyleft licenses present are MPL-2.0 (LightSim2Grid, tqdm) which is file-level copyleft
only and does not infect downstream works.

## Evidence

### Full license inventory

| Package | Version | License | Category |
|---------|---------|---------|----------|
| pandapower | 3.4.0 | BSD-3-Clause | Permissive |
| pandas | 2.3.3 | BSD-3-Clause | Permissive |
| numpy | 2.3.5 | BSD-3-Clause | Permissive |
| scipy | 1.16.3 | BSD-3-Clause | Permissive |
| networkx | 3.6.1 | BSD-3-Clause | Permissive |
| packaging | 25.0 | Apache-2.0 / BSD | Permissive |
| tqdm | 4.67.3 | MPL-2.0 AND MIT | Weak copyleft (file-level) |
| deepdiff | 8.6.1 | MIT | Permissive |
| geojson | 3.2.0 | BSD | Permissive |
| typing_extensions | 4.15.0 | PSF-2.0 | Permissive |
| pandera | 0.26.1 | MIT | Permissive |
| pydantic | 2.12.5 | MIT | Permissive |
| pydantic_core | 2.41.5 | MIT | Permissive |
| annotated-types | 0.7.0 | MIT | Permissive |
| python-dateutil | 2.9.0.post0 | Apache-2.0 / BSD | Permissive |
| pytz | 2026.1.post1 | MIT | Permissive |
| tzdata | 2025.3 | Apache-2.0 | Permissive |
| six | 1.17.0 | MIT | Permissive |
| orderly-set | 5.5.0 | MIT | Permissive |
| immutabledict | 4.3.1 | MIT | Permissive |
| typeguard | 4.5.1 | MIT | Permissive |
| typing-inspect | 0.9.0 | MIT | Permissive |
| typing-inspection | 0.4.2 | MIT | Permissive |
| mypy_extensions | 1.1.0 | MIT | Permissive |
| Pygments | 2.19.2 | BSD-2-Clause | Permissive |
| **Performance extras** | | | |
| LightSim2Grid | 0.12.2 | MPL-2.0 | Weak copyleft (file-level) |
| numba | 0.64.0 | BSD-2-Clause | Permissive |
| llvmlite | 0.46.0 | BSD-2-Clause + Apache-2.0 w/ LLVM exception | Permissive |
| ortools | 9.15.6755 | Apache-2.0 | Permissive |
| absl-py | 2.4.0 | Apache-2.0 | Permissive |
| protobuf | 6.33.5 | BSD-3-Clause | Permissive |
| pybind11 | 3.0.2 | BSD-3-Clause | Permissive |
| matpowercaseframes | 2.0.1 | MIT | Permissive |

### License resolution methodology

Licenses marked "UNKNOWN" in the legacy `License` metadata field were resolved via the
`License-Expression` SPDX field (PEP 639), which all affected packages populate correctly.

### Copyleft assessment

- **MPL-2.0** (LightSim2Grid, tqdm): File-level copyleft. Modifications to the MPL-licensed
  source files themselves must be shared, but MPL does not require disclosure of the larger
  work. No impact on proprietary downstream use.
- No GPL, LGPL, AGPL, or SSPL licenses present.

## Implications

The entire dependency tree is clear for use in proprietary and commercial contexts. The two
MPL-2.0 packages are optional performance extras and impose only file-level copyleft
obligations that do not propagate to consuming code. No flags raised.
