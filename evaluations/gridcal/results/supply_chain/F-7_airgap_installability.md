---
test_id: F-7
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "49227e98"
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

# F-7: Air-Gap Installability

## Result: PASS

## Finding

Air-gap installation is feasible but requires significant effort due to 62 packages with compiled extensions across 25 dependency packages. VeraGridEngine itself is pure Python (no compiled code), simplifying the core package. Its heavy compiled dependencies (scipy, numpy, numba, scikit-learn, opencv-python, pyarrow, h5py) require platform-specific wheel bundling. No runtime network access is required for core power flow functionality.

## Evidence

**Offline installation procedure:**

1. On an internet-connected machine (matching target platform):
   ```bash
   pip download veragridengine --dest ./offline-packages/ \
       --platform manylinux2014_x86_64 --python-version 3.12
   ```
2. Transfer `offline-packages/` directory to air-gapped system
3. Install: `pip install --no-index --find-links ./offline-packages/ veragridengine`

**Complications:**
- VeraGridEngine is **sdist-only** on PyPI, so building requires setuptools/wheel on the target or pre-building the sdist into a wheel on the connected machine
- 25 packages require platform-specific compiled wheels (see F-4)
- Estimated total download size: ~500-700 MB for the full wheel bundle (single platform)

**Packages with compiled extensions requiring platform-specific wheels:**

| Package | Wheel Availability (PyPI) |
|---------|--------------------------|
| scipy | manylinux, macOS, Windows |
| scikit-learn | manylinux, macOS, Windows |
| pandas | manylinux, macOS, Windows |
| numpy | manylinux, macOS, Windows |
| h5py | manylinux, macOS |
| pyarrow | manylinux, macOS, Windows |
| numba/llvmlite | manylinux, macOS, Windows |
| highspy | manylinux, macOS, Windows |
| opencv-python | manylinux, macOS, Windows |
| pyproj | manylinux, macOS |

All major compiled dependencies publish pre-built wheels for common platforms on PyPI.

**Runtime network access:**
- Core power flow, OPF, and analysis functions: **no network access required**
- `VeraGridEngine/IO/veragrid/remote.py` contains a `RemoteInstruction` class using `requests` for VeraGrid Server communication, but this is optional and guarded by `REQUESTS_AVAILABLE` flag
- `websockets` dependency supports VeraGrid Server functionality, not core analysis
- No telemetry, license validation, or phone-home behavior detected

**Dependency reduction potential:**
Many dependencies are not required for core power flow: opencv-python, windpowerlib, pvlib, pymoo, scikit-learn, h5py, pyarrow, matplotlib, rdflib, websockets, brotli. Excluding these would reduce the package count to ~25-30 and significantly reduce the compiled extension footprint.

## Implications

Air-gap installation is achievable for all common platforms (Linux x86_64, macOS, Windows). The main friction is the large wheel bundle size (~500-700 MB) and the need to target the correct platform for 25 compiled packages. The lack of optional dependency groups means the air-gap bundle must include all 62 packages even if only DCPF/DCOPF is needed. No runtime network access is required for power flow functionality.
