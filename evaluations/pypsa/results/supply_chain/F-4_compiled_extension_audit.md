---
test_id: F-4
tool: pypsa
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-4: Compiled Extension Audit

## Finding

The PyPSA environment contains 248 compiled shared object (.so) files across 25 packages. All are standard scientific Python ecosystem components distributed as pre-built wheels from PyPI. Source code is available for all compiled extensions.

## Evidence

Compiled extensions found via scanning site-packages for `.so` files:

**In the critical execution path (power system modeling + optimization):**

| Package | .so count | Role | Source available |
|---------|-----------|------|-----------------|
| highspy | 1 | HiGHS solver bindings | Yes (C++, MIT) |
| numpy | 10 | Numerical arrays | Yes (C, BSD-3) |
| scipy | 60+ | Scientific computing, sparse matrices | Yes (C/Fortran, BSD-3) |
| pandas | 30+ | DataFrames (Cython) | Yes (Cython, BSD-3) |
| shapely | 3 | Geometry (GEOS bindings) | Yes (C++, BSD-3) |
| pyproj | 10 | Map projections (PROJ bindings) | Yes (C, MIT) |
| pyogrio | 5 | Geospatial I/O (GDAL bindings) | Yes (C++, MIT) |

**Supporting packages (visualization, I/O, etc.):**

| Package | .so count | Role |
|---------|-----------|------|
| matplotlib | 8 | Plotting |
| PIL/Pillow | 9 | Image processing |
| contourpy | 1 | Contouring |
| fonttools | 6 | Font handling |
| kiwisolver | 1 | Constraint solving (matplotlib) |
| netCDF4 | 1 | NetCDF I/O |
| cftime | 1 | Time handling |
| pydantic-core | 1 | Validation (Rust) |
| polars | 1 | DataFrames (Rust, via pandapower) |
| Levenshtein | 1 | String matching (C++) |
| rapidfuzz | 8 | String matching (C++) |
| bottleneck | 4 | NumPy acceleration |
| numexpr | 1 | Expression evaluation |
| cffi | 1 | C FFI |
| cryptography | 1 | Crypto (Rust) |
| markupsafe | 1 | String escaping |
| pyyaml | 1 | YAML parsing |
| charset-normalizer | 2 | Encoding detection |
| google protobuf | 1 | Serialization |
| google-crc32c | 1 | CRC32C |

**Key observations:**
1. **PyPSA itself is pure Python** (distributed as `py3-none-any.whl` -- no compiled code)
2. **linopy is pure Python** (no .so files)
3. All compiled extensions come from well-established, widely-used scientific Python packages
4. All are distributed as manylinux/macOS/Windows wheels on PyPI
5. All have source code available on GitHub with standard build systems (meson, setuptools, CMake)
6. No proprietary or closed-source compiled components

## Implications

The compiled extension footprint is typical for scientific Python projects. No custom or unusual compiled code exists. All compiled components are from the standard scientific Python stack with full source availability. The most critical compiled component for this evaluation is **highspy** (HiGHS solver bindings), which is MIT-licensed with full C++ source available. Qualified pass due to the large number of compiled extensions (248), but all are well-established and inspectable.
