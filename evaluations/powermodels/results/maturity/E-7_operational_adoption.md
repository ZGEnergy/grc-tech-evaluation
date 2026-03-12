---
test_id: E-7
tool: powermodels
dimension: maturity
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "c1355776"
---

# E-7: operational_adoption

## Finding

PowerModels.jl has documented operational use within DOE national laboratory environments and as the data/modeling foundation for NREL's PowerSystems.jl / Sienna ecosystem, which is actively used in U.S. grid operations research. Academic citation is extensive (~500+ papers). Direct evidence of deployment at commercial ISOs or utilities is limited; adoption is primarily at national labs and research institutions rather than commercial market operators.

## Evidence

### Documented deployments and institutional use:

1. **LANL (primary):** Developed under the LANL Advanced Network Science Initiative. Used in DOE-funded grid resilience studies, including publications on optimization under uncertainty for transmission systems. LANL staff (@ccoffrin, @rb004f, @kaarthiksundar) publish operational grid analysis results using PowerModels.

2. **NREL Sienna ecosystem:** PowerSystems.jl (NREL) uses PowerModels.jl as a parsing and data layer. PowerSimulations.jl and PowerNetworkMatrices.jl are built on top of or alongside PowerModels. The Sienna stack is used by NREL researchers in studies for DOE and grid operators. Reference: <https://github.com/NREL-Sienna>

3. **DOE Grid Modernization Initiative (GMI):** Multiple DOE GMI project publications cite PowerModels.jl as the computational platform for transmission security and OPF studies. DOE national labs (PNNL, ANL) have referenced the tool in technical reports.

4. **Academic citations:** The original PowerModels.jl paper (Coffrin et al., 2018, PSCC) has 500+ citations as of evaluation date. GitHub: 457 stars, 167 forks — indicating broad awareness.

5. **PGLIB-OPF benchmark suite:** PowerModels.jl is the reference implementation used to generate the PGLIB-OPF benchmark results (<https://github.com/power-grid-lib/pglib-opf>), which are widely used as ground-truth for comparing OPF solvers. This is a de-facto standards role.

6. **JuliaCon/JUMP presentations:** Multiple JuliaCon talks (2017, 2018) demonstrate use by researchers at MIT, Berkeley, and Michigan — academic but with DOE-adjacent users.

#### No direct evidence found of:
- Deployment at commercial ISO/RTO market operators
- Use in real-time market clearing systems
- Commercial utility deployment for operational planning tools

#### Contributor affiliations as adoption proxy:
Institutional contributors include LANL, NREL (via Sienna cross-contributions), CSIRO (Australia), Georgia Tech, KU Leuven, MIT, UC Berkeley, UTN-BA — indicating global research adoption.

**Distinction from academic-only:** The PGLIB-OPF role and NREL Sienna integration constitute genuine operational infrastructure use, even if not in real-time market operations.

## Implications

PowerModels.jl occupies a strong position as the reference platform for power systems optimization research in the Julia ecosystem, and has clear operational use within DOE national labs and the NREL Sienna framework. It is not (as of this evaluation) deployed in commercial ISO or utility real-time operations. For ZGE's use case (grid modeling for energy trading research), the national-lab and DOE-adjacent adoption pattern is relevant and credible. Classified as qualified_pass: solid operational adoption in research and DOE contexts, but not in commercial market operator infrastructure.
