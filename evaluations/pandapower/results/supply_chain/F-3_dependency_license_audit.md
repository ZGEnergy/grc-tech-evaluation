---
test_id: F-3
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "c28ae2f3"
---

# F-3: Dependency License Audit

## Method

Ran `pip-licenses --format=json --with-urls` inside the devcontainer to extract license metadata for all installed packages.

## License Summary by Type

| License Type | Count | Packages |
|-------------|-------|----------|
| BSD (2/3-Clause) | 14 | pandapower, numpy, scipy, pandas, numba, networkx, geojson, Pygments, protobuf, pybind11, pyomo, llvmlite, packaging, python-dateutil |
| MIT | 14 | deepdiff, immutabledict, iniconfig, matpowercaseframes, mypy_extensions, orderly-set, pluggy, pydantic, pydantic_core, pytz, six, typeguard, typing-inspect, typing-inspection |
| Apache 2.0 | 4 | absl-py, ortools, tzdata, packaging (dual) |
| MPL 2.0 | 1 | LightSim2Grid |
| MPL 2.0 + MIT | 1 | tqdm |
| PSF 2.0 | 1 | typing_extensions |
| BSD + Apache | 1 | llvmlite (dual: BSD-2-Clause AND Apache-2.0 WITH LLVM-exception) |

## Copyleft / Restrictive License Analysis

### LightSim2Grid -- MPL 2.0

- **License:** Mozilla Public License 2.0
- **Implication:** MPL 2.0 is a weak copyleft license. It requires that modifications to MPL-licensed *files* be released under MPL 2.0, but does not impose copyleft on the larger work. Code that merely links to or imports LightSim2Grid is not affected.
- **Source:** https://github.com/grid2op/lightsim2grid/ (open source, C++ with Python bindings)
- **Risk level:** Low. MPL 2.0 is OSI-approved and compatible with proprietary use. No legal review required for typical usage (importing the library). Legal review would only be needed if modifying LightSim2Grid source files.
- **Note:** LightSim2Grid is an optional performance dependency (`pandapower[performance]`). pandapower functions without it, falling back to its own pure-Python/NumPy/SciPy Newton-Raphson solver.

### tqdm -- MPL 2.0 + MIT

- **License:** Dual-licensed MPL 2.0 and MIT
- **Implication:** Users may choose either license. MIT is fully permissive.
- **Risk level:** None (choose MIT)

## No Proprietary, GPL, or AGPL Dependencies Found

All 37 packages use permissive or weak-copyleft licenses. No GPL, LGPL, AGPL, or proprietary licenses detected.

## Assessment

- **Dominant license family:** BSD/MIT (permissive) -- 29 of 37 packages
- **Weak copyleft:** 1 package (LightSim2Grid, MPL 2.0) -- optional performance dependency
- **Proprietary:** None
- **GPL/AGPL:** None

**Grade: A-** -- Fully permissive dependency tree except for one optional weak-copyleft dependency (LightSim2Grid, MPL 2.0). The MPL 2.0 license is file-level copyleft only and does not restrict the larger work. If LightSim2Grid is excluded (by not installing the `[performance]` extra), the entire tree is permissive.
