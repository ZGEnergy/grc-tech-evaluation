# Phase 2 Research — State Estimation Investigation

This directory contains the completed state estimation (SE) investigation
conducted as groundwork for Phase 2. It evaluates SE capabilities across all
six Phase 1 tools and surveys the broader open-source landscape.

**Key finding:** None of the six evaluated tools provide production-ready SE
for transmission-scale grids. Phase 2 will require dedicated SE tooling work.

## Per-Tool Findings

| File | Tool | Summary |
|------|------|---------|
| `gridcal-state-estimation-findings.md` | GridCal | Native WLS SE; scaling limits at large networks |
| `matpower-state-estimation-findings.md` | MATPOWER | SE in extras (dormant); requires MATLAB |
| `pandapower-state-estimation-findings.md` | pandapower | Native WLS SE; distribution-focused |
| `powermodels-state-estimation-findings.md` | PowerModels.jl | Ecosystem SE package (PowerModelsStateEstimation.jl) |
| `powersimulations-state-estimation-findings.md` | PowerSimulations.jl | No SE capability |
| `pypsa-state-estimation-findings.md` | PyPSA | No SE capability |

## Landscape Analysis

| File | Scope |
|------|-------|
| `state-estimation-investigation.md` | Master synthesis across all tools + recommendations |
| `se-landscape-academic.md` | Academic SE research (PMU, hybrid, ML-based) |
| `se-landscape-python.md` | Python SE tool survey (power-grid-model, ANDES, etc.) |
| `se-landscape-powsybl.md` | PowSyBl assessment (confirms no SE capability) |
| `se-landscape-remaining.md` | Non-Python tools (GridPACK, InterPSS, PSAT, DPsim) |
