---
test_id: F-4
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 8868c3f4
---

# F-4: Compiled Extension Audit

## Findings

### PyPSA Core

PyPSA itself is **pure Python** with zero compiled extensions. All `.py`
source files are inspectable and modifiable.

### Compiled Components in Execution Path

The following packages in PyPSA's dependency chain contain compiled
(`.so`) extensions:

| Package | Compiled Extensions | Source Available | Buildable | Role in PyPSA |
|---------|-------------------|-----------------|-----------|---------------|
| numpy | 19 .so files | Yes (GitHub) | Yes (C/Fortran) | Core array operations |
| scipy | 114 .so files | Yes (GitHub) | Yes (C/Fortran/Cython) | Sparse linear algebra (spsolve) |
| highspy | 1 .so file | Yes (GitHub) | Yes (C++) | HiGHS LP/MILP solver |
| shapely | 3 .so files | Yes (GitHub) | Yes (C, wraps GEOS) | Geospatial operations |
| Levenshtein | 1 .so file | Yes (GitHub) | Yes (C++) | String matching |
| rapidfuzz | 8 .so files | Yes (GitHub) | Yes (C++) | Fuzzy string matching |
| netCDF4 | 1 .so file | Yes (GitHub) | Yes (C, wraps HDF5/netCDF) | File I/O |
| pyproj | 10 .so files | Yes (GitHub) | Yes (C, wraps PROJ) | Coordinate transforms |
| pyogrio | 5 .so files | Yes (GitHub) | Yes (C, wraps GDAL) | Geospatial I/O |

### Critical Path Analysis

For the core power-system computation path (`n.lpf()` and `n.optimize()`),
only three compiled libraries are in the critical execution path:

1. **numpy** — array operations (BSD, fully open-source, buildable)
2. **scipy** — `scipy.sparse.linalg.spsolve()` for DCPF B-matrix solve
   (BSD, fully open-source, buildable)
3. **highspy** — HiGHS solver for OPF (MIT, fully open-source, buildable)

The geospatial packages (shapely, pyproj, pyogrio) are only invoked for
plotting and GIS operations, not for power-system computation.

### Source Availability

All compiled dependencies have source code available on GitHub under
permissive licenses. All are buildable from source on standard Linux
platforms with common build tools (gcc, gfortran, cmake).

### Assessment

No proprietary or opaque compiled components in the execution path. All
compiled extensions serve well-known numerical/scientific computing roles
with mature, auditable source code.

## Recorded Metrics

- compiled_components: 9 packages with .so files
- source_available: yes (all)
- buildable: yes (all, from public GitHub repos with standard build tools)
