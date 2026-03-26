---
test_id: F-3
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
protocol_version: "v11"
skill_version: "v2"
test_hash: "16372443"
---

# F-3: Dependency License Audit

## Result: INFORMATIONAL

## Finding

All 39 packages in the pandapower dependency tree use permissive or weak-copyleft licenses.
No GPL, LGPL, AGPL, or proprietary licenses detected. One optional dependency
(LightSim2Grid) uses MPL 2.0 (weak copyleft, file-level only). No JLL binary artifacts
apply (Python tool, N/A).

## Evidence

### Method

Extracted license metadata via `importlib.metadata` for all installed packages in the
devcontainer (2026-03-24). Cross-referenced `License`, `License-Expression`, and
`Classifier` fields for each package.

### License Summary by Type

| License Type | Count | Packages |
|-------------|-------|----------|
| BSD (2/3-Clause) | 14 | pandapower, numpy, scipy, pandas, numba, networkx, geojson, Pygments, protobuf, pybind11, pyomo, python-dateutil, numba, geojson |
| MIT | 16 | deepdiff, immutabledict, iniconfig, matpowercaseframes, mypy_extensions, orderly-set, pluggy, pydantic, pydantic_core, pytz, six, typeguard, typing-inspect, typing-inspection, pip, setuptools |
| Apache 2.0 | 4 | absl-py, ortools, packaging, tzdata |
| MPL 2.0 | 1 | LightSim2Grid |
| MPL 2.0 + MIT (dual) | 1 | tqdm |
| PSF 2.0 | 1 | typing_extensions |
| BSD-2 + Apache-2.0 w/ LLVM-exception | 1 | llvmlite |
| MIT (dev/build) | 1 | pytest |

### Copyleft / Restrictive License Analysis

#### LightSim2Grid -- MPL 2.0

- **License:** Mozilla Public License 2.0
- **Implication:** MPL 2.0 is a weak copyleft license. It requires that modifications to
  MPL-licensed *files* be released under MPL 2.0, but does not impose copyleft on the
  larger work. Code that merely links to or imports LightSim2Grid is not affected.
- **Source:** https://github.com/Grid2op/lightsim2grid/ (open source, C++ with Python
  bindings)
- **Risk level:** Low. MPL 2.0 is OSI-approved and compatible with proprietary use. Legal
  review needed only if modifying LightSim2Grid source files.
- **Optionality:** LightSim2Grid is an optional performance dependency
  (`pandapower[performance]`). pandapower functions without it, falling back to its own
  pure-Python/NumPy/SciPy Newton-Raphson solver.

#### tqdm -- MPL 2.0 + MIT (dual)

- **License:** Dual-licensed MPL 2.0 and MIT
- **Implication:** Users may choose either license. MIT is fully permissive.
- **Risk level:** None (choose MIT)

### No Problematic Licenses Found

- **GPL/LGPL/AGPL:** None
- **Proprietary:** None
- **Non-commercial:** None
- **JLL binary artifacts:** N/A (Python tool, no Julia binary wrappers)

### Compiled Dependency License Verification

All compiled dependencies (scipy, numpy, LightSim2Grid, numba, llvmlite, ortools,
pydantic_core, pandas) have source code available on GitHub under their stated licenses.
No binary-only or source-unavailable compiled components detected.

## Implications

- **Dominant license family:** BSD/MIT (permissive) -- 31 of 39 packages
- **Weak copyleft:** 1 package (LightSim2Grid, MPL 2.0) -- optional performance dependency
- **Proprietary:** None
- **GPL/AGPL:** None

The dependency tree is clean from a licensing perspective. The only non-permissive license
is MPL 2.0 on an optional dependency, and it imposes file-level copyleft only. If
LightSim2Grid is excluded (by not installing the `[performance]` extra), the entire tree
is permissive.
