---
test_id: P2-3
tool: gridcal
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "7de8b3ce"
timestamp: "2026-03-13T00:00:00Z"
---

# P2-3: Commitment injection workflow

## Finding

GridCal/VeraGrid can implement a commitment injection workflow (lock SCUC schedule, solve DCOPF, AC PF check) using existing API primitives, but it requires manual orchestration -- there is no built-in pipeline for this multi-stage process.

## Evidence

**Step 1 -- SCUC produces commitment schedule (A-5 confirmed).** The A-5 test demonstrated that `OptimalPowerFlowTimeSeriesDriver` with `OpfDispatchMode.UnitCommitment` produces a 24-hour commitment schedule. The commitment state is derived from generator power output (`gen_power > threshold`), as there is no explicit binary commitment variable exposed in the results object.

**Step 2 -- Lock commitment for DCOPF.** The `Generator` class provides two attributes for fixing commitment:

| Attribute | Type | Effect |
|-----------|------|--------|
| `active` | bool | If `False`, generator is completely removed from the network model |
| `enabled_dispatch` | bool | If `False`, generator is not dispatchable by OPF (treated as fixed injection) |
| `must_run` | bool | If `True`, generator must be committed (cannot be decommitted by UC) |

To inject a commitment schedule:
1. Set `gen.active = False` for decommitted generators at each time step (via `active_prof` for time series)
2. Run a second OPF in `OpfDispatchMode.Normal` (economic dispatch only, no binary variables) to re-dispatch committed units

Alternatively, `enabled_dispatch` can be toggled per generator to fix some units at their SCUC setpoints while re-dispatching others. Both `active_prof` and `enabled_dispatch_prof` support time-varying profiles via the `Profile` object.

**Step 3 -- AC PF check.** After DCOPF dispatch, the generator power setpoints can be written back to the grid model (`gen.P = dispatch_mw`) and an AC power flow run via `vge.power_flow(grid, options)` with `SolverType.NR` validates voltage and reactive power feasibility.

**API friction.** The main friction points are:

1. **No explicit commitment variable in results.** The UC results expose `generator_power` (float) but not the binary commitment decision. Commitment must be inferred from `power > epsilon`, which is fragile for generators at their minimum output.
2. **Manual profile manipulation.** Injecting per-hour commitment requires setting `active_prof` or `enabled_dispatch_prof` arrays element-by-element for each generator, then re-running with a fresh driver instance.
3. **No pipeline abstraction.** Each stage (SCUC, DCOPF, ACPF) is a separate driver invocation. The user must manually extract results, modify the grid, and re-invoke. There is no `balanced_scuc_sced()` convenience function analogous to the existing `balanced_pf()` (which chains OPF + PF).

**The `balanced_pf` function** (`vge.balanced_pf(grid, options, opf_options)`) demonstrates that VeraGrid has the pattern for chaining OPF with PF validation, but it operates at the snapshot level and does not support the UC-then-ED-then-PF pipeline.

## Implications

- **Feasibility:** The commitment injection workflow is achievable with current APIs. All three stages (SCUC, DCOPF, ACPF) are individually supported. The integration is manual but straightforward.
- **Effort level:** Low-to-medium. Approximately 50-80 lines of orchestration code to extract the SCUC schedule, set generator profiles, re-run DCOPF, transfer setpoints, and run ACPF. No internal modifications required.
- **Risk:** The lack of an explicit binary commitment variable in the UC results is the primary risk. Inferring commitment from power output may misclassify generators operating at `Pmin` if `Pmin` is close to zero.
- **Enhancement opportunity:** A `commitment_schedule` array (dtype bool, shape `[nt, ngen]`) in `OptimalPowerFlowTimeSeriesResults` would eliminate the inference step and make the workflow more robust.
