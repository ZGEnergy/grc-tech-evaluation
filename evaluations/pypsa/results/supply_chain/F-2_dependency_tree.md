---
test_id: F-2
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 8b638f83
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-2: Dependency Tree

## Result: INFORMATIONAL

## Finding

PyPSA v1.1.2 has 17 direct runtime dependencies and approximately 88 total packages in the evaluation environment (including evaluation-only packages). Maximum dependency tree depth is 4.

## Evidence

### Direct Dependencies (from PyPSA metadata)

17 direct runtime dependencies declared:

1. numpy
2. scipy
3. pandas (>=2.0)
4. xarray
5. netcdf4 (!=1.7.4)
6. linopy (>=0.6.1)
7. matplotlib
8. plotly
9. pydeck (>=0.6)
10. seaborn
11. geopandas (>=0.9)
12. shapely
13. networkx (>=2)
14. deprecation
15. validators
16. highspy
17. levenshtein (>=0.27.1)

### Total Dependency Count

**88 unique packages** in the evaluation environment (via `importlib.metadata.distributions()`). This includes evaluation-only packages (pandapower, matpowercaseframes, pyomo, pytest). PyPSA's own transitive closure is approximately 70 packages.

### Tree Depth

**Maximum depth: 4** (e.g., pypsa -> linopy -> dask -> partd -> locket).

### Dependency Categories

| Category | Packages | Purpose |
|----------|----------|---------|
| Core computation | numpy, scipy, pandas, xarray | Numerical/data |
| Optimization | linopy, highspy | LP/MILP modeling and solving |
| Visualization | matplotlib, plotly, seaborn, pydeck | Plotting |
| Geospatial | geopandas, shapely, pyproj, pyogrio | GIS/mapping |
| IO | netcdf4, xarray | File format support |
| Graph | networkx | Topology |
| Cloud | google-cloud-storage, google-auth (via linopy) | GCS integration |
| Utility | deprecation, validators, levenshtein | API helpers |

### Version Pinning

Dependencies use lower bounds only (e.g., `pandas>=2.0`, `linopy>=0.6.1`) with one exclusion (`netcdf4!=1.7.4`). No upper bounds are specified. This maximizes compatibility but risks breakage from upstream changes.

### Notable Observations

1. **Google Cloud chain**: linopy pulls in `google-cloud-storage` and ~8 transitive packages. Not needed for local computation.
2. **Visualization weight**: matplotlib, plotly, seaborn, pydeck add ~15 packages. Not needed for headless computation but declared as required.
3. **No unresolvable deps**: All packages resolve cleanly via uv/pip.

## Implications

The dependency tree is moderately sized for a Python scientific package. The lack of upper bounds is a minor reproducibility concern. The mandatory visualization and cloud dependencies increase the install footprint but do not affect computational correctness.
