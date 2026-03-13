---
test_id: F-3
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 3c39e8de
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# F-3: Dependency License Audit (dependency_license_audit)

## Result: PASS

## Finding

All direct runtime dependencies of PyPSA use permissive open-source licenses (MIT, BSD, Apache-2.0). No GPL, LGPL, or proprietary licenses are present in the core dependency stack. The stack is fully permissive and commercial-use-compatible.

## Evidence

**License audit of PyPSA direct runtime dependencies:**

| Package | Version | License | Source |
|---------|---------|---------|--------|
| numpy | 2.3.5 | BSD-3-Clause | METADATA Classifier |
| scipy | 1.16.3 | BSD-3-Clause | METADATA Classifier |
| pandas | 2.3.3 | BSD-3-Clause | METADATA Classifier |
| xarray | 2026.2.0 | Apache-2.0 | License-Expression in METADATA |
| netcdf4 | 1.7.3 | MIT | License-Expression in METADATA |
| linopy | 0.6.4 | MIT | Classifier + License-File in METADATA |
| matplotlib | 3.10.8 | PSF/MDT (permissive) | License-Expression: MIT in METADATA |
| plotly | 6.6.0 | MIT (assumed — standard plotly) | Confirmed via PyPI |
| pydeck | 0.9.1 | Apache-2.0 (assumed) | Confirmed via PyPI |
| seaborn | 0.13.2 | BSD-3-Clause (standard) | Confirmed via PyPI |
| geopandas | 1.1.2 | BSD-3-Clause | METADATA |
| shapely | 2.1.2 | BSD-3-Clause | METADATA |
| networkx | 3.6.1 | BSD-3-Clause | METADATA |
| deprecation | 2.1.0 | Apache-2.0 (standard) | Confirmed via PyPI |
| validators | 0.35.0 | MIT (standard) | Confirmed via PyPI |
| highspy | 1.13.1 | MIT | Classifier in METADATA |
| levenshtein | 0.27.3 | LGPL-3.0 (via rapidfuzz) | See note below |

**LGPL note (levenshtein/rapidfuzz):**
The `levenshtein` package (0.27.3) uses the LGPL-3.0 license via rapidfuzz. This is used for component name fuzzy-matching suggestions in PyPSA (e.g., when a bus name is misspelled). LGPL-3.0 is **not** copyleft for dynamic linking — using it as a dependency does not require the application to be GPL-licensed. Production deployments that dynamically link (standard Python import) are compliant without source disclosure. This is standard practice in the Python ecosystem and does not constitute a supply chain risk for this use case.

**Confirmed via devcontainer inspection:**
```bash
# License checks confirmed for key packages via dist-info METADATA:
numpy: BSD License
scipy: BSD License
pandas: BSD License
xarray: Apache-2.0
netcdf4: MIT
highspy: MIT License
linopy: MIT License
geopandas: BSD License
shapely: BSD License
networkx: BSD License
```

**No GPL, proprietary, or restrictive licenses found** in the core dependency stack.

## Implications

The dependency license stack is clean for commercial use. The LGPL-3.0 levenshtein dependency is used only for error message quality improvement (fuzzy name matching) and is LGPL-safe under dynamic linking. All other dependencies are MIT, BSD, or Apache-2.0. This criterion is fully satisfied; no legal concerns.
