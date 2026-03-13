---
test_id: A-4
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 2e877921
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.285
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 155
solver: NLsolve (compute_ac_pf)
timestamp: 2026-03-11T00:00:00Z
---

# A-4: AC Feasibility Check

## Result: QUALIFIED PASS

## Approach

The test implements the AC feasibility check entirely in-memory with no file I/O between the DC OPF and ACPF steps.

### Step 1 — Reproduce A-3 DC OPF dispatch:

Applied the same Modified Tiny augmentations as A-3 (differentiated costs from `gen_temporal_params.csv`, 70% branch derating) and solved DC OPF using `solve_dc_opf`:

```julia

dc_result = PowerModels.solve_dc_opf(
    data, highs_opt;
    setting = Dict("output" => Dict("duals" => true))
)

```

#### Step 2 — Fix generator outputs to DC OPF dispatch:

Unit note: `dc_result["solution"]["gen"][id]["pg"]` is in per-unit on `baseMVA=100`. Transferred directly to `data["gen"][id]["pg"]` without conversion. Set `pmin = pmax = pg_dispatch` to pin each generator's active power output:

```julia

data["gen"][gen_id]["pg"]   = pg_pu   # same per-unit base
data["gen"][gen_id]["pmin"] = pg_pu   # fix lower bound
data["gen"][gen_id]["pmax"] = pg_pu   # fix upper bound

```

#### Step 3 — Flat start and ACPF (per convergence-protocol.md):

```julia

for (_, bus) in data["bus"]
    bus["vm"] = 1.0; bus["va"] = 0.0
end
ac_result = PowerModels.compute_ac_pf(data)

```

#### Step 4 — Extract violations:

Branch flows computed via `PowerModels.calc_branch_flow_ac(data)` after merging solution voltages with `update_data!`. This is required because `compute_ac_pf` does not populate `result["solution"]["branch"]` (known prior observation from A-2).

The entire workflow modifies `data` in-place. No file write or reimport occurs between DC OPF and ACPF — the "same model context" condition is satisfied by design.

## Output

| Metric | Value |
|--------|-------|
| DC OPF status | OPTIMAL |
| DC OPF objective | $215,211/h |
| ACPF converged | true (Bool) |
| ACPF wall clock | 0.0145s |
| Total wall clock | 2.285s (includes Julia JIT) |
| Vm range | 0.97951 – 1.03902 pu |
| Voltage violations | 0 buses |
| Thermal violations | 4 branches |
| Convergence quality (Va non-flat) | 100% (38/38 non-slack buses) |

**Voltage violations** (|Vm| outside [0.95, 1.05] pu): **none**. All buses stay within bounds after the DC OPF dispatch is applied.

**Thermal violations** (|MVA flow| > rate_a after 70% derating):

| Branch | From→To | Flow (MVA) | Limit (MVA) | Overage |
|--------|---------|-----------|------------|---------|
| 3 | 2→3 | 350.47 | 350.0 | +0.47 MVA |
| 20 | 10→32 | 660.04 | 630.0 | +30.04 MVA |
| 27 | 16→19 | 435.32 | 420.0 | +15.32 MVA |
| 37 | 22→35 | 639.35 | 630.0 | +9.35 MVA |

**Interpretation:** The DC OPF dispatch honored the 70% derated thermal limits in the DC approximation (5 binding branches reported in A-3). The ACPF reveals 4 thermal violations — these represent AC infeasibilities not captured by the DC approximation. The DC OPF enforces flow limits on real power only; the AC solution adds reactive power flows that push apparent MVA beyond the limits. This is the expected and correct behavior of an AC feasibility check.

The 5 binding branches from A-3 correspond closely to the 4 violations here (branch 46 from A-3 is not violated in AC, while branches 3, 20, 27, 37 are all present in both DC binding list and AC violations).

Sample bus voltages:

| Bus | Vm (pu) | Va (deg) |
|-----|---------|---------|
| 1 | 1.00603 | -13.430 |
| 2 | 1.01223 | -9.161 |
| 3 | 1.00324 | -12.112 |
| 4 | 0.99145 | -12.688 |
| 5 | 1.00031 | -11.262 |
| 6 | 1.00439 | -10.480 |
| 7 | 0.99222 | -12.846 |
| 8 | 0.99056 | -13.431 |
| 9 | 1.01753 | -14.272 |
| 10 | 1.01618 | -8.342 |

## Workarounds

- **What:** Branch MVA flows require post-processing via `PowerModels.calc_branch_flow_ac(data)` after merging voltages with `update_data!`
- **Why:** `compute_ac_pf` returns only bus voltages (`vm`, `va`) and generator dispatch (`pg`, `qg`) in its solution dict. Branch flows are not populated.
- **Durability:** stable — `calc_branch_flow_ac` is a documented public API function present since v0.18.3. Used in the same pattern in A-2.
- **Grade impact:** Minor. This is an extra 3-line step using documented API. Not a fundamental capability limitation.

- **What:** `compute_ac_pf` termination status is `Bool` (not a JuMP/MOI status code). NR iteration count and convergence residual are not returned.
- **Why:** `compute_ac_pf` uses NLsolve directly, bypassing JuMP. Its result dict does not expose NLsolve internal diagnostics.
- **Durability:** stable — this is the documented behavior of `compute_ac_pf` (per A-2 findings). Not expected to change without a breaking API update.
- **Grade impact:** Minor diagnostic quality limitation. Convergence verified via Bool status + voltage profile quality check (100% of non-slack buses have non-flat angles).

## Timing

- **Wall-clock:** 2.285s (first invocation, includes Julia JIT compilation)
- **ACPF solve only:** 0.0145s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not available (NLsolve internal, not exposed by `compute_ac_pf`)
- **Convergence residual:** not available (NLsolve internal, not exposed)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a4_ac_feasibility_check_tiny.jl`

Key API sequence:

```julia

# 1. DC OPF to get dispatch (same model context — no file I/O)
dc_result = PowerModels.solve_dc_opf(data, highs_opt;
    setting = Dict("output" => Dict("duals" => true)))

# 2. Fix generation at DC OPF dispatch (in per-unit, baseMVA=100)
for (gen_id, gen_sol) in dc_result["solution"]["gen"]
    pg_pu = gen_sol["pg"]
    data["gen"][gen_id]["pg"] = pg_pu
    data["gen"][gen_id]["pmin"] = pg_pu
    data["gen"][gen_id]["pmax"] = pg_pu
end

# 3. Flat start
for (_, bus) in data["bus"]
    bus["vm"] = 1.0; bus["va"] = 0.0
end

# 4. Run ACPF — same data dict, no file write/reimport
ac_result = PowerModels.compute_ac_pf(data)

# 5. Get branch flows (workaround — compute_ac_pf doesn't populate branch)
PowerModels.update_data!(data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(data)

```
