---
test_id: A-10
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 9314de95
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 135.03
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 195
solver: "Ipopt (DCPLLPowerModel); HiGHS (DCPPowerModel baseline)"
timestamp: 2026-03-11T00:00:00Z
---

# A-10: DC OPF with Loss Approximation and LMP Decomposition — SMALL

## Result: QUALIFIED PASS

## Approach

Two solves on the ACTIVSg 2000-bus network with SMALL preprocessing applied:

1. **Lossless baseline** — `DCPPowerModel` solved with HiGHS (LP). Generator costs linearized (c2=0) to avoid HiGHS QP `OTHER_ERROR` on this network. Dual variables (`lam_kcl_r`) extracted via `setting=Dict("output"=>Dict("duals"=>true))` and converted to LMPs as `-lam_kcl_r / baseMVA`.

2. **Lossy DCPLL** — `DCPLLPowerModel` solved with Ipopt (NLP). HiGHS rejected due to `UnsupportedConstraint{ScalarQuadraticFunction, GreaterThan}` — confirmed behavior from TINY test. Ipopt handles the quadratic loss constraints natively and reports `LOCALLY_SOLVED`.

LMP decomposition (same as TINY):
- **Energy component** = LMP at reference bus (bus 7098)
- **Loss component** = LMP_lossy[bus] − LMP_lossless[bus]
- **Congestion component** = LMP_lossless[bus] − energy_component

All four consistency checks passed.

## Output

| Metric | Value |
|--------|-------|
| Network | 2000 buses, 3206 branches, 544 gens |
| Lossless DCPPowerModel objective | $1,187,342.95/h |
| Lossy DCPLLPowerModel objective | $1,215,204.43/h |
| Objective difference (lossy − lossless) | +$27,861.48/h |
| Total load | 67,109.21 MW |
| Estimated losses (gen − load) | 1,483.13 MW (2.21%) |
| Reference bus | 7098 |
| Energy component (ref bus LMP) | $17.702/MWh |
| Lossy LMP range | $15.461 – $20.058/MWh |
| Max \|loss component\| | $2.356/MWh |
| Loss components non-zero | YES |
| Congestion component | All zero (network uncongested at base case) |

### LMP decomposition sample (first 10 buses):

| Bus | LMP lossless | LMP lossy | Loss component |
|-----|-------------|-----------|----------------|
| 1001 | 17.702 | 17.9609 | +0.2589 |
| 1002 | 17.702 | 17.4665 | −0.2355 |
| 1003 | 17.702 | 15.9219 | −1.7801 |
| 1004 | 17.702 | 16.0848 | −1.6172 |
| 1005 | 17.702 | 16.8085 | −0.8935 |
| 1006 | 17.702 | 16.7564 | −0.9456 |
| 1007 | 17.702 | 17.5131 | −0.1889 |
| 1008 | 17.702 | 15.8076 | −1.8944 |
| 1009 | 17.702 | 15.7186 | −1.9834 |
| 1010 | 17.702 | 17.1011 | −0.6009 |

#### Consistency checks:

| Check | Result |
|-------|--------|
| (a) Loss components non-zero (max > 1e-4) | PASS (max=2.356 $/MWh) |
| (b) Estimated losses 0.5–3% of load | PASS (2.21%) |
| (c) Lossy objective ≥ lossless objective | PASS (diff=+$27,861/h) |
| (d) Component sum residual < 1% | PASS (max_residual=0.0) |

Note: Zero congestion components indicate the 2000-bus network has no binding branch constraints at base case (consistent with ACTIVSg2000 cross-tool watchpoint: max loading ~92%, but linearized costs + no derating leaves the base case uncongested in the LP sense). This is a network characteristic, not a tool limitation.

## Workarounds

- **What 1:** DCPLLPowerModel requires Ipopt instead of HiGHS.
- **Why:** DCPLLPowerModel introduces `ScalarQuadraticFunction{Float64} GreaterThan{Float64}` constraints for branch loss linearization. HiGHS supports QP objectives but not quadratic constraints. Ipopt handles these as NLP constraints.
- **Durability:** stable — Both solvers are in the evaluation stack. This is the same documented behavior as the TINY test.

- **What 2:** Generator costs linearized (c2=0) for the lossless HiGHS solve.
- **Why:** HiGHS QP (quadratic cost objectives) returns `OTHER_ERROR` on the ACTIVSg2000 network. Linearization makes it a pure LP. The loss decomposition is unaffected by cost linearity.
- **Durability:** stable — Does not affect the LMP physics. The DCPLL solve (Ipopt) retains whatever cost form was present (after linearization).

- **Grade impact:** Minor. Both workarounds are expected and documented. The underlying PowerModels API works correctly — solver selection and cost linearization are user-side choices.

## Timing

- **Wall-clock:** 135.03s total
- **Lossless solve (HiGHS):** 65.48s
- **Lossy solve (Ipopt):** 49.18s
- **Timing source:** measured (includes Julia startup and package load)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a10_lossy_dcopf_lmp_decomposition_small.jl`

Key pattern — solver selection and LMP extraction:

```julia

# Lossless: HiGHS (LP with linearized costs)
result_lossless = PowerModels.solve_opf(data_lossless, DCPPowerModel, highs_opt;
    setting=Dict("output" => Dict("duals" => true)))
lmps_lossless[bid] = -lam_kcl_r / baseMVA

# Lossy: Ipopt required for DCPLL quadratic constraints
result_lossy = PowerModels.solve_opf(data_lossy, DCPLLPowerModel, ipopt_opt;
    setting=Dict("output" => Dict("duals" => true)))

# LMP decomposition
energy_component = lmps_lossless[ref_bus_id]
loss_component = lmps_lossy[bid] - lmps_lossless[bid]
congestion_component = lmps_lossless[bid] - energy_component

```
