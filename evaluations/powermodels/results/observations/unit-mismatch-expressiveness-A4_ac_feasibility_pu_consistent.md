---
tag: unit-mismatch
source_dimension: expressiveness
source_test: A-4
tool: powermodels
severity: low
timestamp: 2026-03-13T18:00:00Z
---

# Observation: DC OPF to ACPF transfer uses consistent per-unit convention (no mismatch)

## Finding

The DC OPF dispatch to ACPF transfer in A-4 operates entirely in per-unit on baseMVA=100. Both `solve_dc_opf` results (`result["solution"]["gen"][id]["pg"]`) and `compute_ac_pf` input (`data["gen"][id]["pg"]`) use the same per-unit convention. No unit conversion is needed at the transfer point. Thermal limits (`rate_a`) are also in per-unit, consistent with branch flow outputs from `calc_branch_flow_ac`.

## Context

The unit consistency guardrail for A-4 required explicitly logging base_power, dispatch units, and limit units at the transfer point. All quantities confirmed to be in per-unit on baseMVA=100. The only conversion needed is for human-readable output (multiply by baseMVA for MW/MVA).

## Implications

PowerModels' consistent use of per-unit internally simplifies the DC-to-AC transfer workflow. This is a positive finding for Accessibility -- users do not need to manage unit conversions between different solver modes within the same tool.
