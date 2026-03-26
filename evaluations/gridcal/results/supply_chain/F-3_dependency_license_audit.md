---
test_id: F-3
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "9f121feb"
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

# F-3: Dependency License Audit

## Result: PASS

## Finding

Of 62 installed packages, 2 use LGPL (weak copyleft) licenses: `chardet` (LGPL-2.1-or-later, direct dependency) and `moocore` (LGPL-2.1-or-later, transitive via pymoo). No AGPL, GPL, or other strong copyleft licenses were found. No proprietary or unknown licenses were identified. All remaining packages use permissive licenses (MIT, BSD, Apache-2.0, PSF, MPL-2.0).

**JLL binary artifact audit:** Not applicable. VeraGridEngine is a Python package; no Julia JLL packages are in the dependency tree.

## Evidence

**Complete license breakdown:**

| License | Count | Packages |
|---------|-------|----------|
| MIT | 24 | about-time, alive-progress, autograd, brotli, cffi, charset-normalizer, et_xmlfile, fonttools, geographiclib, geopy, graphemeu, highspy, iniconfig, openpyxl, platformdirs, pluggy, PuLP, pyparsing, pyproj, pytest, pytz, setuptools, urllib3, wheel |
| BSD (2/3-Clause) | 18 | cma, contourpy, cycler, h5py, idna, joblib, kiwisolver, networkx, numba, numpy, packaging, pandas, pycparser, pvlib, scikit-learn, threadpoolctl, wrapt, websockets |
| Apache-2.0 | 5 | opencv-python, pyarrow, pymoo, llvmlite (dual BSD-2/Apache-2.0+LLVM-exception), requests |
| MPL-2.0 | 2 | certifi, VeraGridEngine |
| LGPL-2.1-or-later | 2 | chardet (direct dep), moocore (transitive via pymoo) |
| PSF | 1 | matplotlib |
| MIT-CMU | 1 | Pillow |
| BSD + Dual | 1 | python-dateutil (BSD/Apache dual) |
| Pygments | 1 | BSD-2-Clause |
| Deprecated | 1 | MIT |
| windpowerlib | 1 | MIT |
| rdflib | 1 | BSD-3-Clause |
| scipy | 1 | BSD |
| xlrd | 1 | BSD |
| xlwt | 1 | BSD |

**Flagged packages (LGPL, weak copyleft):**

1. **chardet 6.0.0.post1** (LGPL-2.1-or-later): Character encoding detection. Direct dependency of veragridengine. Pure Python package. LGPL-2.1+ permits use as an imported library without triggering copyleft on the consuming application (no linking concerns for pure Python). Could be replaced with `charset-normalizer` (MIT) if LGPL avoidance is required.

2. **moocore 0.2.0** (LGPL-2.1-or-later): Multi-objective optimization core. Transitive dependency via pymoo. Contains 1 compiled .so extension (C code via cffi). Same LGPL considerations apply. Only exercised when using pymoo's multi-objective optimization features, which are not part of core power flow.

**No proprietary, GPL, AGPL, or unknown licenses found.**

## Implications

The dependency license profile is largely permissive. The two LGPL packages are low risk: chardet is pure Python (no linking concern), and moocore is a transitive dependency of pymoo that most power flow use cases do not exercise. If strict LGPL avoidance is required, chardet could be replaced with charset-normalizer (MIT), and pymoo could be made an optional dependency. Neither LGPL package poses a practical barrier to enterprise adoption when consumed as a library. No strong copyleft licenses were found.
