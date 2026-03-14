---
test_id: F-2
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "d87fa2a9"
timestamp: "2026-03-13T23:00:00Z"
---

# F-2: Dependency Tree

## Finding

VeraGridEngine 5.6.28 installs 62 packages (including itself). It declares 28 direct dependencies in its metadata, several of which are heavy scientific computing packages with deep transitive dependency trees and compiled extensions.

## Evidence

**Direct dependencies (from package metadata):** 28 declared requirements

| Category | Dependencies |
|----------|-------------|
| Core scientific | numpy>=2.2.0, scipy>=1.0.0, pandas>=2.2.3, scikit-learn>=1.5.0 |
| Optimization | highspy>=1.8.0, pulp>=3.3.0 |
| Numerics | autograd>=1.7.0, numba>=0.61 |
| Graph/network | networkx>=2.1 |
| Geospatial | geopy>=1.16, pyproj |
| Visualization | matplotlib>=3.10.0 |
| I/O formats | openpyxl>=2.4.9, xlwt>=1.3.0, xlrd>=1.1.0, chardet>=3.0.4, h5py>=3.12.0, pyarrow>=15, rdflib |
| Domain-specific | windpowerlib>=0.2.2, pvlib>=0.11 |
| Multi-objective | pymoo>=0.6 |
| Computer vision | opencv-python>=4.10.0.84 |
| Build/test | setuptools>=41.0.1, wheel>=0.37.2, pytest>=7.2 |
| Communication | websockets, brotli |
| Optional | tables (extra: gch5-files) |

**Total installed packages:** 62

**Notable dependency characteristics:**
- **Heavy packages:** numpy, scipy, pandas, scikit-learn, numba/llvmlite, pyarrow, opencv-python, h5py, matplotlib are all large packages with compiled C/C++/Fortran extensions
- **Unusual for power systems:** `opencv-python` (computer vision), `windpowerlib` and `pvlib` (renewable energy), `pymoo` (multi-objective optimization) are not typical power flow dependencies
- **Dependency depth:** 2-3 levels typical (e.g., veragridengine -> scipy -> numpy; veragridengine -> matplotlib -> pillow -> packaging)

**Package sizes (approximate, by .so count):**

| Package | Compiled Extensions |
|---------|-------------------|
| scipy | 109 .so files |
| scikit-learn | 69 |
| pandas | 45 |
| h5py | 25 |
| pyarrow | 24 |
| numpy | 19 |
| numba | 14 |
| pyproj | 10 |
| matplotlib | 8 |
| PIL/Pillow | 8 |
| pymoo | 7 |

## Implications

The dependency count of 62 is moderate, but the inclusion of heavy compiled packages (scipy, scikit-learn, numba, opencv-python) significantly increases the supply chain surface area. Several dependencies (opencv-python, windpowerlib, pvlib, pymoo) appear to be application-level features rather than core power flow requirements, suggesting the package bundles domain-specific capabilities that not all users need. This monolithic packaging approach increases install size and attack surface for users who only need power flow functionality.
