---
test_id: P2-3
tool: pypsa
dimension: p2_readiness
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 48659195
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# P2-3: Commitment Injection Workflow

## Result: INFORMATIONAL

## Finding

The full SCUC → commitment injection → DCOPF → ACPF workflow is confirmed end-to-end in PyPSA 1.1.2. All four stages completed successfully using only documented public API. The main friction point is the absence of a native `fix_commitment()` method — the two-stage MILP→LP transition requires ~10 LOC of manual schedule-to-bounds conversion using `generators_t.p_min_pu` / `generators_t.p_max_pu`. Total workflow effort is approximately 391 LOC (A-6 script) for the full two-stage UC+ED pipeline.

## Evidence

All findings below are synthesized from confirmed test results in A-4, A-5, and A-6 (all passing).

### Step 1: SCUC (24-hour MILP UC)

**Status: Confirmed working (A-5: PASS)**

```python
# Key API pattern
n.generators["committable"] = True
n.generators["min_up_time"] = n.generators["min_up_time"].astype(int)   # must be int
n.generators["min_down_time"] = n.generators["min_down_time"].astype(int)
n.optimize(snapshots=snapshots, solver_name="highs",
           solver_options={"time_limit": 300, "mip_rel_gap": 0.01})

status_df = n.generators_t.status   # DataFrame: 24 snapshots × 10 generators, values 0.0/1.0
```

Results from A-5 (IEEE 39-bus, Modified Tiny dataset, 10 generators, 24 hours):

| Metric | Value |
|---|---|
| MILP problem size | 6,107 rows, 2,064 cols (720 binary) |
| Solve time | 1.62s |
| MIP gap | 0.818% |
| Objective (total cost) | $1,743,649.64 |
| Generators cycling (≥1 transition) | 3 (G3 coal, G6 gas_CC, G9 gas_CC) |

**Friction:** `min_up_time` / `min_down_time` must be cast to `int` — assigning float values causes a `TypeError` deep in xarray's rolling-window constraint builder. Fix: `int()` cast before assignment. Classified as stable (documented public attribute, single-line fix).

### Step 2: Lock Commitments (Manual p_min_pu / p_max_pu encoding)

**Status: Confirmed working (A-6: QUALIFIED PASS)**

PyPSA has no `fix_commitment()` API. The commitment schedule from Stage 1 is injected into the Stage 2 LP by:
1. Setting `committable=False` (removes binary variables)
2. Setting time-varying `generators_t.p_min_pu` and `generators_t.p_max_pu`

```python
# Stage 2: inject commitment schedule as capacity bounds
n2.generators["committable"] = False   # removes all binary variables
for g in gen_names:
    committed = status_df[g].values   # 1.0=on, 0.0=off per hour
    n2.generators_t.p_min_pu[g] = np.where(committed > 0.5, 0.3, 0.0)
    n2.generators_t.p_max_pu[g] = np.where(committed > 0.5, 1.0, 0.0)
```

This loop body is ~10 LOC. All used attributes are documented public API.

**Why `n.optimize.fix_optimal_capacities()` does not help:** This method fixes generator investment decisions (`p_nom`) for multi-period capacity planning problems, not the operational commitment schedule. There is no `fix_optimal_dispatch()` or `fix_commitment()` convenience method.

The approach of `committable=False + time-varying bounds` is the standard PyPSA idiom for externally constrained dispatch, confirmed by PyPSA documentation examples and GitHub usage.

### Step 3: DCOPF with Fixed Commitment

**Status: Confirmed working (A-6: QUALIFIED PASS)**

```python
n2.optimize(snapshots=snapshots, solver_name="highs",
            solver_options={"presolve": "on", "threads": 1})
```

Results from A-6 Stage 2:

| Metric | Value |
|---|---|
| LP problem size | 4,276 rows, 1,344 cols, **0 binary** |
| Solve time | 0.36s |
| Objective (dispatch cost only) | $1,715,602.96 |
| Simplex iterations | 592 |
| Ramp violations | 0 of 230 generator-interval pairs |

The 0 binary variables confirms pure LP — the commitment injection succeeded completely. Ramp constraints (`Generator-p-ramp_limit_up/down`) were present in the LP constraint matrix and binding (G3 coal at 100% ramp utilization in 2 consecutive-hour pairs).

