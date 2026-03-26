---
test_id: F-1
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
protocol_version: "v11"
skill_version: "v2"
test_hash: "17f3907c"
---

# F-1: Core Package License

## Result: INFORMATIONAL

## Finding

pandapower is licensed under the BSD License (permissive, OSI-approved). No copyleft
obligations. No proprietary components. Full commercial use permitted.

## Evidence

- **Package:** pandapower 3.4.0
- **PyPI classifier:** `License :: OSI Approved :: BSD License`
- **License-Expression metadata:** `BSD` (confirmed via `importlib.metadata` in devcontainer,
  2026-03-24)
- **Copyright holders:** University of Kassel and Fraunhofer Institute for Energy Economics
  and Energy System Technology (IEE), Kassel
- **Source file headers** contain:
  > Copyright (c) 2016-2026 by University of Kassel and Fraunhofer Institute for Energy
  > Economics and Energy System Technology (IEE), Kassel. All rights reserved.
- **Home page:** https://www.pandapower.org
- **Source:** https://github.com/e2nIEE/pandapower

BSD is a permissive, OSI-approved license permitting commercial use, modification, and
redistribution with minimal restrictions (attribution in source/binary distributions).

## Implications

- **License type:** BSD (permissive)
- **Copyleft:** No
- **Proprietary components:** None
- **Commercial use:** Permitted without restriction
- **Legal review required:** No

No supply chain risk from the core package license.
