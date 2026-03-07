---
test_id: F-1
tool: pypsa
dimension: supply_chain
slug: core_license
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# F-1: Core License Audit

## Finding

PyPSA is licensed under the **MIT License** (SPDX: `MIT`).

- **PyPSA** (v1.1.2): MIT License
- **Linopy** (v0.6.4, optimization backend): MIT License
- **HiGHS** / **highspy** (v1.13.1, solver): MIT License

The entire core stack -- from the modeling layer through the optimization backend to the solver -- uses the MIT permissive license. There are no copyleft (GPL, LGPL, AGPL) or proprietary components in the critical execution path.

## Dependency License Summary

All 87 transitive dependencies use permissive licenses:
- MIT: majority of packages (pypsa, linopy, highspy, numpy, scipy, pandas, xarray, networkx, etc.)
- BSD-3-Clause: matplotlib, scipy, pandas
- Apache-2.0: google-* packages, requests, protobuf
- PSF: Python standard library extensions

No copyleft or proprietary licenses were identified in the dependency tree.

## Source

- PyPI: <https://pypi.org/project/pypsa/> (license field: MIT)
- GitHub: <https://github.com/PyPSA/PyPSA> (SPDX: MIT)
- Author contact: <t.brown@tu-berlin.de> (TU Berlin)

## Assessment

**PASS** -- MIT license throughout the stack. No copyleft contamination. No proprietary dependencies. Suitable for commercial use without license encumbrance.
