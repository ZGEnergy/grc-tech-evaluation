---
test_id: F-4
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

# F-4: Compiled Extension Audit

## Result: PASS

## Finding

pandapower itself is pure Python with no compiled extensions. The `.so` files present in
the environment belong to its dependencies. All compiled extensions have source code
publicly available and are buildable from source.

## Evidence

### pandapower core

pandapower ships as a `py3-none-any` wheel -- pure Python, no compiled code. The bundled
PYPOWER module (`pandapower.pypower`) is also pure Python. The DC power flow solver uses
`scipy.sparse.linalg.spsolve` for the linear system solve.

### Compiled extensions by dependency

| Package | .so files | Source available | Build system |
|---------|-----------|-----------------|--------------|
| **LightSim2Grid** | `lightsim2grid_cpp.cpython-312-x86_64-linux-gnu.so` (3.0 MB) | Yes ([GitHub](https://github.com/BDonnot/lightsim2grid)) | C++/pybind11, CMake |
| **numba** | 12 `.so` files (JIT runtime, ufunc pools) | Yes ([GitHub](https://github.com/numba/numba)) | C/C++/Cython |
| **llvmlite** | `libllvmlite.so` | Yes ([GitHub](https://github.com/numba/llvmlite)) | C++, wraps LLVM |
| **numpy** | 8 `.so` files (core ufuncs, linalg, random) | Yes ([GitHub](https://github.com/numpy/numpy)) | C/Cython, Meson |
| **scipy** | ~60 `.so` files (linalg, sparse, optimize, etc.) | Yes ([GitHub](https://github.com/scipy/scipy)) | C/C++/Fortran/Cython, Meson |
| **pandas** | ~25 `.so` files (parsers, algos, tslibs) | Yes ([GitHub](https://github.com/pandas-dev/pandas)) | Cython, Meson |
| **ortools** | ~15 `.so` files (solver bindings) | Yes ([GitHub](https://github.com/google/or-tools)) | C++/pybind11, CMake |
| **pydantic_core** | `_pydantic_core.cpython-312-x86_64-linux-gnu.so` | Yes ([GitHub](https://github.com/pydantic/pydantic-core)) | Rust/PyO3 |
| **protobuf** | `_message.abi3.so` | Yes ([GitHub](https://github.com/protocolbuffers/protobuf)) | C++ |

### Critical path extensions

For the DC power flow execution path (`pp.rundcpp()`), the only compiled code invoked is:

1. **scipy** `spsolve` -- calls into LAPACK/SuperLU via scipy's Fortran/C extensions.
   Source is fully available. Bundled OpenBLAS (`libscipy_openblas-b75cc656.so`) is also
   open-source (BSD-3-Clause).
2. **numpy** array operations -- standard C extensions, fully open.

LightSim2Grid is an *optional* alternative backend. When active, it replaces the Python
Newton-Raphson with a C++ implementation. Source is available on GitHub under MPL-2.0.

### Buildability

All packages with compiled extensions provide sdist distributions on PyPI and/or build
instructions in their repositories. scipy and numpy bundle OpenBLAS as a vendored shared
library; this is also open-source and buildable from source.

## Implications

No opaque binary blobs in the execution path. All compiled code has publicly available
source and documented build procedures. The core power flow path can run entirely on
pure Python (pandapower + PYPOWER) with scipy as the only compiled dependency for
sparse linear algebra.
