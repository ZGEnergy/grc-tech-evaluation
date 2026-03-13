---
test_id: F-2
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: e816cc39
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# F-2: Dependency Tree (dependency_tree)

## Result: PASS

## Finding

The `uv.lock` file resolves 89 packages. PyPSA's `pyproject.toml` lists 16 direct runtime dependencies, all unpinned (no version pins beyond the `>=` lower bounds specified by PyPSA itself). The `uv.lock` provides full pinned resolution for reproducibility.

## Evidence

**Total packages in lock file:**
```bash
grep '^\[\[package\]\]' /workspace/evaluations/pypsa/uv.lock | wc -l
→ 89
```

**PyPSA direct runtime dependencies** (from `pypsa-1.1.2.dist-info/METADATA`):
```
numpy, scipy, pandas>=2.0, xarray, netcdf4!=1.7.4, linopy>=0.6.1,
matplotlib, plotly, pydeck>=0.6, seaborn, geopandas>=0.9, shapely,
networkx>=2, deprecation, validators, highspy, levenshtein>=0.27.1
```

**Evaluation project `pyproject.toml` direct dependencies:**
```toml
dependencies = [
    "pypsa",          # unpinned — resolves to latest at uv sync time
    "pandapower",     # unpinned
    "matpowercaseframes",  # unpinned
    "highspy",        # unpinned
]
```

**Pinning status:**
- Evaluation `pyproject.toml`: no version pins (intentional for evaluation flexibility)
- `uv.lock`: all 89 packages are pinned with exact versions and SHA256 hashes
- PyPSA's own `pyproject.toml` uses `>=` lower bounds (e.g., `linopy>=0.6.1`, `pandas>=2.0`), not exact pins

**Key installed versions:**

| Package | Version |
|---------|---------|
| pypsa | 1.1.2 |
| linopy | 0.6.4 |
| highspy | 1.13.1 |
| numpy | 2.3.5 |
| pandas | 2.3.3 |
| scipy | 1.16.3 |
| networkx | 3.6.1 |
| xarray | 2026.2.0 |
| geopandas | 1.1.2 |
| netcdf4 | 1.7.3 |
| matplotlib | 3.10.8 |

**Notable optional dependencies present in install:**
- `pandapower` (3.4.0) — pulled in by evaluation project, not PyPSA core
- `dask` (2026.1.2) — pulled in transitively
- `google-cloud-storage` (3.9.0) — pulled in by pydeck/cloudpickle transitively

## Implications

89 packages is a moderate-sized dependency tree for a scientific Python tool. All packages resolve from PyPI. The lock file provides full reproducibility. The unpinned evaluation `pyproject.toml` is appropriate for the evaluation context; production deployments would want pinned versions. No concerns about dependency tree size or structure.
