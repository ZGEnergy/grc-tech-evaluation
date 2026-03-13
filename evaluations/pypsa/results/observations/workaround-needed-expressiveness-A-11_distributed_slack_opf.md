---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-11
tool: pypsa
severity: high
timestamp: 2026-03-11T00:00:00Z
---

# Observation: PyPSA DC OPF has no bus voltage angle variable — distributed slack OPF architecturally blocked

## Finding

PyPSA v1.1.2's DC OPF (`n.optimize()`) builds a linopy model with exactly three variable types: `Generator-p`, `Line-s`, `Transformer-s`. Bus voltage angles are NOT modeled as explicit variables. KVL constraints are expressed in terms of line-flow slack variables. There is no `Bus-v_ang` variable and no angle reference constraint to modify or distribute. Distributed slack in the OPF context is architecturally impossible without source-level changes to PyPSA's model construction.

## Context

Discovered during A-11 distributed slack OPF test. The standard approach to distributed slack OPF — replacing a single-bus angle-zero constraint with a weighted-sum-equals-zero constraint — requires explicit bus angle variables. These do not exist in PyPSA's linopy model.

Contrast: `n.pf()` (AC Newton-Raphson power flow) DOES support `distribute_slack=True, slack_weights="p_set"` and works correctly. This is a PF capability, not an OPF capability.

## Implications

- **Extensibility dimension (B-tests):** Any custom OPF formulation that requires bus voltage angle variables (e.g., custom angle constraints, angle difference limits, multi-area angle reference) will require adding explicit angle variables — a non-trivial model modification.
- **Grade impact:** This is a blocking limitation for distributed slack OPF specifically (A-11 pass condition). It reflects PyPSA's PTDF/flow-based DC OPF formulation philosophy.
- **Positive note:** The flow-based formulation (no angle variables) can be numerically better-conditioned than angle-based formulations and is sufficient for standard DCOPF. The limitation only manifests for features that explicitly need angle variables.
