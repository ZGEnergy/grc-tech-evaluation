---
test_id: F-7
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "49227e98"
timestamp: "2026-03-13T23:00:00Z"
---

# F-7: Air-Gap Installability

## Finding

Air-gap installation is feasible but requires significant effort due to 62 packages with 360 compiled extensions across platform-specific binaries. The pure-Python nature of VeraGridEngine itself simplifies the core package, but its heavy compiled dependencies (scipy, numpy, numba, scikit-learn, opencv-python, pyarrow, h5py) make offline wheel bundling a multi-platform challenge.

## Evidence

**Total packages required:** 62 (including VeraGridEngine)

**Packages with compiled extensions (require platform-specific wheels):**

| Package | .so Files | Wheel Availability |
|---------|-----------|-------------------|
| scipy | 109 | manylinux, macOS, Windows wheels on PyPI |
| scikit-learn | 69 | manylinux, macOS, Windows wheels on PyPI |
| pandas | 45 | manylinux, macOS, Windows wheels on PyPI |
| h5py | 25 | manylinux, macOS wheels; Windows may need HDF5 lib |
| pyarrow | 24 | manylinux, macOS, Windows wheels on PyPI |
| numpy | 19 | manylinux, macOS, Windows wheels on PyPI |
| numba/llvmlite | 14+1 | manylinux, macOS, Windows wheels; llvmlite requires LLVM |
| pyproj | 10 | manylinux, macOS wheels; bundles PROJ library |
| matplotlib | 8 | manylinux, macOS, Windows wheels on PyPI |
| Pillow | 8 | manylinux, macOS, Windows wheels on PyPI |
| pymoo | 7 | manylinux wheels on PyPI |
| highspy | 1 | manylinux, macOS, Windows wheels on PyPI |
| opencv-python | 2 | manylinux, macOS, Windows wheels on PyPI |

**Air-gap installation procedure:**

1. On an internet-connected machine:
   ```bash
   pip download veragridengine --dest ./offline-packages/ --platform manylinux2014_x86_64 --python-version 3.12
   ```
2. Transfer `offline-packages/` to air-gapped system
3. Install: `pip install --no-index --find-links ./offline-packages/ veragridengine`

**Complications:**
- **VeraGridEngine is sdist-only** on PyPI (no wheels), so the air-gapped system needs build tools (setuptools, wheel) or the sdist must be pre-built on the connected system
- **llvmlite** requires LLVM shared libraries at runtime; the wheel bundles these but they are platform-specific
- **pyproj** bundles PROJ data files; the wheel is ~20 MB
- **opencv-python** is ~60 MB and pulls in system libraries (libGL, etc.)
- **Total download size estimate:** ~500-700 MB for the full wheel bundle (one platform)

**Dependency reduction potential:**
Many dependencies are not required for core power flow. An air-gap-optimized installation could potentially exclude: opencv-python, windpowerlib, pvlib, pymoo, scikit-learn, h5py, pyarrow, matplotlib, rdflib, websockets, brotli. This would reduce the package count from 62 to approximately 25-30 and eliminate many compiled extensions.

## Implications

Air-gap installation is achievable but operationally heavy. The 62-package, 360-compiled-extension footprint requires careful platform targeting and substantial transfer bandwidth (~500-700 MB). The monolithic packaging of VeraGridEngine (no optional dependency groups for core vs. full features) means the air-gap bundle must include all dependencies even if only DCPF/DCOPF functionality is needed. A `veragridengine[core]` extra would significantly improve air-gap feasibility.
