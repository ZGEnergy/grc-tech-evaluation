---
tag: api-friction
dimension: extensibility
test_id: B-8
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# API Friction: No native distributed slack — stable workaround via PTDF

## Observation

PowerModels.jl v0.21.5 does not provide a native distributed slack formulation. The single-slack
reference bus is the only supported reference bus type.

Implementing load-proportional distributed slack requires:
1. `PowerModels.make_basic_network(data)` + `PowerModels.calc_basic_ptdf_matrix(basic_data)` — compute PTDF
2. `ptdf_dist = ptdf_single - ptdf_single * slack_weights` — distributed-slack PTDF derivation
3. Manual construction of a JuMP OPF model with distributed-slack flow constraints
4. LMP extraction from LP dual variables

This amounts to ~150 lines of manual code. All components use documented public APIs.

## Single-Slack Reference Bus Change

In contrast, single-slack reference bus reconfiguration is trivially supported:

```julia

data["bus"]["31"]["bus_type"] = 2   # old ref → PV bus
data["bus"]["1"]["bus_type"]  = 3   # new ref → slack

```

No model reconstruction. Re-solve with the same `solve_dc_opf` call. LMPs are invariant to
reference bus choice in DC OPF (mathematically correct behavior, not a limitation).

## Classification

**Single-slack configuration:** Not a workaround — this is a clean API (data dict mutation,
documented behavior).

**Distributed slack:** Stable workaround — high effort (~150 LOC) but uses only documented
public APIs. `calc_basic_ptdf_matrix` and `make_basic_network` are first-class public API.

## Implication for Extensibility Grade

The distributed slack gap is a moderate friction point for users who need multi-area LMP
calculations or distributed-slack AC power flow. The single-slack configuration is well-designed
and clean. `calc_basic_ptdf_matrix` provides the building block needed for a workaround, which
mitigates the gap somewhat.
