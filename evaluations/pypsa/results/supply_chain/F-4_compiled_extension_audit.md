---
test_id: F-4
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 03ce9dd3
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

# F-4: Compiled Extension Audit (compiled_extension_audit)

## Result: PASS

## Finding

248 `.so` files are present in the venv; all belong to well-known open-source packages with publicly available source code. The critical PyPSA-specific compiled extension is `highspy/_core.cpython-312-x86_64-linux-gnu.so` (HiGHS C++ solver binding). PyPSA itself has no compiled extensions — it is pure Python.

## Evidence

**Total compiled extensions:**
```bash
find /workspace/evaluations/pypsa/.venv -name '*.so' | wc -l
→ 248
```

**Key compiled extensions by package:**

| Package | .so file | Source Available? | License |
|---------|----------|------------------|---------|
| highspy | `_core.cpython-312-x86_64-linux-gnu.so` | Yes — https://github.com/ERGO-Code/HiGHS | MIT |
| numpy | Multiple `_core/*.so` (BLAS/LAPACK bindings) | Yes — https://github.com/numpy/numpy | BSD |
| scipy | `scipy.libs/libscipy_openblas-b75cc656.so` | Yes — https://github.com/scipy/scipy | BSD |
| shapely | `lib.cpython-312-x86_64-linux-gnu.so` (GEOS binding) | Yes — https://github.com/shapely/shapely | BSD |
| pyproj | Multiple `.so` (PROJ binding) | Yes — https://github.com/pyproj4/pyproj | MIT |
| netCDF4 | `_netCDF4.abi3.so` | Yes — https://github.com/Unidata/netcdf4-python | MIT |
| cftime | `_cftime.cpython-312-x86_64-linux-gnu.so` | Yes | MIT |
| cryptography | `_rust.abi3.so` (Rust extension) | Yes — https://github.com/pyca/cryptography | Apache/BSD |
| rapidfuzz | Multiple `.so` (C++ string matching) | Yes — https://github.com/maxbachmann/RapidFuzz | MIT |
| bottleneck | Multiple `.so` (NumPy acceleration) | Yes — https://github.com/pydata/bottleneck | BSD |
| numexpr | `interpreter.cpython-312-x86_64-linux-gnu.so` | Yes | MIT |
| contourpy | `_contourpy.cpython-312-x86_64-linux-gnu.so` | Yes | BSD |

**PyPSA core:** Pure Python — no `.so` files in the `pypsa/` package directory itself. All computation delegated to numpy/scipy/linopy/highspy.

**HiGHS solver inspection:**
- `highspy/_core.cpython-312-x86_64-linux-gnu.so` is a pybind11 wrapper around the HiGHS C++ LP/MILP solver
- Source: https://github.com/ERGO-Code/HiGHS (MIT licensed)
- Build system: CMake + pybind11, fully reproducible from source
- The HiGHS C++ solver itself (libhighs) is statically linked into the `.so`; no runtime shared library dependencies beyond system libc

**No opaque binaries found.** All `.so` files trace to well-known open-source projects with public repositories, documented build systems, and permissive licenses.

## Implications

The compiled extension audit raises no concerns. The most critical extension (highspy) is the HiGHS solver — the source is publicly available and MIT licensed. PyPSA's design as pure Python with delegated computation makes the source inspection chain straightforward. No proprietary or obscure binary blobs are present.
