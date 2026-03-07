---
test_id: E-7
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-7: Operational Adoption

## Result: FAIL

## Finding

There is no evidence of PowerModels.jl being deployed in operational/production settings by utilities, ISOs, or government grid operators. Usage is confined to academic research, DOE-funded benchmarking (ARPA-E GOC), and the Julia/JuMP optimization research community.

## Evidence

**Confirmed usage contexts:**

1. **ARPA-E Grid Optimization Competition (GOC):** PowerModelsSecurityConstrained.jl served as the benchmark SCOPF solver for Challenge 1 (October 2019). This is a competition benchmark, not an operational deployment.
   Source: <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl>

2. **Academic research:** The foundational paper (Coffrin et al., 2018, arXiv:1711.01728) is widely cited in power systems optimization literature. Recent 2024-2025 papers continue to use PowerModels.jl for formulation comparison and algorithm development.
   Source: <https://arxiv.org/abs/1711.01728>

3. **PGLib-OPF benchmarking:** PowerModels.jl is a primary tool for the IEEE PES Power Grid Library benchmark suite, used for comparing OPF formulations across standardized test cases.

4. **Julia ecosystem integration:** pandapower provides a bridge to PowerModels.jl for OPF solving, but this is a research interface, not an operational deployment pathway.
   Source: <https://pandapower.readthedocs.io/en/v2.6.0/opf/powermodels.html>

5. **LANL internal research:** Used within the Advanced Network Science Initiative at LANL for research on power network optimization formulations.

**Evidence searched but NOT found:**
- No utility company (IOU, co-op, or municipal) mentions PowerModels.jl in operational contexts
- No ISO/RTO (ERCOT, MISO, CAISO, PJM, SPP, NYISO, ISO-NE) references PowerModels.jl in production systems
- No government agency (DOE, FERC, NERC) lists PowerModels.jl as an approved or operational tool
- No consulting firm or vendor packages PowerModels.jl for commercial grid operations
- The project README describes it as enabling "computational evaluation of emerging power network formulations and algorithms" -- explicitly a research framing

**Contrast with other tools:**
- pandapower: Used by multiple European DSOs and documented in utility case studies
- MATPOWER: Referenced in ISO market software validation
- PyPSA: Used in EU policy modeling (PyPSA-Eur) with government adoption

## Implications

PowerModels.jl's value proposition is academic: comparing mathematical formulations of power flow problems. It is not positioned for, nor adopted in, operational grid management. This is consistent with its design goals but represents a significant gap for any evaluation criterion that values production deployment evidence. The Julia language barrier further limits operational adoption potential, as utility IT environments overwhelmingly use Python, MATLAB, or C++.
