---
test_id: F-3
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-3: Dependency License Audit

## Method

Checked licenses of all direct dependencies and key transitive dependencies via GitHub API and upstream project documentation.

## Direct Dependency Licenses

| Package | License | Notes |
|---------|---------|-------|
| PowerSimulations.jl | BSD-3-Clause | NREL-Sienna |
| PowerSystems.jl | BSD-3-Clause | NREL-Sienna |
| InfrastructureSystems.jl | BSD-3-Clause | NREL-Sienna |
| PowerFlows.jl | BSD-3-Clause | NREL-Sienna |
| PowerNetworkMatrices.jl | BSD-3-Clause | NREL-Sienna |
| JuMP.jl | MPL-2.0 | Permissive with file-level copyleft |
| MathOptInterface.jl | MPL-2.0 | Core JuMP dependency |
| HiGHS.jl (wrapper) | MIT | jump-dev |
| GLPK.jl (wrapper) | MPL-2.0 | jump-dev |
| Ipopt.jl (wrapper) | MPL-2.0 | jump-dev |
| SCIP.jl (wrapper) | MIT | scipopt |
| DataFrames.jl | MIT | JuliaData |
| CSV.jl | MIT | JuliaData |

## Key Transitive / Compiled Library Licenses

| Library | License | Notes |
|---------|---------|-------|
| HiGHS (C++) | MIT | Open-source LP/MIP solver |
| SCIP (C) | Apache-2.0 | Since SCIP 8.0 (2022); previously ZIB Academic |
| Ipopt (C++) | EPL-2.0 | Eclipse Public License; weak copyleft, commercial-friendly |
| GLPK (C) | GPL-3.0 | **Copyleft** -- see note below |
| MUMPS (Fortran) | CeCILL-C | LGPL-compatible; used by Ipopt |
| METIS (C) | Apache-2.0 | Since 5.2.0 (2023) |
| PowerModels.jl | BSD-3-Clause | LANL (transitive via InfrastructureModels) |
| InfrastructureModels.jl | BSD-3-Clause | LANL |

## Flagged Licenses

### GLPK -- GPL-3.0 (copyleft)

GLPK (GNU Linear Programming Kit) is licensed under GPL-3.0. The Julia wrapper (`GLPK.jl`) dynamically links to the GLPK C library via `GLPK_jll`. The GPL-3.0 copyleft applies when GLPK is used at runtime.

**Mitigation:** GLPK is an optional solver. The evaluation environment includes it for completeness, but HiGHS (MIT) covers the same LP/MIP functionality. GLPK can be excluded from a production deployment by simply not including it in `Project.toml`.

### JuMP / MathOptInterface -- MPL-2.0

MPL-2.0 is a weak file-level copyleft: modifications to MPL-licensed files must remain MPL-licensed, but the license does not extend to other files in the project. This is generally considered commercial-friendly and is widely used in industry.

### Ipopt -- EPL-2.0

EPL-2.0 is a weak copyleft similar to MPL-2.0. Modifications to EPL-licensed code must be shared, but using Ipopt as a dependency does not trigger copyleft for the calling code.

## Assessment

No proprietary or unknown licenses found. The only strong copyleft dependency (GLPK, GPL-3.0) is an optional solver that can be excluded. The remaining copyleft licenses (MPL-2.0, EPL-2.0) are weak/file-level and commercially friendly. **Informational** -- GLPK's GPL-3.0 should be reviewed by legal if included in production, but can be trivially excluded.
