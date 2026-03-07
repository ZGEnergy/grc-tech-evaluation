---
test_id: A-11
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 8.005
peak_memory_mb: null
loc: 396
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-11: Distributed Slack OPF on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

Qualified because PowerModels has **no native distributed slack support**. The OPF
and power flow formulations use a single reference bus (bus_type=3) exclusively. A
functional workaround was constructed using a manually-built PTDF-based DC OPF with
distributed slack weights derived from PowerModels' `calc_basic_ptdf_matrix`.

## Confirmed Limitation

PowerModels.jl has no distributed slack bus support:

- **GitHub Issue #989:** Generators at PQ buses cause assertion errors
- **GitHub Issue #932:** Incorrect behavior for active generators at load buses
- **Research finding:** Single-slack-bus model hardcoded throughout formulations
- No API parameter, configuration option, or extension point for distributed slack

## Approach

1. **Single-slack DC OPF** via `PowerModels.solve_dc_opf()` with HiGHS (reference from A-3)
2. **Compute single-slack PTDF** via `PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))`
3. **Derive distributed-slack PTDF:** `H_dist = H_single - H_single * w` where `w` is the
   load-proportional slack weight vector
4. **Build manual PTDF-based DC OPF** via JuMP with:
   - Generator dispatch variables with bounds
   - Power balance equality constraint
   - Branch flow limits using distributed-slack PTDF: `flow_l = H_dist[l,:] *(Cg * pg - load)`
   - Quadratic generator cost objective (same as PowerModels)
5. **Extract distributed-slack LMPs** from dual variables:
   `LMP_i = lambda_balance + sum_l(H_dist[l,i] * mu_l)`
6. **Compare dispatch and LMPs** between single-slack and distributed-slack formulations

## Output

- **Single-slack termination:** OPTIMAL (HiGHS QP)
- **Distributed-slack termination:** OPTIMAL (HiGHS QP)
- **Single-slack objective:** 41,263.94
- **Distributed-slack objective:** 41,263.94 (identical -- economic dispatch is invariant)

### Dispatch Comparison

Dispatch is identical between single-slack and distributed-slack (max difference: 8.1e-9 p.u.).
This is physically correct: the optimal economic dispatch depends only on the feasible
region (generator bounds + flow limits) and cost function, not on the slack distribution.
The slack distribution affects only the interpretation of flows and prices, not the
optimal generation schedule.

### LMP Comparison

| Property | Single-Slack | Distributed-Slack |
|----------|-------------|-------------------|
| LMP range | 2.5e-6 (nearly uniform) | 0.0 (exactly uniform) |
| Sign convention | Negative (PM dual convention) | Positive (JuMP dual convention) |
| Ref bus LMP | -1351.692 | 1351.692 |
| LMPs differ | Yes (sign + small numerical differences) | -- |

The IEEE 39-bus network under uncongested conditions produces nearly uniform LMPs regardless
of slack distribution. The key structural finding is confirmed: the distributed-slack
PTDF produces a valid OPF solution with settable weights. In congested networks, the
LMP differences between single-slack and distributed-slack would be more pronounced.

### Distributed Slack Weights

- **Load-proportional:** 21 of 39 buses have nonzero load, giving 21 nonzero weights
- **Uniform:** 1/39 at each bus (also demonstrated)
- **PTDF difference:** max |H_single - H_dist| = 0.999 (significant structural difference)
- **Weights are settable:** Yes, via the weight vector `w` in `H_dist = H_single - H_single * w`

## What PowerModels Contributed vs. What Was Manual

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Single-slack DC OPF | PowerModels (`solve_dc_opf`) |
| Single-slack PTDF matrix | PowerModels (`calc_basic_ptdf_matrix`) |
| Basic network preparation | PowerModels (`make_basic_network`) |
| Distributed-slack PTDF derivation | Manual (linear algebra) |
| Distributed-slack DC OPF formulation | Manual (JuMP, ~150 lines) |
| LMP extraction from distributed OPF | Manual (JuMP dual extraction) |
| Slack weight construction | Manual |

## Workarounds

1. **No native distributed slack (stable workaround):** PowerModels provides no API for
   distributed slack in any formulation (PF, OPF, or native compute functions). The
   entire distributed-slack OPF must be manually assembled via JuMP. PowerModels
   contributes the single-slack PTDF matrix and data parsing, but the formulation
   (~150 lines of JuMP code) is user-built. The workaround is mathematically clean
   (H_dist = H_single - H_single * w) but requires understanding of PTDF algebra
   and JuMP modeling.

## Timing

- Wall-clock: 8.0s (including PowerModels single-slack OPF, PTDF computation, manual OPF
  build, dual extraction; excludes JIT)
- Single-slack solve: ~0.001s (HiGHS QP)
- Distributed-slack solve: 0.001s (HiGHS QP)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a11_distributed_slack_opf.jl`
