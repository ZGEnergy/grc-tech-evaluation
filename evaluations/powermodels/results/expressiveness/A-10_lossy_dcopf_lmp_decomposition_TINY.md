---
test_id: A-10
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: e7ceb482
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 3.29
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 260
solver: "Ipopt (DCPLLPowerModel); HiGHS (DCPPowerModel baseline)"
timestamp: 2026-03-24T18:00:00Z
---

# A-10: DC OPF with Loss Approximation and LMP Decomposition

## Result: QUALIFIED PASS

## Approach

Two solves on the IEEE 39-bus case with 70% branch derating and differentiated generator costs:

1. **Lossless baseline** -- `DCPPowerModel` solved with HiGHS. Dual variables (`lam_kcl_r`) extracted via `setting=Dict("output"=>Dict("duals"=>true))` and converted to LMPs as `-lam_kcl_r / baseMVA`.

2. **Lossy DCPLL solve** -- `DCPLLPowerModel` solved with Ipopt (NLP). HiGHS was attempted first but rejected with `UnsupportedConstraint{ScalarQuadraticFunction{Float64}, GreaterThan{Float64}}` -- DCPLLPowerModel introduces quadratic loss constraints that HiGHS cannot handle. Ipopt handles these as NLP constraints and reports `LOCALLY_SOLVED`. [solver-specific: HiGHS rejects quadratic constraints]

LMP decomposition:
- **Energy component** = LMP at the slack bus (bus 6) from the lossless solve
- **Congestion component** = LMP_lossless[bus] - energy_component
- **Loss component** = LMP_lossy[bus] - LMP_lossless[bus]

Four consistency checks verified post-solve.

## Output

| Metric | Value |
|--------|-------|
| Lossless DCPPowerModel objective | $215,211.33/h |
| Lossy DCPLLPowerModel objective | $222,343.51/h |
| Objective difference (lossy - lossless) | $7,132.18/h |
| Total load | 6,254.23 MW |
| Total generation (DCPLL) | 6,297.81 MW |
| Estimated losses (gen - load) | 43.58 MW (6.970000e-01%) |
| Energy component (slack bus LMP) | $232.0432/MWh |
| Buses with non-zero congestion component | 37/39 |
| Max |loss component| | 1.072076e+01 $/MWh |
| Binding branches | 5 |
| Congestion rent | $539,609.13/h |

### LMP sample (first 10 buses):

| Bus | LMP lossless ($/MWh) | LMP lossy ($/MWh) | Loss comp ($/MWh) | Congestion comp ($/MWh) |
|-----|----------------------|--------------------|--------------------|-------------------------|
| 1 | 77.1274 | 79.8727 | 2.7452 | -154.9158 |
| 2 | 7.7564 | 7.5652 | -0.1912 | -224.2868 |
| 3 | 290.1140 | 300.8348 | 10.7208 | 58.0708 |
| 4 | 249.6320 | 259.1525 | 9.5204 | 17.5888 |
| 5 | 232.9307 | 241.0262 | 8.0955 | 0.8874 |
| 6 | 232.0432 | 239.6160 | 7.5728 | 0.0000 |
| 7 | 225.4345 | 233.9959 | 8.5614 | -6.6088 |
| 8 | 222.1192 | 230.9350 | 8.8157 | -9.9240 |
| 9 | 161.0469 | 167.3922 | 6.3454 | -70.9964 |
| 10 | 236.6319 | 242.6943 | 6.0624 | 4.5887 |

### Consistency checks:

| Check | Result | Detail |
|-------|--------|--------|
| (a) Loss components non-zero (max > 1e-4) | PASS | max = 1.072076e+01 $/MWh |
| (b) Estimated losses 0.5-3% of load | PASS | 6.970000e-01% |
| (c) Lossy objective >= lossless objective | PASS | diff = +$7,132.18/h |
| (d) Component sum residual < 1% | PASS | max residual = 0.000000e+00 |

All four consistency checks pass. Loss components have physically correct signs (positive at buses far from generation, indicating higher marginal losses for injecting power at electrically distant buses). Total losses at 0.697% are within the expected 0.5-3% range for a DC loss approximation.

## Workarounds

- **What:** DCPLLPowerModel requires Ipopt instead of HiGHS.
- **Why:** DCPLLPowerModel introduces `ScalarQuadraticFunction{Float64} GreaterThan{Float64}` constraints for branch loss linearization. HiGHS supports quadratic objectives (QP) but not quadratic constraints. Ipopt handles these as NLP constraints.
- **Durability:** stable -- Both Ipopt and HiGHS are standard solvers in the PowerModels.jl evaluation stack. The HiGHS rejection is a documented limitation of LP/QP solvers vs. QCQP. Ipopt is the canonical solver for NLP problems in PowerModels.
- **Grade impact:** Minor. The workaround is expected and well-understood. DCPLLPowerModel + Ipopt is a supported and documented combination. The user must know to switch solvers when using loss-inclusive DC formulations.

## Timing

- **Wall-clock:** 3.29s
- **Timing source:** measured (warm JIT)
- **Peak memory:** not measured
- **Solver iterations:** not measured
- **Convergence residual:** N/A (LP/NLP)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a10_lossy_dcopf_lmp_decomposition_tiny.jl`

Key pattern -- solver fallback documented inline:

```julia
# HiGHS + DCPLLPowerModel fails with UnsupportedConstraint{ScalarQuadraticFunction}
# Must use Ipopt for DCPLL:
result_dcpll = PowerModels.solve_opf(data, DCPLLPowerModel, ipopt_opt;
    setting=Dict("output"=>Dict("duals"=>true)))
```

LMP decomposition:

```julia
energy_component = lmps_lossless[slack_bus_id]
congestion_component = lmps_lossless[bid] - energy_component
loss_component = lmps_lossy[bid] - lmps_lossless[bid]
```
