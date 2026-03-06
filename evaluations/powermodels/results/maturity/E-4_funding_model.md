---
test_id: E-4
tool: powermodels
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-4: Funding Model

## Finding

PowerModels.jl is institutionally funded through Los Alamos National Laboratory (LANL) under DOE contract DE-AC52-06NA25396. This is durable government-lab funding, not grant-dependent, though it depends on continued LANL prioritization of the Advanced Network Science Initiative (ANSI).

## Evidence

- **License header**: "Copyright 2016. Los Alamos National Security, LLC. This software was produced under U.S. Government contract DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL)."
- **LANL code identifier**: LA-CC-15-024
- **Organization**: Developed under the Advanced Network Science Initiative (ANSI) at LANL.
- **DOE connection**: Related packages (PowerModelsITD.jl) explicitly cite DOE Office of Electricity (OE) Advanced Grid Modeling (AGM) program funding under program manager Ali Ghassemian.
- **ARPA-E GOC**: PowerModelsSecurityConstrained.jl served as the benchmark algorithm for ARPA-E Grid Optimization Competition Challenge 1 (2019), indicating direct DOE/ARPA-E programmatic investment.
- **PSCC 2018 paper**: ~300+ citations demonstrates academic recognition.
- **OSTI record**: <https://www.osti.gov/biblio/1454978>

Source: LICENSE.md, <https://github.com/lanl-ansi/PowerModels.jl,> OSTI.gov

## Implications

DOE national lab funding is among the most durable funding models for open-source research software. The risk is not funding disappearing but rather LANL/ANSI deprioritizing the project or the primary developer (Coffrin) moving on. The project has no commercial revenue or foundation backing. The ARPA-E competition involvement provides additional programmatic justification for continued DOE investment.
