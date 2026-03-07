---
test_id: F-3
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-3: Compiled Extensions

## Criteria

Determine whether the tool ships compiled (binary) extensions and whether full source
code is available for audit of all executable components.

## Result: PASS

The core VeraGridEngine package is **100% pure Python**. All 866 source files are `.py`
files. Zero `.so`, `.pyd`, or `.dll` files ship in the package.

### Evidence

- File inventory of installed `veragridengine` package: 866 `.py` files, 0 compiled
  extension modules
- numba performs JIT compilation at runtime from Python source -- no pre-compiled
  opaque binaries
- Power flow execution path is fully traceable through Python source:
  `vge.power_flow()` -> `PowerFlowDriver.run()` -> `compile_numerical_circuit_at()`
  -> `NumericalCircuit` -> `scipy.sparse.linalg.spsolve()`

### Dependency Compiled Extensions

Several dependencies do ship compiled extensions (numpy, scipy, numba LLVM, opencv).
All of these are widely-used open-source packages with publicly available source code
and reproducible build pipelines:

| Package | Extension Type | Source Available |
|---------|---------------|-----------------|
| numpy | C/Fortran `.so` | Yes (github.com/numpy/numpy) |
| scipy | C/Fortran/Cython `.so` | Yes (github.com/scipy/scipy) |
| numba | LLVM-based `.so` | Yes (github.com/numba/numba) |
| opencv-python | C++ `.so` | Yes (github.com/opencv/opencv) |
| highspy | C++ `.so` | Yes (github.com/ERGO-Code/HiGHS) |

No dependency ships proprietary or source-unavailable binaries.
