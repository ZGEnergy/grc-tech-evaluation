---
test_id: F-2
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "a4e41898"
---

# F-2: Full Dependency Tree Enumeration

## Method

Ran `uv run pip list --format=json` inside the devcontainer to enumerate all installed packages in the pandapower virtualenv. The project uses `uv.lock` for deterministic pinning.

## Direct Dependencies (from pyproject.toml)

1. `pandapower[performance]` -- core package with performance extras (numba, LightSim2Grid)
2. `matpowercaseframes` -- MATPOWER case file loader
3. `pyomo` -- optimization modeling (for OPF)

## pandapower's Own Direct Dependencies (from pip show)

deepdiff, geojson, networkx, numpy, packaging, pandas, pandera, scipy, tqdm, typing_extensions

## Full Installed Package List (37 packages, excluding pip/setuptools)

| # | Package | Version | Role |
|---|---------|---------|------|
| 1 | pandapower | 3.4.0 | Core |
| 2 | numpy | 2.3.5 | Numerical arrays |
| 3 | scipy | 1.16.3 | Sparse linear algebra, solvers |
| 4 | pandas | 2.3.3 | DataFrames |
| 5 | networkx | 3.6.1 | Graph algorithms |
| 6 | numba | 0.64.0 | JIT compilation (performance extra) |
| 7 | llvmlite | 0.46.0 | LLVM backend for numba |
| 8 | LightSim2Grid | 0.12.2 | C++ accelerated power flow (performance extra) |
| 9 | ortools | 9.15.6755 | Google OR-Tools (optimization) |
| 10 | pyomo | 6.10.0 | Optimization modeling |
| 11 | matpowercaseframes | 2.0.1 | MATPOWER .m file parser |
| 12 | deepdiff | 8.6.1 | Deep comparison utility |
| 13 | geojson | 3.2.0 | GeoJSON support |
| 14 | pandera | 0.26.1 | DataFrame validation |
| 15 | pydantic | 2.12.5 | Data validation |
| 16 | pydantic_core | 2.41.5 | Pydantic Rust core |
| 17 | pybind11 | 3.0.2 | C++ binding headers |
| 18 | protobuf | 6.33.5 | Protocol buffers (ortools dep) |
| 19 | absl-py | 2.4.0 | Abseil Python (ortools dep) |
| 20 | tqdm | 4.67.3 | Progress bars |
| 21 | packaging | 25.0 | Version parsing |
| 22 | typing_extensions | 4.15.0 | Typing backports |
| 23 | annotated-types | 0.7.0 | Pydantic dep |
| 24 | immutabledict | 4.3.1 | Immutable dict |
| 25 | orderly-set | 5.5.0 | Ordered set (deepdiff dep) |
| 26 | mypy_extensions | 1.1.0 | Mypy typing |
| 27 | Pygments | 2.19.2 | Syntax highlighting |
| 28 | python-dateutil | 2.9.0.post0 | Date utilities |
| 29 | pytz | 2026.1.post1 | Timezone data |
| 30 | tzdata | 2025.3 | IANA timezone database |
| 31 | six | 1.17.0 | Python 2/3 compat |
| 32 | typeguard | 4.5.1 | Runtime type checking |
| 33 | typing-inspect | 0.9.0 | Typing introspection |
| 34 | typing-inspection | 0.4.2 | Typing inspection |
| 35 | iniconfig | 2.3.0 | Config parser (pytest dep) |
| 36 | pluggy | 1.6.0 | Plugin framework (pytest dep) |
| 37 | pytest | 9.0.2 | Testing framework (dev dep) |

## Metrics

- **Total packages:** 37 (excluding pip/setuptools)
- **Direct dependencies:** 3 (project-level) + 10 (pandapower's own) = 13 unique direct
- **Max dependency depth:** 3 (e.g., pandapower -> pandera -> pydantic -> pydantic_core)
- **Pinning:** All versions locked via `uv.lock`; no unpinned dependencies
- **Notable large dependencies:** ortools (9.15.6755) is the largest by install size, brings C++ compiled components and protobuf

## Assessment

Moderate dependency count (37 packages). All versions are pinned via uv.lock. The dependency tree is shallow (max depth 3). The ortools dependency is large but well-maintained by Google. No orphaned or unmaintained packages observed.
