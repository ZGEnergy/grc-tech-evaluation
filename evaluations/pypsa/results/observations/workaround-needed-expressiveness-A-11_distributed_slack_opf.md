---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-11
tool: pypsa
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Distributed slack OPF architecturally impossible in PyPSA

## Finding

PyPSA's DC OPF formulation (`n.optimize()`) uses flow variables (`Generator-p`, `Line-s`, `Transformer-s`) without explicit bus voltage angle variables. There is no `Bus-v_ang` variable in the linopy model, making distributed slack OPF via angle-sum-to-zero constraint architecturally impossible. This is a blocking limitation -- no workaround via `extra_functionality` callback is possible because the angle variables do not exist.

## Context

Test A-11 inspected `n.model.variables` after `n.optimize()` and confirmed only three variable types exist. KVL constraints in PyPSA are expressed in terms of line flow variables, not bus angle differences. PyPSA does support `distribute_slack=True` in `n.pf()` (Newton-Raphson AC power flow) with configurable `slack_weights` parameter, demonstrating the concept is understood but only implemented in the PF context.

## Implications

This affects both Extensibility (B-dimension) and Accessibility assessments. The flow-based OPF formulation is simpler and sufficient for most use cases, but users requiring distributed slack reference pricing (common in ISO/RTO LMP calculations) cannot achieve this with PyPSA's optimization module. The AC PF distributed slack capability is a partial mitigation but does not produce shadow prices / LMPs.
