---
test_id: E-7
tool: powermodels
dimension: maturity
status: fail
timestamp: 2026-03-05
---

# E-7: Operational Adoption

## Finding

No evidence of operational deployment at any utility, ISO/RTO, or government agency. PowerModels.jl is explicitly positioned as a research tool for "computational evaluation of emerging power network formulations and algorithms." Its primary adoption is academic and competition-based.

## Evidence

**Stated purpose** (from README): "designed to enable computational evaluation of emerging power network formulations and algorithms in a common platform."

**ARPA-E GOC Competition**: PowerModelsSecurityConstrained.jl served as the benchmark algorithm for ARPA-E Grid Optimization Competition Challenge 1 (2019). This is a research competition benchmark, not an operational deployment.

**Academic citations**: The PSCC 2018 paper has ~300+ citations, indicating strong academic adoption.

**pandapower integration**: pandapower (which has broader industry adoption) can optionally delegate OPF to PowerModels.jl via PyCall, but this is an analysis tool integration, not operational deployment.

**No evidence found of**:
- Utility or ISO/RTO operational use
- Commercial product embedding
- Government operational deployment
- Production grid operations use

**Ecosystem positioning**: PowerSimulations.jl (NREL) extends PowerModels for operational simulation but is itself a research tool.

Sources:
- <https://github.com/lanl-ansi/PowerModels.jl>
- <https://lanl-ansi.github.io/PowerModels.jl/stable/>
- <https://www.osti.gov/biblio/1454978>
- <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl>

## Implications

PowerModels.jl is a well-respected research tool with no evidence of production operational use. This is consistent with its design goals and the Julia ecosystem's general positioning. For an evaluation criterion requiring operational adoption evidence, this is a clear gap.
