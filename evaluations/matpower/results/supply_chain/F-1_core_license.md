---
test_id: F-1
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: 8014315c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-1: Core License

## Result: PASS

## Finding

MATPOWER 8.1 is licensed under the 3-clause BSD license, a permissive open-source license with no copyleft or proprietary restrictions. The license is clearly stated in the root `LICENSE` file and covers all core source code. Case data files are explicitly noted as not covered by the BSD license (separate permissions or public-source data).

## Evidence

- **License file:** `matpower8.1/LICENSE`
- **License type:** BSD 3-Clause
- **Copyright holder:** Power Systems Engineering Research Center (PSERC) and individual contributors, 1996-2025
- **Copyleft flag:** No
- **Proprietary flag:** No
- **Full text excerpt:** "The code in MATPOWER is distributed under the 3-clause BSD license below. The MATPOWER case files distributed with MATPOWER are not covered by the BSD license."
- **Source:** GitHub repository at https://github.com/MATPOWER/matpower (accessed 2026-03-14)

## Implications

BSD 3-Clause is one of the most permissive OSS licenses available. It permits commercial use, modification, and redistribution with minimal restrictions (attribution only). No supply chain risk from the core license.
