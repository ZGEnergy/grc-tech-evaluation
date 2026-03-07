---
test_id: F-7
tool: pypsa
dimension: supply_chain
slug: airgap_installability
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# F-7: Air-gap Installability

## Summary

| Metric | Value |
|--------|-------|
| Total packages | 90 |
| Pure Python (wheel-only, no compiled code) | 63 |
| Packages with compiled extensions (.so/.pyd) | 27 |
| All packages available as wheels on PyPI | Yes |
| Runtime network access required | No (optional, gated by config) |

## Offline Installation Feasibility

### Package Download

All 90 packages in the PyPSA dependency tree are available on PyPI as pre-built wheels for Linux x86_64 (manylinux). An air-gapped installation can be prepared with:

```bash
uv pip download pypsa --dest ./offline-wheels --python-version 3.12 --platform manylinux2014_x86_64
```

Or equivalently with pip:

```bash
pip download pypsa -d ./offline-wheels --platform manylinux2014_x86_64 --python-version 3.12
```

The resulting wheel bundle can then be installed in the air-gapped environment:

```bash
uv pip install --no-index --find-links ./offline-wheels pypsa
```

### Compiled Extensions

27 packages contain compiled C/C++/Rust extensions distributed as platform-specific wheels:

| Package | Extension Type | Platform Wheels Available |
|---------|---------------|-------------------------|
| numpy, scipy, pandas | C/Fortran | linux, macOS, Windows |
| highspy | C++ (HiGHS solver) | linux, macOS, Windows |
| shapely, pyproj, pyogrio | GEOS/PROJ/GDAL C libs | linux, macOS, Windows |
| cryptography | Rust + C (OpenSSL) | linux, macOS, Windows |
| cffi, pycparser | C | linux, macOS, Windows |
| polars, polars-runtime-32 | Rust | linux, macOS, Windows |
| RapidFuzz, Levenshtein | C++ | linux, macOS, Windows |
| Others (contourpy, cftime, etc.) | C/C++ | linux, macOS, Windows |

All of these publish pre-built wheels for major platforms. No source-only (sdist-only) packages that would require a compiler in the target environment.

### Runtime Network Access

PyPSA has three code paths that access the network at runtime, all optional:

1. **Version check** (`pypsa.common`): Queries GitHub API for latest release. Gated by `pypsa.options.set_option("general.allow_network_requests", False)`. Disabled by default in recent versions.

2. **Example network loading** (`pypsa.examples`): Downloads example .nc files from GitHub. Only triggered when calling `pypsa.examples.*()` functions. Not needed for production use.

3. **Network import from URL** (`pypsa.network.io`): Uses `urlretrieve` to download network files from URLs. Only triggered when a URL string is passed to `Network()` constructor instead of a local path.

None of these paths are required for core functionality (power flow, optimization, I/O from local files).

### System-Level Dependencies

The geospatial stack (shapely, pyproj, pyogrio) bundles its C library dependencies (GEOS, PROJ, GDAL) inside the wheels. No system package installation is required beyond Python itself.

The HiGHS solver is also bundled inside the `highspy` wheel.

## Assessment

**PASS** -- PyPSA and all 90 dependencies can be fully installed offline using pre-downloaded wheels. No source compilation is required in the target environment. Runtime network access is entirely optional and can be disabled via configuration. The tool is fully functional in an air-gapped environment for all production use cases (power flow, optimization, I/O from local files).
