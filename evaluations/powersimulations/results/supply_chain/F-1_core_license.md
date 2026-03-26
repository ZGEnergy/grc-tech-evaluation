---
test_id: F-1
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "64a1874e"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# F-1: Core License

## Result: INFORMATIONAL — All Permissive (BSD-3-Clause)

## Finding

PowerSimulations.jl and all companion Sienna ecosystem packages are licensed under the BSD 3-Clause License. This is a permissive open-source license with no copyleft obligations. The copyright holder is "Alliance for Sustainable Energy, LLC and The Regents of the University of California" (NREL's managing entity). No proprietary, copyleft, or otherwise problematic licenses were found in the core Sienna packages.

## Evidence

### PowerSimulations.jl

- **License:** BSD 3-Clause
- **Copyright:** 2018, 2023 Alliance for Sustainable Energy, LLC and The Regents of the University of California
- **Source:** `LICENSE` file in repo root, verified via `gh api repos/NREL-Sienna/PowerSimulations.jl`
- **GitHub API SPDX:** `BSD-3-Clause`

### Companion Sienna Packages

| Package | GitHub Repo | License (SPDX) | Verified |
|---------|-------------|-----------------|----------|
| PowerSystems.jl | NREL-Sienna/PowerSystems.jl | BSD-3-Clause | GitHub API |
| PowerFlows.jl | NREL-Sienna/PowerFlows.jl | BSD-3-Clause | GitHub API |
| PowerNetworkMatrices.jl | NREL-Sienna/PowerNetworkMatrices.jl | BSD-3-Clause | GitHub API |
| InfrastructureSystems.jl | NREL-Sienna/InfrastructureSystems.jl | BSD-3-Clause | GitHub API |

All five Sienna packages share the same BSD-3-Clause license from the same copyright holder.

### License Permissions

BSD-3-Clause permits:
- Commercial use
- Modification
- Distribution
- Private use

Conditions:
- Retain copyright notice in source distributions
- Retain copyright notice in binary distributions
- Do not use copyright holder names for endorsement without permission

No copyleft, no patent grant, no network-use (AGPL-style) clauses.

### Data Source

- `gh api repos/NREL-Sienna/PowerSimulations.jl` — `.license.spdx_id` = `BSD-3-Clause` (accessed 2026-03-24)

## Implications

1. **No license risk for the core tool:** BSD-3-Clause is one of the most permissive OSS licenses. It imposes no obligations beyond attribution.
2. **Consistent licensing across ecosystem:** All five Sienna packages use the same license, eliminating license interaction complexity within the core stack.
3. **DOE/national lab provenance:** The U.S. Government retains certain rights under the DOE contract, but this does not restrict commercial use by third parties under the BSD terms.
4. **Gate criterion status:** F-1 is a gate criterion. PowerSimulations.jl passes cleanly with no copyleft or proprietary encumbrances in the core packages. (Note: dependency licenses are assessed separately in F-3.)
