---
test_id: A-10
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 5.069
peak_memory_mb: null
loc: 367
solver: Ipopt
timestamp: "2026-03-06T00:00:00Z"
---

# A-10: Lossy DC OPF with LMP Decomposition on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

Qualified because DCPLLPowerModel (the built-in lossy DC formulation) generates quadratic
constraints (QCQP) that HiGHS cannot solve. Ipopt is required as a solver fallback.
LMP decomposition into energy/congestion/loss components is NOT built-in and must be
manually computed from bus duals and PTDF matrix.

## Approach

1. `PowerModels.parse_file("case39.m")` to load network data
2. `PowerModels.solve_opf(data, DCPLLPowerModel, Ipopt.Optimizer, setting=Dict("output" => Dict("duals" => true)))` to solve lossy DC OPF with dual extraction
3. LMPs extracted from `result["solution"]["bus"][id]["lam_kcl_r"]` (active power balance dual)
4. Branch losses computed from `pf + pt` per branch (from-end + to-end flows)
5. PTDF matrix computed via `PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))`
6. Energy component = reference bus (31) LMP
7. Congestion + loss component = LMP - energy for each bus
8. Per-line congestion rent = flow *(LMP_to - LMP_from)
9. Lossless DC OPF solved with HiGHS for comparison

## Solver Incompatibility Finding

DCPLLPowerModel generates `ScalarQuadraticFunction-in-GreaterThan` constraints from its
loss linearization. HiGHS only supports LP/QP/MIP (quadratic objective with linear
constraints), not QCQP (quadratic constraints). Ipopt (NLP solver) is required. This
is a significant solver-issues finding: the protocol-specified solver (HiGHS) cannot
be used with PowerModels' lossy DC formulation.

## Output

- **Termination status:** LOCALLY_SOLVED (Ipopt, 18 iterations)
- **Solve time:** 0.0075s (Ipopt NLP)
- **Objective:** 41,890.78 (lossy) vs 41,263.94 (lossless) -- losses increase cost by 1.52%
- **Total losses:** 45.49 MW (0.73% of 6,254 MW load)
  - MATPOWER reference (post-hoc): 49.01 MW (0.78%) -- reasonably consistent
- **LMP range:** [-1412.66, -1336.92] (spread = 75.73)
  - Lossy LMP spread (75.73) >> lossless LMP spread (0.0000025) -- dramatically wider
  - Negative sign reflects dual convention (shadow price on equality constraint)
- **Reference bus (31) LMP:** -1385.10 (energy component)
- **Losses are non-zero:** Yes -- key A-10 pass criterion met
- **Loss components non-zero:** Yes -- congestion_plus_loss differs across buses

## LMP Decomposition

| Component | Method | Values |
|-----------|--------|--------|
| Energy | Ref bus (31) LMP | -1385.10 $/MWh |
| Congestion + Loss | LMP_i - energy | [-27.56, +48.18] range |
| Bus 39 (most negative) | Generator bus, electrically distant | c+l = -27.56 |
| Bus 37 (most positive) | Gen bus, low-loss path | c+l = +48.18 |
| Bus 6 (near zero) | Near ref bus | c+l ~ 0.0 |

Full three-component separation (congestion vs loss individually) requires extracting
individual flow constraint duals, which PowerModels does not automatically report
in the solution dictionary. The combined congestion+loss component is extractable.

## Per-Line Congestion Rent

Top lines by absolute congestion rent:

| Branch | From-To | Flow (MW) | Cong Rent ($/hr) |
|--------|---------|-----------|-----------------|
| 1      | 1->2    | -366.5    | -12,457         |
| 27     | 16->19  | -471.0    | -9,617          |
| 46     | 29->38  | -650.7    | -9,064          |
| 35     | 21->22  | -624.0    | -8,651          |
| 33     | 19->33  | -649.1    | -7,918          |

**Total congestion rent:** -124,117 $/hr

## LMP Reconciliation

| Metric | Value |
|--------|-------|
| Total load payment | -8,640,894 $/hr |
| Total gen revenue | -8,578,835 $/hr |
| Merchandising surplus | -62,059 $/hr |
| Reconciliation error | 0.72% of load payment |
| **Within 5% tolerance** | **Yes** |

## MATPOWER Reference Comparison

| Metric | MATPOWER (lossless) | PowerModels (lossy) | Note |
|--------|--------------------|--------------------|------|
| Formulation | Lossless DC OPF | DCPLLPowerModel (lossy) | Fundamentally different |
| Total losses | 49.01 MW (post-hoc) | 45.49 MW (in optimization) | ~7% difference |
| Loss % | 0.78% | 0.73% | Consistent magnitude |
| LMP spread | [9.87, 32.19] | 75.73 (abs spread) | Not directly comparable (sign conventions differ) |

Direct 1% LMP comparison is not applicable because MATPOWER used lossless DC OPF with
post-hoc loss estimation, while PowerModels' DCPLLPowerModel includes losses in the
optimization. The loss magnitudes are directionally consistent (both ~0.7-0.8% of load).

## Workarounds

1. **Solver incompatibility (stable workaround):** HiGHS cannot solve DCPLLPowerModel due
   to quadratic constraints. Ipopt required as fallback. This is a fundamental formulation
   limitation -- the "linear loss" name (DCPLL) is misleading as the formulation generates
   QCQP constraints.

2. **LMP decomposition not built-in (stable workaround):** Manual computation required.
   Energy = ref bus LMP. Congestion + loss = LMP - energy. Full three-component
   separation requires accessing individual constraint duals from the JuMP model.

## Timing

- Wall-clock: 5.07s (including warm-up, parse, lossy solve, lossless solve; excludes JIT)
- Lossy DC OPF solve: 0.0075s (Ipopt, 18 iterations)
- Lossless DC OPF solve: ~0.001s (HiGHS)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a10_lossy_dcopf_lmp.jl`
