---
test_id: F-4
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "42e7914a"
timestamp: "2026-03-13T23:00:00Z"
---

# F-4: Compiled Extension Audit

## Finding

VeraGridEngine itself is 100% pure Python with zero compiled extensions (.so/.pyd files). However, its dependency tree contains 360 compiled extension files across 20 packages, dominated by scipy (109), scikit-learn (69), pandas (45), h5py (25), pyarrow (24), and numpy (19).

## Evidence

**VeraGridEngine package:** 0 compiled extensions. All source is pure Python (.py files). The package uses numba's `@njit` decorator for JIT compilation of performance-critical numerical code (42 files reference numba), but this produces machine code at runtime rather than shipping pre-compiled binaries.

**Numba JIT usage in VeraGridEngine (42 files):**
- `Utils/Sparse/csc_numba.py` — sparse matrix operations
- `Utils/NumericalMethods/ips.py` — interior point solver
- `Utils/NumericalMethods/common.py` — shared numerical utilities
- `Utils/Symbolic/` — symbolic computation
- Various simulation modules

**Dependency compiled extensions (360 total .so files):**

| Package | .so Count | Language | Purpose |
|---------|-----------|----------|---------|
| scipy | 109 | C/C++/Fortran | Sparse solvers, linear algebra, optimization |
| scikit-learn | 69 | C++/Cython | Machine learning (used for clustering) |
| pandas | 45 | C/Cython | DataFrame operations |
| h5py | 25 | C | HDF5 file I/O |
| pyarrow | 24 | C++ | Arrow/Parquet I/O |
| numpy | 19 | C | Array operations, BLAS/LAPACK |
| numba | 14 | C++ | JIT compiler runtime |
| pyproj | 10 | C | Coordinate projections |
| matplotlib | 8 | C/C++ | Plotting backend |
| PIL/Pillow | 8 | C | Image processing |
| pymoo | 7 | C | Multi-objective optimization |
| fontTools | 6 | C | Font rendering |
| highspy | 1 | C++ | HiGHS LP/MIP solver |
| llvmlite | 1 | C++ | LLVM bindings for numba |
| opencv-python (cv2) | 2 | C++ | Computer vision |
| moocore | 1 | C | Multi-objective core |
| brotli | 1 | C | Compression |
| charset_normalizer | 2 | C | Encoding detection |
| wrapt | 1 | C | Function wrappers |
| scipy.libs | 1 | Fortran | BLAS/LAPACK shared libs |

**Key compiled components for power flow functionality:**
1. **scipy.sparse.linalg.spsolve** — used directly in DCPF (sparse linear system solver)
2. **numpy** — array operations throughout all numerical code
3. **highspy** — HiGHS solver for LP/MILP optimization
4. **numba/llvmlite** — JIT compilation for performance-critical inner loops

## Implications

The pure-Python nature of VeraGridEngine itself is a positive finding for inspectability — all solver logic can be read and audited as Python source. The numba JIT compilation adds a runtime compilation step that is auditable (the decorated Python source is visible) but produces opaque machine code at execution time. The compiled dependency footprint (360 .so files) is large but consists entirely of well-known, widely-audited scientific computing packages (numpy, scipy, pandas). The opencv-python dependency adds 2 compiled extensions that are unnecessary for power flow use cases.
