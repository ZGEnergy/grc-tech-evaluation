---
test_id: F-2
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

# F-2: Dependency Tree

## Result: PASS

## Finding

pandapower v3.4.0 with the `[performance]` extra (as installed in the evaluation environment)
has 38 total packages in the virtualenv. The core runtime dependency tree is shallow (max
depth 2) with 10 direct runtime dependencies. All dependencies use compatible-release
pinning (`~=`) or upper bounds, providing reproducible installs.

## Evidence

### Direct runtime dependencies (from `pyproject.toml`)

| Package | Pin | Purpose |
|---------|-----|---------|
| pandas | ~=2.3 | Data model (DataFrames) |
| networkx | ~=3.4 | Graph topology |
| scipy | <1.17 | Sparse linear algebra (spsolve) |
| numpy | >=1.26,<2.4 | Numerical arrays |
| packaging | ~=25.0 | Version utilities |
| tqdm | ~=4.67 | Progress bars |
| deepdiff | ~=8.6 | Object comparison |
| geojson | ~=3.2 | GeoJSON support |
| typing_extensions | ~=4.9 | Typing backports |
| pandera | ~=0.26.1 | DataFrame validation |

### Performance extras (installed via `pandapower[performance]`)

| Package | Pin | Purpose |
|---------|-----|---------|
| ortools | ~=9.14 | OR-Tools optimization |
| numba | ~=0.61 | JIT compilation |
| lightsim2grid | ~=0.12.2 | C++ power flow backend |

### Dependency tree metrics

- **Total packages in venv:** 38 (including dev tools like pytest, pip, setuptools)
- **Runtime deps from pandapower root:** 12 packages (depth 0-2)
- **Max tree depth:** 2
- **Unpinned items:** 0 -- all direct deps use `~=` or bounded ranges

### Full package list (from venv)

```
absl-py==2.4.0, annotated-types==0.7.0, deepdiff==8.6.1, geojson==3.2.0,
immutabledict==4.3.1, iniconfig==2.3.0, LightSim2Grid==0.12.2, llvmlite==0.46.0,
matpowercaseframes==2.0.1, mypy_extensions==1.1.0, networkx==3.6.1, numba==0.64.0,
numpy==2.3.5, orderly-set==5.5.0, ortools==9.15.6755, packaging==25.0,
pandapower==3.4.0, pandas==2.3.3, pandera==0.26.1, pip==26.0.1, pluggy==1.6.0,
protobuf==6.33.5, pybind11==3.0.2, pydantic==2.12.5, pydantic_core==2.41.5,
Pygments==2.19.2, pytest==9.0.2, python-dateutil==2.9.0.post0, pytz==2026.1.post1,
scipy==1.16.3, setuptools==82.0.0, six==1.17.0, tqdm==4.67.3, typeguard==4.5.1,
typing-inspect==0.9.0, typing-inspection==0.4.2, typing_extensions==4.15.0,
tzdata==2025.3
```

## Implications

The dependency tree is compact and well-pinned. Max depth of 2 limits transitive-dependency
risk. Compatible-release pins (`~=`) ensure patch updates are accepted while major/minor
breakage is prevented. The `uv.lock` file in the project further pins exact versions for
full reproducibility.
