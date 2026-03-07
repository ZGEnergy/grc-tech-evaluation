---
tag: workaround-needed
dimension: expressiveness
test_id: A-10
slug: lossy_dcopf_lmp
tool: powermodels
network: TINY
---

# workaround-needed: LMP decomposition not built-in

## Finding

PowerModels provides total LMPs via bus power balance duals (`lam_kcl_r`) but does
not decompose them into energy, congestion, and loss components. This decomposition
is fundamental for market operations (ISO settlement, FTR valuation, loss allocation).

## Workaround

1. Energy component = reference bus LMP (trivial extraction)
2. Congestion + loss = LMP_i - energy (simple arithmetic)
3. Full three-component separation requires accessing individual flow constraint duals
   from the JuMP model, which PowerModels does not automatically populate in the
   solution dictionary

## Effort

Low for two-component (energy + congestion/loss combined). Moderate for full
three-component separation requiring JuMP model introspection.

## Stability

Stable -- the approach is mathematically sound and uses documented PowerModels APIs
(duals setting, PTDF computation) plus standard JuMP dual extraction.
