---
test_id: E-4
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 21fed0a4
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# E-4: Funding Model

## Result: PASS

## Finding

PowerModels.jl is developed at Los Alamos National Laboratory (LANL) under the Advanced Network Science Initiative (ANSI), with funding from the U.S. Department of Energy (DOE). The license explicitly references DOE contract DE-AC52-06NA25396. This constitutes stable, long-term federal institutional backing that is not dependent on a single grant cycle.

## Evidence

### License Header (verbatim)

> "Copyright 2016. Los Alamos National Security, LLC. This software was produced under U.S. Government contract DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL), which is operated by Los Alamos National Security, LLC for the U.S. Department of Energy."

Source: <https://github.com/lanl-ansi/PowerModels.jl/blob/master/LICENSE.md> (accessed 2026-03-24)

### README Acknowledgment (verbatim)

> "This code has been developed as part of the Advanced Network Science Initiative at Los Alamos National Laboratory. The primary developer is Carleton Coffrin (@ccoffrin)..."

Source: <https://github.com/lanl-ansi/PowerModels.jl> (accessed 2026-03-24)

### Institutional Details

- **LANL:** Los Alamos National Laboratory -- a DOE national laboratory operated by Triad National Security, LLC. Annual budget ~$4B. Core mission includes energy and national security research.
- **ANSI (Advanced Network Science Initiative):** LANL research program focused on complex networks including power grid analysis. Not a single-year grant but an ongoing research initiative. Publications page: <https://lanl-ansi.github.io/publications/>
- **DOE contract:** DE-AC52-06NA25396 -- the operating contract for LANL itself, indicating PowerModels.jl was developed under LANL's institutional umbrella, not a separate competitive grant.
- **Primary developer:** Carleton Coffrin, staff scientist at LANL. Employment continuity is institutional, not grant-dependent.

### LANL Contributors in PowerModels.jl

| Contributor | Affiliation | Role |
|-------------|-------------|------|
| ccoffrin | LANL | Primary developer, 831 commits |
| rb004f (Russell Bent) | LANL | Matpower export, TNEP |
| pseudocubic (David Fobes) | LANL | PSS/E v33 data support |
| kaarthiksundar | LANL | OBBT utility |
| tasseff (Byron Tasseff) | LANL | Multi-infrastructure updates |

Five LANL staff contributors demonstrates institutional depth beyond one person.

### Ecosystem and Adoption Signals

- **OSTI record:** PowerModels.jl has OSTI.GOV entries (DOE publication database), e.g., <https://www.osti.gov/biblio/1454978>
- **ARPA-E:** Used in ARPA-E Grid Optimization Competition benchmark code
- **DOE-NREL cross-pollination:** NREL-Sienna ecosystem (PowerSystems.jl, PowerSimulations.jl) leverages PowerModels.jl; @jd-lara (NREL) is a contributor
- **Academic citations:** 2018 PSCC paper (Coffrin et al.) is widely cited in power systems optimization literature
- **Related DOE-funded packages:** PowerModelsITD.jl, PowerModelsDistribution.jl, PowerModelsRestoration.jl -- all LANL-ANSI projects extending the same framework

### Secondary Support: JuliaHub / JuMP Ecosystem

@odow (Oscar Dowson), a JuMP maintainer employed at JuliaHub, has become the most active recent contributor (17 of 24 commits in last 12 months). This provides a secondary layer of institutional support from the commercial Julia ecosystem, though it is informal rather than contractual.

### Durability Assessment

**High.** Federal national laboratory backing provides multi-decade institutional stability. The DOE operating contract (DE-AC52-06NA25396) funds LANL as an institution, not PowerModels.jl specifically, which means the project does not face individual grant expiration risk. The primary risk is reduced prioritization if LANL's grid research focus shifts, not sudden funding loss.

## Implications

LANL/DOE institutional backing is among the strongest possible funding models for an open-source scientific tool. The project is not at risk of sudden abandonment due to grant expiration. Five LANL staff contributors and DOE contract acknowledgment in the license provide concrete evidence of sustained institutional investment. This is a strong positive maturity signal.