**Cost accounting check:** UC cost ($1,743,649.64) − ED cost ($1,715,602.96) = $28,046.68, which equals exactly one gas_CC cold-start cost ($28,047 from Modified Tiny `gen_temporal_params.csv`). This confirms the startup cost was correctly attributed to the MILP stage and not double-counted in the LP stage.

### Step 4: ACPF Feasibility Check

**Status: Confirmed working (A-4: PASS, no Ipopt required)**

```python
n.generators_t.p_set = p_set_df   # inject SCED dispatch in-memory
pf_result = n.pf(snapshots=[snapshot])

converged = bool(pf_result["converged"].values.flatten()[0])
n_iter   = int(pf_result["n_iter"].values.flatten()[0])
residual = float(pf_result["error"].values.flatten()[0])
```

Results from A-4:

| Metric | Value |
|---|---|
| PF solver | Newton-Raphson (SciPy, built into PyPSA) |
| Convergence | Yes |
| Iterations | 4 |
| Final residual | 1.891e-09 |
| Wall-clock (full test) | 1.10s |
| Voltage violations | 6 buses (all slight over-voltages from DC→AC dispatch transfer) |
| Thermal violations | 0 |

**No Ipopt required:** `n.pf()` uses PyPSA's built-in Newton-Raphson solver (SciPy-based). Ipopt is only needed for `n.optimize.optimize_and_run_non_linear_powerflow()` (AC OPF). The ACPF feasibility check step does not require any solver beyond what is already installed.

### Workflow Summary

| Stage | PyPSA API | Status | Wall-clock | Friction |
|---|---|---|---|---|
| SCUC (MILP UC) | `n.optimize()` with `committable=True` | PASS | 1.62s | `min_up/down_time` must be `int`; 1-line fix |
| Lock commitments | `committable=False` + `generators_t.p_min/max_pu` | Working (manual) | ~0.01s | No native API; ~10 LOC manual encoding |
| DCOPF-SCED (LP) | `n.optimize()` with `committable=False` | PASS | 0.36s | None beyond Stage 2 setup |
| ACPF check | `n.pf()` | PASS | ~0.09s | `pf()` return structure non-obvious (Dict, not attr-based) |
| **Total workflow** | | | **~3.04s** | |

**Total script LOC:** 391 (A-6, which covers Stages 1–3; A-4 adds ~333 LOC for Stage 4 as a standalone script).

### Friction Assessment

1. **Missing `fix_commitment()` API** — moderate friction. The workaround is well-defined, stable, and uses documented public attributes. Impact: ~10 extra LOC per scenario, no solver upgrade needed.
2. **`min_up/down_time` dtype requirement** — minor friction. Single-line `astype(int)` fix, findable from error trace.
3. **`pf()` return structure** — minor friction. The return value is a `Dict` with DataFrame values, not an attribute-based object. First-time users may expect `n.buses_t.v_ang` to auto-populate (it does), but convergence metadata requires parsing the return dict.
4. **Two separate `n.optimize()` calls, two networks** — By PyPSA design, the cleanest approach is to create a fresh network for Stage 2 (to avoid contamination of `generators_t.status` from Stage 1). This is ~20 LOC of network re-initialization but is architecturally clean.

## Phase 2 Implications

The full SCUC → commitment injection → DCOPF → ACPF workflow is production-ready in PyPSA 1.1.2 with the following notes:

- **No blocking gaps.** All four stages work with HiGHS (LP/MILP) and PyPSA's built-in NR solver. No Ipopt, no external solvers.
- **Workflow effort:** Approximately 1–2 developer-days to implement a reusable two-stage UC+ED pipeline function that handles network setup, parameter loading, commitment injection, and result extraction. The A-6 test script (391 LOC) is a nearly production-ready prototype.
- **Scale consideration:** A-5/A-6 used the 39-bus TINY network (10 generators, 24 hours). Phase 2 with a larger network (hundreds of generators, 8,760 hours) will increase solve time but the API pattern is unchanged — linopy's xarray-based vectorization handles large DataFrames without per-generator loops.
- **Recommended Phase 2 improvement:** Wrap the commitment injection loop (`for g in gen_names: ...`) into a helper function `inject_commitment(n, status_df, p_min_committed=0.3)` to reduce boilerplate and make the pattern reusable across scenarios.
