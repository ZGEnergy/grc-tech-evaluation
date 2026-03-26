---
test_id: E-7
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: c1355776
status: qualified_pass
workaround_class: null
timestamp: 2026-03-24T12:00:00Z
---

# E-7: operational_adoption

## Finding

PowerModels.jl has documented operational use within DOE national laboratory environments and serves as the reference OPF implementation for the IEEE PES PGLIB-OPF benchmark suite. It is architecturally connected to NREL's Sienna/SIIP ecosystem (PowerSystems.jl, PowerSimulations.jl), which is used in DOE-funded grid operations research. Academic citation is extensive. Direct evidence of deployment at commercial ISOs, utilities, or in real-time market operations is absent.

## Evidence

### Institutional and operational use

1. **LANL (primary developer):** Developed under the LANL Advanced Network Science Initiative. LANL staff (@ccoffrin, @rb004f, @kaarthiksundar) are the core contributors. Used as the computational platform in DOE-funded grid resilience and optimization studies.

2. **IEEE PES PGLIB-OPF benchmark (de-facto standards role):** PowerModels.jl is one of two official reference implementations (alongside MATPOWER) for the PGLIB-OPF benchmark library (https://github.com/power-grid-lib/pglib-opf, 390 stars, 96 forks). This benchmark suite is maintained by the IEEE PES Task Force on Benchmarks for Validation of Emerging Power System Algorithms and is widely used as ground truth for comparing OPF solvers. This constitutes operational infrastructure use in the power systems research community.

3. **NREL Sienna/SIIP ecosystem:** PowerSystems.jl (NREL, 360 stars, 101 forks, 7,271 commits, 198 releases) is part of the Scalable Integrated Infrastructure Planning (SIIP) initiative. The Sienna ecosystem shares data model lineage with PowerModels.jl. PowerSystems.jl has a DOE software record designation (SWR-23-105) and peer-reviewed publication in SoftwareX (2021). The ecosystem is used by NREL researchers in grid planning and operations studies for DOE and grid operators.

4. **DOE Grid Modernization Initiative:** Multiple DOE GMI project publications cite PowerModels.jl as the computational platform for transmission security and OPF studies. National labs including PNNL and ANL have referenced it in technical reports.

5. **Academic adoption:** The original paper (Coffrin et al., 2018, PSCC) has extensive citations. GitHub metrics: 460 stars, 167 forks. JuliaCon presentations (2017, 2018) demonstrate use at MIT, Berkeley, Michigan, and other institutions.

### Contributor affiliations as adoption proxy
Institutional contributors include LANL, NREL (via Sienna cross-contributions), CSIRO (Australia), Georgia Tech, KU Leuven, MIT, UC Berkeley, UTN-BA — indicating global research adoption across multiple continents.

### No direct evidence found of
- Deployment at commercial ISO/RTO market operators
- Use in real-time market clearing or dispatch systems
- Commercial utility deployment for operational planning
- The README itself describes PowerModels as enabling "computational evaluation of emerging power network formulations" — positioning it as a research tool

## Implications

PowerModels.jl occupies a strong position as a reference platform for power systems optimization research, with genuine operational infrastructure roles (PGLIB-OPF benchmarks, DOE national lab studies, NREL SIIP ecosystem). The national-lab and DOE-adjacent adoption pattern is credible and relevant for ZGE's use case (grid modeling for energy trading research). However, the absence of commercial ISO or utility deployment means it has not been validated in production market operations contexts. Status: **qualified_pass** — solid operational adoption in research and DOE infrastructure, but not in commercial market operator systems.
