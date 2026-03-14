---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-5
tool: pandapower
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: pandapower has no unit commitment formulation

## Finding

pandapower 3.4.0 is a steady-state network analysis tool with no SCUC capability. It lacks binary commitment variables, startup/shutdown costs, minimum up/down time constraints, and multi-period temporal coupling. This is a design scope limitation, not a missing feature.

## Context

During A-5 (SCUC) evaluation, pandapower was confirmed to have only single-period continuous OPF (`rundcopp`, `runopp`). The PandaModels.jl bridge is not installed and would not resolve the gap since PowerModels.jl also lacks native SCUC.

## Implications

This blocking limitation affects the extensibility assessment: pandapower cannot be extended to support SCUC through its API alone. A complete external optimization model (Pyomo, PuLP) would be required, bypassing pandapower's solver entirely. This also blocks A-6 (SCED), creating a cascaded failure across the UC/ED workflow tests.
