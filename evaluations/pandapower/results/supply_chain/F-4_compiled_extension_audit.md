---
test_id: F-4
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
protocol_version: "v11"
skill_version: "v2"
test_hash: "13233460"
---

# F-4: Compiled Extension Audit

## Result: INFORMATIONAL

## Finding

pandapower's virtualenv contains 216 shared object (.so) files. All compiled components
in the power flow execution path have publicly available source code. No opaque or
source-unavailable binaries exist in the dependency tree.

## Evidence

### Method

Enumerated all `.so` files in the devcontainer virtualenv via `find .venv/lib -name "*.so"`
(2026-03-24). Classified each by package, role in the power flow execution path, source
availability, and license.

### Tier 1: Directly in the Power Flow Solve Path

| Package | Key .so Files | Language | Source Available | License |
|---------|--------------|----------|-----------------|---------|
| **scipy** | `sparse/linalg/_dsolve/_superlu.cpython-312-x86_64-linux-gnu.so` | C/Fortran | Yes (GitHub) | BSD |
| **scipy** | `sparse/_sparsetools.cpython-312-x86_64-linux-gnu.so` | C++ | Yes (GitHub) | BSD |
| **scipy** | `scipy.libs/libscipy_openblas-b75cc656.so` | C/Fortran | Yes (OpenBLAS GitHub) | BSD |
| **numpy** | `_core/_multiarray_umath.cpython-312-x86_64-linux-gnu.so` | C | Yes (GitHub) | BSD |
| **numpy** | `linalg/_umath_linalg.cpython-312-x86_64-linux-gnu.so` | C | Yes (GitHub) | BSD |
| **LightSim2Grid** | `lightsim2grid_cpp.cpython-312-x86_64-linux-gnu.so` | C++ (pybind11) | Yes (GitHub) | MPL 2.0 |

`scipy.sparse.linalg.spsolve` (SuperLU sparse LU factorization) is the critical solve
step in `dcpf()`. LightSim2Grid is an optional alternative C++ Newton-Raphson solver for
AC power flow.

### Tier 2: Performance Acceleration (Not in Critical Solve Path)

| Package | Key .so Files | Language | Source Available | License |
|---------|--------------|----------|-----------------|---------|
| **numba** | `_dispatcher.so`, `_helperlib.so`, ~10 others | C/C++ | Yes (GitHub) | BSD |
| **llvmlite** | `libllvmlite.so` | C++ (LLVM) | Yes (GitHub) | BSD-2/Apache-2.0 |
| **pandas** | ~25 Cython `.so` files | Cython | Yes (GitHub) | BSD |
| **pydantic_core** | `_pydantic_core.cpython-312-x86_64-linux-gnu.so` | Rust | Yes (GitHub) | MIT |

### Tier 3: Not in Power Flow Path

| Package | .so Count | Language | Source Available | License |
|---------|-----------|----------|-----------------|---------|
| **ortools** | ~15 files | C++ | Yes (GitHub: google/or-tools) | Apache 2.0 |
| **protobuf** | 1 file | C++ | Yes (GitHub) | BSD-3 |
| **pyomo** | 1 file | C++ | Yes (GitHub) | BSD-3 |
| **scipy** (non-sparse) | ~80 files | C/Fortran | Yes (GitHub) | BSD |

### Summary Metrics

- **Total .so files:** 216
- **In execution path (Tier 1):** ~6 critical files
- **Performance acceleration (Tier 2):** ~40 files
- **Not in power flow path (Tier 3):** ~170 files

### Opaque Binary Assessment

**No opaque binaries detected.** Every compiled component has publicly available source
code on GitHub or equivalent repositories:

1. **scipy SuperLU** -- the actual linear system solver for DC power flow -- is a
   peer-reviewed sparse direct solver with full C/Fortran source.
2. **LightSim2Grid** -- the optional C++ AC PF accelerator -- has full source on GitHub.
3. **OpenBLAS** (`libscipy_openblas*.so`) -- prebuilt BLAS/LAPACK library shipped with
   scipy wheels. Source available (OpenBLAS GitHub). BSD licensed.
4. **pydantic_core** -- Rust compiled extension with full source on GitHub.

## Implications

All compiled extensions in the execution path have publicly available source code. The
critical solve path (scipy.sparse.linalg.spsolve -> SuperLU) uses well-established,
auditable open-source code. No proprietary or source-unavailable binaries exist in the
dependency tree. The supply chain is fully inspectable from a compiled-code perspective.
