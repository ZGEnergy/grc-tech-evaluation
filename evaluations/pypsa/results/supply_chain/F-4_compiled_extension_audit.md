---
test_id: F-4
tool: pypsa
dimension: supply_chain
slug: compiled_extension_audit
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# F-4: Compiled Extension Audit

## Summary

Compiled shared libraries (.so files) were identified in the installed environment. PyPSA and Linopy themselves contain **zero** compiled extensions -- they are pure Python. Compiled code exists only in well-known, open-source numerical and geospatial dependencies.

## Compiled Extension Inventory

| Package | .so Count | Language | Source Available | Buildable from Source |
|---------|-----------|----------|-----------------|----------------------|
| **numpy** (2.3.5) | 19 | C/Cython | Yes (GitHub, PyPI sdist) | Yes |
| **scipy** (1.16.3) | 114 | C/C++/Fortran/Cython | Yes (GitHub, PyPI sdist) | Yes |
| **pandas** (2.3.3) | 44 | Cython | Yes (GitHub, PyPI sdist) | Yes |
| **highspy** (1.13.1) | 1 | C++ (HiGHS solver) | Yes (GitHub: ERGO-Code/HiGHS) | Yes |
| **shapely** (2.1.2) | 3 | C++ (GEOS bindings) | Yes (GitHub) | Yes |
| **pyproj** (3.7.2) | 10 | Cython (PROJ bindings) | Yes (GitHub) | Yes |
| **pyogrio** (0.12.1) | 5 | Cython (GDAL/OGR bindings) | Yes (GitHub) | Yes |
| **pypsa** (1.1.2) | 0 | N/A | N/A | N/A |
| **linopy** (0.6.4) | 0 | N/A | N/A | N/A |

## Critical Path Analysis

The optimization execution path `n.optimize() -> linopy -> highspy -> HiGHS` involves exactly **one** compiled binary: `highspy/_core.cpython-312-x86_64-linux-gnu.so`, which wraps the HiGHS C++ solver. The HiGHS source code is fully available at <https://github.com/ERGO-Code/HiGHS> under the MIT license and is buildable from source via CMake.

The numerical foundations (numpy, scipy, pandas) are industry-standard packages with well-documented build processes. All use open-source compilers (gcc/gfortran) and their source code is available via both GitHub and PyPI sdist archives.

## Geospatial Extensions (Non-Critical Path)

shapely (GEOS), pyproj (PROJ), and pyogrio (GDAL/OGR) are geospatial libraries used only for visualization (`n.plot()`, `n.explore()`). They are not in the optimization or power flow execution path. All are open-source with buildable source code.

## Assessment

**PASS** -- No opaque binary blobs. All compiled extensions have publicly available source code and are buildable from source. The critical optimization path has minimal compiled surface area (a single HiGHS .so file). PyPSA and linopy themselves are pure Python.
