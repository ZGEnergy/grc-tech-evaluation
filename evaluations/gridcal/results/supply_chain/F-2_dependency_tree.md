---
test_id: F-2
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "d87fa2a9"
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

# F-2: Dependency Tree

## Result: PASS

## Finding

VeraGridEngine 5.6.28 installs 62 packages (including itself). It declares 28 direct dependencies. The maximum dependency tree depth is 4 (veragridengine -> windpowerlib -> requests -> urllib3 -> backports_zstd). No unresolvable dependencies were found.

## Evidence

**Direct dependencies (28):** setuptools, wheel, numpy, autograd, scipy, networkx, pandas, highspy, xlwt, xlrd, matplotlib, openpyxl, chardet, scikit-learn, geopy, pytest, h5py, numba, pyproj, pulp, pyarrow, windpowerlib, pvlib, rdflib, pymoo, websockets, brotli, opencv-python.

**Dependency categorization:**

| Category | Dependencies |
|----------|-------------|
| Core scientific | numpy>=2.2.0, scipy>=1.0.0, pandas>=2.2.3, scikit-learn>=1.5.0 |
| Optimization | highspy>=1.8.0, pulp>=3.3.0 |
| Numerics/JIT | autograd>=1.7.0, numba>=0.61 |
| Graph/network | networkx>=2.1 |
| Geospatial | geopy>=1.16, pyproj |
| Visualization | matplotlib>=3.10.0 |
| I/O formats | openpyxl>=2.4.9, xlwt>=1.3.0, xlrd>=1.1.0, chardet>=3.0.4, h5py>=3.12.0, pyarrow>=15, rdflib |
| Domain-specific | windpowerlib>=0.2.2, pvlib>=0.11 |
| Multi-objective | pymoo>=0.6 |
| Computer vision | opencv-python>=4.10.0.84 |
| Build/test | setuptools>=41.0.1, wheel>=0.37.2, pytest>=7.2 |
| Communication | websockets, brotli |

**Tree metrics:**
- Total packages installed: 62
- Direct dependencies: 28
- Maximum tree depth: 4
- Unresolvable dependencies: 0

**Notable characteristics:**
- Heavy compiled dependencies: numpy, scipy, pandas, scikit-learn, numba/llvmlite, pyarrow, opencv-python, h5py, matplotlib
- Non-core dependencies: opencv-python (computer vision), windpowerlib and pvlib (renewable energy), pymoo (multi-objective optimization) are not required for basic power flow
- The package has no optional dependency groups (`extras_require`), so all 28 direct deps are mandatory

## Implications

The dependency count of 62 is moderate for a scientific Python package. The monolithic packaging (no optional extras for core vs. full features) means all dependencies are installed even if only DCPF/DCOPF is needed. Several dependencies (opencv-python, windpowerlib, pvlib, pymoo) serve application-level features rather than core power flow, increasing the supply chain surface area unnecessarily for users who need only grid analysis functionality.
