---
test_id: F-4
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "42e7914a"
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T18:00:00Z"
---

# F-4: Compiled Extension Audit

## Result: PASS

## Finding

VeraGridEngine itself is 100% pure Python (Tag: `py3-none-any`) with zero compiled extensions. It uses numba `@njit` for JIT compilation of performance-critical numerical code (38 source files). The dependency tree contains compiled extensions across 25 packages, dominated by scipy, scikit-learn, pandas, h5py, pyarrow, and numpy. All compiled dependencies have publicly available source code.

## Evidence

**VeraGridEngine package:**
- Wheel tag: `py3-none-any` (pure Python, no compiled code)
- 0 `.so` or `.pyd` files in the VeraGridEngine package directory
- `Root-Is-Purelib: true` in WHEEL metadata
- 38 Python files reference numba (`@nb.njit`, `from numba`), producing JIT-compiled machine code at runtime

**Numba JIT usage (38 files), key modules:**
- `DataStructures/numerical_circuit.py` -- sparse matrix operations
- `Simulations/Derivatives/ac_jacobian.py`, `csc_derivatives.py`, `csr_derivatives.py` -- Jacobian computation
- `Simulations/PowerFlow/NumericalMethods/` -- Newton-Raphson, HELM, common functions
- `Simulations/LinearFactors/linear_analysis.py` -- PTDF/LODF computation
- `Simulations/OPF/NumericalMethods/newton_raphson_ips_fx.py` -- interior-point solver
- `Topology/admittance_matrices.py`, `topology.py` -- admittance matrix construction

**Dependency compiled extensions (25 packages with .so files):**

| Package | Source Available | License |
|---------|----------------|---------|
| scipy | Yes (github.com/scipy/scipy) | BSD |
| scikit-learn | Yes (github.com/scikit-learn/scikit-learn) | BSD-3-Clause |
| pandas | Yes (github.com/pandas-dev/pandas) | BSD-3-Clause |
| h5py | Yes (github.com/h5py/h5py) | BSD-3-Clause |
| pyarrow | Yes (github.com/apache/arrow) | Apache-2.0 |
| numpy | Yes (github.com/numpy/numpy) | BSD-3-Clause |
| numba | Yes (github.com/numba/numba) | BSD-2-Clause |
| llvmlite | Yes (github.com/numba/llvmlite) | BSD-2-Clause + Apache-2.0 |
| pyproj | Yes (github.com/pyproj4/pyproj) | MIT |
| matplotlib | Yes (github.com/matplotlib/matplotlib) | PSF |
| Pillow | Yes (github.com/python-pillow/Pillow) | MIT-CMU |
| pymoo | Yes (github.com/anyoptimization/pymoo) | Apache-2.0 |
| highspy | Yes (github.com/ERGO-Code/HiGHS) | MIT |
| opencv-python | Yes (github.com/opencv/opencv) | Apache-2.0 |
| moocore | Yes (github.com/multi-objective/moocore) | LGPL-2.1 |
| contourpy | Yes (github.com/contourpy/contourpy) | BSD-3-Clause |
| fontTools | Yes (github.com/fonttools/fonttools) | MIT |
| kiwisolver | Yes (github.com/nucleic/kiwi) | BSD |
| cffi | Yes (github.com/python-cffi/cffi) | MIT |
| charset_normalizer | Yes (github.com/Ousret/charset_normalizer) | MIT |
| brotli | Yes (github.com/google/brotli) | MIT |
| wrapt | Yes (github.com/GrahamDumpleton/wrapt) | BSD-2-Clause |
| websockets | Yes (github.com/python-websockets/websockets) | BSD-3-Clause |
| sklearn | (same as scikit-learn) | BSD-3-Clause |

**Key compiled components in the power flow execution path:**
1. **scipy.sparse.linalg.spsolve** -- sparse linear system solver (SuperLU), used for DCPF and Newton-Raphson
2. **numpy** -- array operations throughout all numerical code
3. **highspy** -- HiGHS LP/MILP solver for optimization
4. **numba/llvmlite** -- JIT compilation for performance-critical inner loops

All 25 packages with compiled extensions have source available on public GitHub repositories.

## Implications

The pure-Python nature of VeraGridEngine is a strong positive for inspectability -- all solver logic can be read and audited as Python source. The numba JIT compilation is auditable at the source level (decorated Python functions are readable) but produces opaque machine code at runtime. All compiled dependencies are well-known, widely-audited scientific computing packages with publicly available source code. No proprietary or source-unavailable compiled components were found.
