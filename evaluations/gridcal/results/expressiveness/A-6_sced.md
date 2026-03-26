---
test_id: A-6
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "3343ccf1"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.97
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 418
solver: "HiGHS"
sced_mode: full_sced
timestamp: "2026-03-24T00:00:00Z"
---

# A-6: Fix commitment from A-5, solve economic dispatch as LP/QP

## Result: QUALIFIED PASS

## Approach

Implemented as a two-stage workflow:

**Stage 1 (UC):** Ran 24-hour SCUC using `OptimalPowerFlowTimeSeriesDriver` with
`OpfDispatchMode.UnitCommitment`, `consider_ramps=True`, and `consider_time_up_down=True`.
Extracted the commitment schedule as a binary matrix (generator dispatching > 0.1 MW = committed).

**Stage 2 (ED):** Loaded a fresh grid, applied the same costs and load profiles, then fixed the
commitment schedule by setting `Pmax_prof` and `Pmin_prof` profiles on each generator. For hours
where a generator was decommitted in Stage 1, both Pmax and Pmin were set to 0. Ran the ED as
`OpfDispatchMode.Normal` with `consider_ramps=True`.

GridCal does not have a named SCED abstraction. The UC-ED separation is achieved by using the
same linear OPF formulation in two modes (UnitCommitment vs Normal) with profile-based commitment
fixing. This is a documented, public API approach using `Pmax_prof`/`Pmin_prof` setter methods.

**sced_mode: full_sced** -- Both UC and ED stages were performed. The UC stage produces a
commitment schedule which is fixed in the ED stage. No security constraints are enforced in
the ED stage (N-1 contingency analysis would require `consider_contingencies=True`).

## Output

| Metric | Value |
|--------|-------|
| UC converged | True (all 24 hours) |
| ED converged | True (all 24 hours) |
| Cycling generators (UC) | 6 of 10 |
| ED wall-clock | 0.12 s |
| Ramp violations in baseline ED | 0 |
| Total ramp checks | 208 |

**Commitment schedule** (from UC stage, 6 generators cycle):

| Generator | Hours On | Transitions |
|-----------|----------|-------------|
| G0 (Hydro) | 24 | 0 |
| G1 (Nuclear) | 24 | 0 |
| G2 (Nuclear) | 22 | 4 |
| G3 (Nuclear) | 24 | 0 |
| G4 (Nuclear) | 24 | 0 |
| G5 (Coal) | 23 | 2 |
| G6 (Gas CC) | 21 | 1 |
| G7 (Gas CC) | 23 | 1 |
| G8 (Coal) | 23 | 2 |
| G9 (Gas CC) | 14 | 2 |

**ED dispatch summary** (with fixed commitment):

| Generator | Min MW | Max MW | Mean MW |
|-----------|--------|--------|---------|
| G0 | 827.3 | 900.0 | 892.6 |
| G1 | 0.0 | 646.0 | 575.2 |
| G2 | 0.0 | 725.0 | 640.5 |
| G3 | 241.0 | 652.0 | 607.8 |
| G4 | 191.1 | 444.8 | 430.5 |
| G5 | 0.0 | 687.0 | 641.3 |
| G6 | 0.0 | 71.0 | 58.6 |
| G7 | 0.0 | 564.0 | 425.2 |
| G8 | 0.0 | 865.0 | 829.0 |
| G9 | 0.0 | 703.8 | 138.7 |

### v11 Ramp Binding Evidence

**Baseline ramp enforcement:** All 208 inter-hour ramp checks passed with no violations,
confirming `consider_ramps=True` enforces ramp constraints in the baseline ED.

**Tightened ramp test (10% of baseline, capped at 50 MW/hr):**
- Dispatch changed significantly (max diff 865 MW from baseline), confirming ramp constraints
  affect the optimization.
- 1 ramp violation detected with tightened limits: Gen 5 at hour 1, delta = 219.1 MW vs
  50 MW/hr limit (ratio 4.38x).
- 0 binding constraints at the tightened limit (no generator delta matched the limit exactly).

**Ramp dual values:** GridCal does not expose ramp constraint dual values from the LP solution.
Binding status can only be inferred from dispatch deltas. This is a formulation transparency
limitation. [tool-specific]

**Finding:** Ramp enforcement in `OpfDispatchMode.Normal` works for the baseline case but
partially fails with very tight ramp limits. The violation suggests the ramp constraint
formulation may not enforce on all generators equally in Normal mode. The UC mode
(`OpfDispatchMode.UnitCommitment`) appears to enforce ramps more reliably. [tool-specific]

## Workarounds

- **What:** Commitment fixing via `Pmax_prof`/`Pmin_prof` profiles rather than a dedicated
  commitment-fixing API. Ramp dual values not extractable.
- **Why:** GridCal has no named SCED abstraction or API to pass a binary commitment matrix.
  The UC and ED stages use the same `linear_opf` formulation; the separation is achieved by
  zeroing Pmax/Pmin for decommitted generators.
- **Durability:** stable -- Uses documented public API (`Pmax_prof.set()`, `Pmin_prof.set()`)
  and a standard OPF dispatch mode (`OpfDispatchMode.Normal`).
- **Grade impact:** Minor. The two-stage workflow is clean and uses only documented features.
  The ramp violation under tightened limits and inability to extract dual values reduce
  from pass to qualified_pass.

## Timing

- **Wall-clock:** 1.97 s (total, both stages + ramp binding test)
- **ED stage only:** 0.12 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a6_sced.py`

Key code showing the two-stage separation:

```python
# Stage 1: UC
opf_opts_uc = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    dispatch_mode=OpfDispatchMode.UnitCommitment,
    consider_ramps=True,
    consider_time_up_down=True,
)
# ... run and extract commitment matrix ...

# Stage 2: ED -- fix commitment via profiles
for g_idx, gen in enumerate(generators_ed):
    pmax_profile = np.full(n_hours, gen.Pmax)
    pmin_profile = np.full(n_hours, gen.Pmin)
    for t in range(n_hours):
        if commitment[t, g_idx] == 0:
            pmax_profile[t] = 0.0
            pmin_profile[t] = 0.0
    gen.Pmax_prof.set(pmax_profile)
    gen.Pmin_prof.set(pmin_profile)

opf_opts_ed = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    dispatch_mode=OpfDispatchMode.Normal,
    consider_ramps=True,
)
```
