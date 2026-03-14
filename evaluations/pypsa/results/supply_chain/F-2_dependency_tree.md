---
test_id: F-2
tool: pypsa
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 8b638f83
---

# F-2: Dependency Tree

## Findings

### Direct Dependencies

PyPSA v1.1.2 declares 17 direct runtime dependencies in `pyproject.toml`:

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

**90 unique packages** installed in the evaluation environment (including
pypsa itself, dev dependencies pytest, and tool dependencies pandapower,
matpowercaseframes, pyomo used for evaluation).

PyPSA's own transitive closure (excluding evaluation-only packages):
approximately **70 packages**.

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
| Cloud | google-cloud-storage, google-auth | GCS integration (via linopy) |
| Utility | deprecation, validators, levenshtein | API helpers |

### Notable Observations

1. **Google Cloud dependencies**: linopy pulls in `google-cloud-storage`
   and its transitive chain (~8 packages). These are runtime dependencies
   for cloud-based model storage but not needed for local execution.

2. **Visualization weight**: matplotlib, plotly, seaborn, and pydeck
   collectively add ~15 packages. These are not needed for headless
   computation but are declared as required dependencies (not optional).

3. **Version pinning**: Dependencies use lower bounds only (e.g.,
   `pandas>=2.0`, `linopy>=0.6.1`) with one exclusion (`netcdf4!=1.7.4`
   due to a known bug). No upper bounds, which maximizes compatibility
   but risks breakage from upstream changes (as seen with pandas 3.0
   issues in #1580).

### Issues

No unresolvable dependencies. All packages resolve cleanly via pip/uv.
The lack of upper bounds is a minor supply chain concern — the pandas 3.0
breakage in issue #1580 demonstrates the risk.

## Recorded Metrics

- dep_count: ~70 (pypsa transitive), ~90 (full evaluation env)
- tree_depth: 4
- issues: no upper bounds on most dependencies; google-cloud chain pulled
  transitively via linopy
