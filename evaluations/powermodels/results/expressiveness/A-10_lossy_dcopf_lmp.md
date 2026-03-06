---
test_id: A-10
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-10: Lossy DC OPF with LMP Decomposition on case39

## Result: PASS (with workaround for LMP decomposition)

## Metrics

- **Wall clock:** ~1.2 s
- **Lines of code:** ~40 lines (including manual LMP decomposition)
- **Output format:** Nested `Dict{String,Any}`
- **Workarounds:** 1

## Details

- **Network:** 39 buses, 46 branches
- **Solver:** Ipopt (HiGHS cannot handle DCPLLPowerModel's quadratic loss constraints)
- **Lossless objective:** 41,263.94
- **Lossy objective:** 41,890.78
- **Objective difference:** 626.83 (1.5% increase due to losses)
- **Total system losses:** 0.455 pu
- **Termination status:** LOCALLY_SOLVED (via Ipopt)

### LMP Decomposition

- **Reference bus:** Bus 31 (bus_type == 3)
- **Energy component:** -1,385.10 (ref bus LMP from lossy model)
- **Congestion components:** ~0 across all buses (no congestion in case39)
- **Loss components:** Range from -27.6 to +48.2 across buses
- **Buses with nonzero loss component:** 37 of 39

### Decomposition Method

```

LMP_total = energy + congestion + loss
energy    = ref_bus_LMP (from lossy model)
congestion = lossless_LMP - lossless_ref_LMP (from lossless model)
loss      = total_LMP - energy - congestion (residual)

```

## Workaround

**LMP decomposition is NOT built-in.** PowerModels provides:
- `DCPLLPowerModel` for lossy DC OPF with piecewise-linear losses (native formulation type)
- Bus duals (`lam_kcl_r`) from the lossy model

But it does NOT provide:
- Automatic LMP decomposition into energy/congestion/loss components
- Access to loss penalty factor duals
- A decomposition API

The decomposition was computed manually using a two-solve approach: (1) lossless DC OPF for congestion-only duals, (2) lossy DC OPF for total LMPs, (3) residual attribution for loss component. This is an approximation; exact decomposition would require access to loss sensitivity factors from the JuMP model internals.

## API Pattern

```julia
# Lossless reference
result_lossless = solve_dc_opf(data, solver; setting=Dict("output"=>Dict("duals"=>true)))
# Lossy solve
result_lossy = solve_opf(data, DCPLLPowerModel, Ipopt.Optimizer;
    setting=Dict("output"=>Dict("duals"=>true)))
# Manual decomposition from duals

```

## Notes

- `DCPLLPowerModel` is a first-class formulation type -- no custom model construction needed
- HiGHS fails because DCPLLPowerModel introduces quadratic loss constraints; Ipopt handles these
- The loss components are physically meaningful: buses far from generation centers have higher loss-LMPs
- case39 has no congestion, so the congestion component is uniformly zero

## Test Script

See `evaluations/powermodels/tests/expressiveness/A10_lossy_dcopf_lmp.jl`
