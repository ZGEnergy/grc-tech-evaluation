---
test_id: F-2
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
test_hash: "a4e41898"
---

# F-2: Full Dependency Tree Enumeration

## Result: INFORMATIONAL

## Finding

pandapower's evaluation virtualenv contains 39 packages (excluding pip/setuptools). All
versions are deterministically pinned via `uv.lock`. The dependency tree is shallow
(max depth 3). The largest dependency by install size is Google OR-Tools.

## Evidence

### Method

Ran `uv run python -c "import importlib.metadata ..."` inside the devcontainer
(2026-03-24) to enumerate all installed packages.

### Full Installed Package List (39 packages)

| # | Package | Version | License | Role |
|---|---------|---------|---------|------|
| 1 | pandapower | 3.4.0 | BSD | Core |
| 2 | numpy | 2.3.5 | BSD | Numerical arrays |
| 3 | scipy | 1.16.3 | BSD | Sparse linear algebra, solvers |
| 4 | pandas | 2.3.3 | BSD | DataFrames |
| 5 | networkx | 3.6.1 | BSD-3 | Graph algorithms |
| 6 | numba | 0.64.0 | BSD | JIT compilation (performance extra) |
| 7 | llvmlite | 0.46.0 | BSD-2/Apache-2.0 w/ LLVM | LLVM backend for numba |
| 8 | LightSim2Grid | 0.12.2 | MPL-2.0 | C++ accelerated power flow (performance extra) |
| 9 | ortools | 9.15.6755 | Apache-2.0 | Google OR-Tools (optimization) |
| 10 | pyomo | 6.10.0 | BSD-3 | Optimization modeling |
| 11 | matpowercaseframes | 2.0.1 | MIT | MATPOWER .m file parser |
| 12 | deepdiff | 8.6.1 | MIT | Deep comparison utility |
| 13 | geojson | 3.2.0 | BSD | GeoJSON support |
| 14 | pandera | 0.26.1 | MIT | DataFrame validation |
| 15 | pydantic | 2.12.5 | MIT | Data validation |
| 16 | pydantic_core | 2.41.5 | MIT | Pydantic Rust core |
| 17 | pybind11 | 3.0.2 | BSD-3 | C++ binding headers |
| 18 | protobuf | 6.33.5 | BSD-3 | Protocol buffers (ortools dep) |
| 19 | absl-py | 2.4.0 | Apache-2.0 | Abseil Python (ortools dep) |
| 20 | tqdm | 4.67.3 | MPL-2.0/MIT | Progress bars |
| 21 | packaging | 25.0 | Apache-2.0 | Version parsing |
| 22 | typing_extensions | 4.15.0 | PSF-2.0 | Typing backports |
| 23 | annotated-types | 0.7.0 | MIT | Pydantic dep |
| 24 | immutabledict | 4.3.1 | MIT | Immutable dict |
| 25 | orderly-set | 5.5.0 | MIT | Ordered set (deepdiff dep) |
| 26 | mypy_extensions | 1.1.0 | MIT | Mypy typing |
| 27 | Pygments | 2.19.2 | BSD-2 | Syntax highlighting |
| 28 | python-dateutil | 2.9.0.post0 | BSD | Date utilities |
| 29 | pytz | 2026.1.post1 | MIT | Timezone data |
| 30 | tzdata | 2025.3 | Apache-2.0 | IANA timezone database |
| 31 | six | 1.17.0 | MIT | Python 2/3 compat |
| 32 | typeguard | 4.5.1 | MIT | Runtime type checking |
| 33 | typing-inspect | 0.9.0 | MIT | Typing introspection |
| 34 | typing-inspection | 0.4.2 | MIT | Typing inspection |
| 35 | iniconfig | 2.3.0 | MIT | Config parser (pytest dep) |
| 36 | pluggy | 1.6.0 | MIT | Plugin framework (pytest dep) |
| 37 | pytest | 9.0.2 | MIT | Testing framework (dev dep) |
| 38 | pip | 26.0.1 | MIT | Package installer |
| 39 | setuptools | 82.0.0 | MIT | Build system |

### Metrics

- **Total packages:** 39 (including pip/setuptools)
- **Direct pandapower dependencies:** deepdiff, geojson, networkx, numpy, packaging,
  pandas, pandera, scipy, tqdm, typing_extensions (10 packages)
- **Project-level extras:** pandapower[performance] (adds numba, LightSim2Grid),
  matpowercaseframes, pyomo
- **Max dependency depth:** 3 (pandapower -> pandera -> pydantic -> pydantic_core)
- **Pinning:** All versions locked via `uv.lock`; no unpinned dependencies
- **Notable large dependency:** ortools (9.15.6755) -- largest by install size, brings
  C++ compiled components and protobuf

## Implications

Moderate dependency count (39 packages). All versions are deterministically pinned. The
dependency tree is shallow (max depth 3). No orphaned or unmaintained packages observed.
The ortools dependency is large but well-maintained by Google. LightSim2Grid and numba are
optional performance extras that can be excluded without losing core functionality.
