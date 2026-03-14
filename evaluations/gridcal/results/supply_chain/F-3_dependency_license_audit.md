---
test_id: F-3
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "d65d77ee"
timestamp: "2026-03-13T23:00:00Z"
---

# F-3: Dependency License Audit

## Finding

Of 62 installed packages, 2 use LGPL (weak copyleft) licenses: `chardet` (LGPL-2.1+) and `moocore` (LGPL-2.1). No AGPL, GPL, or other strong copyleft licenses were found. The remainder use permissive licenses (MIT, BSD, Apache-2.0, PSF, MPL-2.0).

## Evidence

**License breakdown by category:**

| License | Count | Packages |
|---------|-------|----------|
| MIT | 22 | about-time, alive-progress, autograd, brotli, charset-normalizer, Deprecated, et_xmlfile, fonttools, geographiclib, geopy, graphemeu, openpyxl, pyparsing, pyproj, pytest, pytz, setuptools, six, urllib3, websockets, wheel, windpowerlib |
| BSD (2/3-Clause) | 16 | cma, contourpy, cycler, h5py, idna, joblib, kiwisolver, networkx, numba, numpy, pandas, pycparser, Pygments, rdflib, scikit-learn, scipy, threadpoolctl, wrapt, xlrd, xlwt |
| Apache-2.0 | 5 | opencv-python, packaging, pyarrow, pymoo, requests |
| MPL-2.0 | 2 | certifi, VeraGridEngine |
| LGPL-2.1+ | 1 | chardet |
| LGPL-2.1 | 1 | moocore (transitive dep of pymoo) |
| PSF | 1 | matplotlib |
| HPND/MIT-CMU | 1 | Pillow |
| BSD-2-Clause | 3 | llvmlite, PuLP, wrapt |
| Other/custom | 8 | cffi (MIT), iniconfig (MIT), pluggy (MIT), pvlib (BSD-3), pyproj (MIT), python-dateutil (BSD/Apache dual), highspy (MIT), platformdirs (MIT) |

**Flagged packages:**

1. **chardet** (LGPL-2.1+): Character encoding detection library. Used by VeraGridEngine for file format detection. LGPL-2.1+ requires dynamic linking or source provision if distributed as part of a proprietary application. However, since chardet is a pure Python package imported at runtime, typical Python usage satisfies LGPL requirements.

2. **moocore** (LGPL-2.1): Multi-objective optimization core library, transitive dependency of pymoo. Contains 1 compiled .so extension. Same LGPL considerations as chardet, plus the compiled extension adds a linking consideration.

**No strong copyleft (GPL, AGPL) licenses found in any dependency.**

## Implications

The dependency license profile is largely permissive. The two LGPL packages (chardet and moocore) are low-risk for typical use cases: chardet is pure Python, and moocore is a transitive dependency of pymoo (multi-objective optimization) that most power flow use cases may not exercise. If LGPL compliance is a concern, chardet could be replaced with `charset-normalizer` (MIT), and pymoo could potentially be made optional. Neither LGPL package poses a practical barrier to enterprise adoption when consumed as a library.
