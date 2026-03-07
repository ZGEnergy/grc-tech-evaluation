---
test_id: F-2
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-2: Dependency License Audit

## Criteria

Audit all direct and transitive runtime dependencies for license compatibility and
identify any copyleft, proprietary, or problematic licenses.

## Result: PASS

All 83 packages (29 direct + transitive) are open-source under permissive or weak-copyleft
licenses. No proprietary or strong-copyleft (GPL) dependencies found.

### License Breakdown

| License | Count | Examples |
|---------|-------|----------|
| MIT | ~30 | numba, highspy, websockets, geopy |
| BSD (2/3-clause) | ~25 | numpy, scipy, pandas, scikit-learn, matplotlib |
| Apache-2.0 | ~10 | pyarrow, rdflib, pvlib |
| MPL-2.0 | 1 | veragridengine (core) |
| LGPL-2.1/3.0 | 1 | chardet |
| PSF/Python | ~5 | setuptools, typing-extensions |
| Other permissive | ~11 | PIL/Pillow (HPND), unlicense |

### Risk Items

- **chardet (LGPL-2.1)**: Used for character encoding detection. LGPL requires either
  dynamic linking (satisfied by Python imports) or offering source. Low risk but should
  be documented in any license compliance report.
- **opencv-python (Apache-2.0)**: License is clean but the dependency itself is unusual
  for a power systems tool and inflates the supply chain surface.

### Evidence

All license metadata verified via PyPI classifier fields and individual package LICENSE
files. No packages use GPL-2.0, AGPL, SSPL, or any network-copyleft license.
