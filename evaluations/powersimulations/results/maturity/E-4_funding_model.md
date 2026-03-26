---
test_id: E-4
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "21fed0a4"
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

# E-4: Funding Model

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl is developed and maintained by NREL (National Renewable Energy Laboratory), a U.S. Department of Energy (DOE) national laboratory operated by the Alliance for Sustainable Energy, LLC. Funding is primarily through DOE appropriations and DOE-funded research programs, providing a durable institutional backing that is significantly more stable than grant-dependent academic projects or volunteer open-source efforts.

## Evidence

### Institutional Structure

- **Developer:** NREL Sienna team (github.com/NREL-Sienna)
- **Laboratory operator:** Alliance for Sustainable Energy, LLC (a Battelle/MRIGlobal joint venture)
- **Funding authority:** U.S. Department of Energy, Office of Energy Efficiency and Renewable Energy (EERE)
- **NREL annual budget:** ~$700M+ (FY2024), making it the largest U.S. national lab focused on renewable energy
- **GitHub org:** NREL-Sienna contains 10+ related repositories, all under NREL copyright with BSD 3-Clause license

### Sienna Ecosystem Context

PowerSimulations.jl is part of the Sienna ecosystem, NREL's strategic open-source platform for power systems modeling. The ecosystem includes:
- **PowerSystems.jl** — data model layer (now at v5.6.1, indicating continued major investment)
- **PowerSimulations.jl** — optimization/simulation
- **PowerFlows.jl** — power flow analysis
- **PowerNetworkMatrices.jl** — network matrix computations
- **InfrastructureSystems.jl** — shared infrastructure

The ecosystem has its own landing page (nrel-sienna.github.io) and documentation site, indicating institutional investment beyond a single researcher's project.

### Funding Durability Assessment

| Factor | Assessment |
|--------|------------|
| **Funding source** | DOE congressional appropriations + competitive research grants |
| **Institutional permanence** | National labs are effectively permanent institutions; NREL founded 1977 |
| **Strategic alignment** | Power grid modeling directly supports DOE's grid modernization mandate |
| **Alternative funding risk** | Low — DOE grid modernization is bipartisan priority with sustained funding |
| **Single-grant dependency** | No — NREL operates on diversified funding (base appropriations + multiple grants) |
| **Commercial adoption** | Sienna tools used by utilities, ISOs, and researchers, creating constituency for continued funding |

### Risk Factors

1. **Political risk:** DOE budgets are subject to congressional appropriations. Severe budget cuts could reduce NREL headcount, but this is a systemic risk affecting all DOE-funded research, not specific to Sienna.
2. **Priority risk:** If NREL leadership deprioritizes Julia-based tools in favor of alternatives (e.g., Python-based tools), funding could be redirected. The recent PowerSystems.jl v5 major release (Nov 2025) and active v0.33.x development (Mar 2026) suggest this is not currently happening.
3. **Personnel risk:** The core team is small (see E-3). Institutional backing does not prevent key-person departures; it only means positions can be backfilled.

### Data Source

- NREL institutional information: https://www.nrel.gov/about/ (accessed 2026-03-24)
- Sienna ecosystem: https://github.com/NREL-Sienna (accessed 2026-03-24)
- BSD 3-Clause license with NREL copyright in all repositories

## Implications

The DOE/NREL institutional backing is the strongest funding model among the tools under evaluation. National lab projects have multi-decade lifespans supported by federal appropriations rather than time-limited grants. The Sienna ecosystem's alignment with DOE's grid modernization mission provides additional durability. The primary risk is not funding cessation but rather the personnel concentration identified in E-3 — the funding exists to maintain the project, but the knowledge to do so is concentrated in a small team.
