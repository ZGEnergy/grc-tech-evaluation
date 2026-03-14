---
tag: arch-quality
source_dimension: extensibility
source_test: B-8
tool: gridcal
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: PTDF-based DC OPF produces slack-invariant LMPs

## Finding

GridCal's DC OPF uses a PTDF-based LP formulation where LMPs are mathematically invariant to the reference bus choice. Changing `bus.is_slack` on different buses and re-solving produces identical LMPs (max difference ~3e-13). This is correct behavior for PTDF-based formulations and a positive architectural property.

## Context

During B-8 testing, three slack bus configurations were tested. Unlike B-matrix-based DC OPF tools where the slack bus affects the angle reference and thus the flow equations, GridCal's PTDF approach eliminates this dependency. The `bus.is_slack` property is still configurable via a simple boolean toggle without model reconstruction, satisfying the API extensibility requirement.

## Implications

For the accessibility dimension: users do not need to understand the relationship between reference bus selection and LMP values, because the formulation handles it correctly by construction. For cross-tool comparison: tools using B-matrix-based DC OPF will show LMP variation with slack bus changes, which is a formulation difference (not a bug in either approach).
