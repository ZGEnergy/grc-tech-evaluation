---
test_id: F-4
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "13233460"
---

# F-4: Compiled Extension Audit

## Method

Enumerated all `.so` (shared object) files in the pandapower virtualenv's site-packages directory. Classified each by package and role in the power flow execution path.

## Compiled Components in the Execution Path

### Tier 1: Directly in the power flow solve path

| Package | Key .so Files | Language | Source Available | License |
|---------|--------------|----------|-----------------|---------|
| **scipy** | `sparse/linalg/_dsolve/_superlu.so`, `sparse/_sparsetools.so`, `optimize/_highspy/_core.so` | C/C++/Fortran | Yes (GitHub) | BSD |
| **numpy** | `_core/_multiarray_umath.so`, `linalg/_umath_linalg.so` | C | Yes (GitHub) | BSD |
| **LightSim2Grid** | `lightsim2grid_cpp.so` | C++ (pybind11) | Yes (GitHub: grid2op/lightsim2grid) | MPL 2.0 |

**scipy.sparse.linalg.spsolve** is the critical solve step in `dcpf()`. It uses SuperLU (sparse LU factorization) which is compiled C/Fortran. Source is fully available.

**LightSim2Grid** provides an alternative C++ Newton-Raphson solver for AC power flow. It is optional -- pandapower falls back to pure Python/SciPy if not installed. Source is available on GitHub.

### Tier 2: Performance acceleration (not in critical solve path)

| Package | Key .so Files | Language | Source Available | License |
|---------|--------------|----------|-----------------|---------|
| **numba** | `_dispatcher.so`, `_helperlib.so`, plus ~10 others | C/C++ | Yes (GitHub) | BSD |
| **llvmlite** | `libllvmlite.so` | C++ (LLVM) | Yes (GitHub) | BSD-2/Apache-2.0 |
| **pandas** | ~25 Cython `.so` files | Cython | Yes (GitHub) | BSD |
| **pydantic_core** | `_pydantic_core.so` | Rust | Yes (GitHub) | MIT |

### Tier 3: Not in power flow path

| Package | Key .so Files | Language | Source Available | License |
|---------|--------------|----------|-----------------|---------|
| **ortools** | ~15 `.so` files (LP/MIP solvers, graph algorithms) | C++ | Yes (GitHub: google/or-tools) | Apache 2.0 |
| **protobuf** | `_message.abi3.so` | C++ | Yes (GitHub) | BSD |
| **pyomo** | `appsi_cmodel.so` | C++ | Yes (GitHub) | BSD |

## Total Compiled Object Count

- **Total .so files:** ~180
- **In execution path (Tier 1):** ~5 critical files
- **Performance acceleration (Tier 2):** ~40 files
- **Not in power flow path (Tier 3):** ~135 files

## Opaque Binary Assessment

**No opaque binaries detected.** Every compiled component has publicly available source code on GitHub or equivalent repositories. The key observations:

1. **scipy SuperLU** -- the actual linear system solver for DC power flow -- is a well-known, peer-reviewed sparse solver with full Fortran/C source available.
2. **LightSim2Grid** -- the optional C++ accelerator -- has full source on GitHub under MPL 2.0.
3. **numpy OpenBLAS** (`libscipy_openblas64_.so`) -- prebuilt BLAS/LAPACK library shipped with numpy wheels. Source available (OpenBLAS GitHub). BSD licensed.

## Assessment

All compiled extensions in the execution path have publicly available source code. The critical solve path (scipy.sparse.linalg.spsolve -> SuperLU) uses well-established, auditable open-source code. No proprietary or source-unavailable binaries exist in the dependency tree.
