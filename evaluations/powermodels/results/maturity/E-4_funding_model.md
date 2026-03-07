---
test_id: E-4
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-4: Funding Model

## Result: INFORMATIONAL

## Finding

PowerModels.jl is funded by the U.S. Department of Energy through Los Alamos National Laboratory under contract DE-AC52-06NA25396. This provides strong institutional backing but creates dependency on continued DOE research funding, which is grant-cycle dependent. The recent shift of active maintenance to the JuMP ecosystem (Oscar Dowson) suggests a partial de-risking of the LANL funding dependency.

## Evidence

**Primary funding:**
- U.S. Department of Energy, National Nuclear Security Administration (DOE/NNSA)
- Contract: DE-AC52-06NA25396
- Institutional home: Advanced Network Science Initiative (ANSI), Los Alamos National Laboratory
- License: BSD-3-Clause (LA-CC-18-005, copyright Triad National Security, LLC)

**Research program connections:**
- ARPA-E Grid Optimization Competition (GOC): PowerModels served as the benchmark algorithm for Challenge 1 (October 2019). The security-constrained extension (PowerModelsSecurityConstrained.jl) was developed specifically for this competition.
- PGLib-OPF: PowerModels is a primary consumer of the IEEE PES benchmark library
- Multiple DOE-funded extensions: PowerModelsDistribution.jl, PowerModelsITD.jl, PowerModelsSecurityConstrained.jl

**Ecosystem sustainability:**
- The JuMP ecosystem (Julia Mathematical Programming) provides a broader sustainability base. Oscar Dowson (odow), the current active maintainer, is a JuMP core developer funded separately (NumFOCUS fiscal sponsorship for JuMP).
- Julia General registry inclusion ensures package discovery and compatibility testing.

**Durability assessment:**
- STRONG: DOE/LANL backing provides multi-year institutional support uncommon in open-source
- MODERATE RISK: Grant-cycle funding means support could diminish if DOE priorities shift
- MITIGANT: JuMP ecosystem integration provides a secondary sustainability path
- CONCERN: No commercial entity depends on or funds PowerModels directly; no corporate sponsors

Sources:
- <https://github.com/lanl-ansi/PowerModels.jl> (license and institutional attribution)
- <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl> (ARPA-E GOC connection)

## Implications

The DOE/LANL backing is stronger than typical academic open-source but weaker than commercially-funded projects (e.g., pandapower/Fraunhofer, PyPSA/TU Berlin consortium). The lack of any commercial adoption or corporate funding is a long-term durability concern. The funding model supports continued research use but provides limited assurance for production operational deployment.
