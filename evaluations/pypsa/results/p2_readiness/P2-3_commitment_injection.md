---
test_id: P2-3
tool: pypsa
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
depends_on: A-5
timestamp: 2026-03-06T00:00:00Z
---

# P2-3: Commitment Injection

## Capability: Yes (all steps achievable, moderate API friction)

The full UC-to-DCOPF-to-ACPF pipeline is achievable in PyPSA by composing three tested capabilities:

1. **SCUC** (A-5): Obtain commitment schedule
2. **Fix commitment + DCOPF** (A-6): Lock commitments, solve economic dispatch as LP
3. **AC PF feasibility check** (A-4): Run Newton-Raphson AC power flow on dispatch solution

All three steps were independently tested and passed in the expressiveness dimension. This test documents how they compose.

## Step-by-Step Workflow

### Step 1: Obtain SCUC Schedule (from A-5)

```python
n.optimize(solver_name="highs", solver_options={"mip_rel_gap": 0.01})
commitment = n.generators_t.status.copy()  # 24x10 binary DataFrame
```

PyPSA returns the commitment schedule as `n.generators_t.status` -- a time-indexed DataFrame of binary values (1=on, 0=off). Tested on case39 with 10 generators, 24 hourly snapshots, min up/down times, ramp limits, and startup/shutdown costs.

**Effort:** Minimal. Single API call with `committable=True` on generators.

### Step 2: Lock Commitments + Solve DCOPF (from A-6)

PyPSA has **no dedicated `fix_commitment()` method**. The commitment must be injected manually by encoding the binary schedule into generator bounds:

```python
# Disable binary variables
n.generators["committable"] = False

# Encode commitment into time-varying bounds
for gen in n.generators.index:
    status_series = commitment[gen]
    n.generators_t["p_max_pu"][gen] = status_series * 1.0  # 0 when off
    n.generators_t["p_min_pu"][gen] = status_series * 0.3  # min stable output when on

# Solve as LP (no binary variables)
n.optimize(solver_name="highs")
```

This produces a pure LP (confirmed: no integer variables in the HiGHS solve). Ramp constraints remain active.

**Effort:** Moderate (~10 lines of glue code). The pattern is straightforward but requires understanding that `committable=False` removes binary variables and that bounds must be set via time-varying `p_min_pu`/`p_max_pu` DataFrames.

**API friction:** The `fix_optimal_dispatch()` method exists but fixes all dispatch values (not just commitment) -- it is not suitable. The `fix_optimal_capacities()` method is for investment planning. Neither supports the SCUC-to-SCED pattern. This is a notable ergonomic gap.

### Step 3: AC PF Feasibility Check (from A-4)

```python
# Transfer dispatch to PF set points
for gen in n.generators.index:
    n.generators.loc[gen, "p_set"] = float(n.generators_t.p.iloc[0][gen])

# Run AC power flow (Newton-Raphson)
n.pf()

# Check violations
v_mag = n.buses_t.v_mag_pu.iloc[0]
violations_v = v_mag[(v_mag < 0.95) | (v_mag > 1.05)]
```

AC PF converges on flat start for case39. Voltage magnitudes and thermal loading are extractable from the solution.

**Effort:** Minimal (~5 lines). Standard two-step pattern documented in PyPSA examples. The convenience method `n.optimize.optimize_and_run_non_linear_powerflow()` exists but runs OPF+PF in one call -- it does not accept externally fixed commitment.

## Composition Summary

| Step | Method | Problem Type | Tested In | Effort |
|------|--------|-------------|-----------|--------|
| SCUC | `n.optimize()` with `committable=True` | MILP | A-5 | Low |
| Fix commitment | Manual bounds manipulation | -- | A-6 | Moderate |
| DCOPF (fixed UC) | `n.optimize()` with `committable=False` | LP | A-6 | Low |
| AC PF check | `n.pf()` with dispatch set points | Newton-Raphson | A-4 | Low |

**Total glue code:** ~20 lines to connect the three stages.

**Overall effort level:** Moderate. Each individual step uses public API. The main friction point is the absence of a `fix_commitment()` convenience method, requiring manual bound manipulation in Step 2.

## Verified Outputs from Prior Tests

| Metric | Source | Value |
|--------|--------|-------|
| SCUC objective | A-5 | $36,474.67 |
| SCED objective (fixed UC) | A-6 | $36,474.67 |
| SCED problem type | A-6 | LP (confirmed no binaries) |
| Ramp violations in SCED | A-6 | 0 |
| AC PF convergence | A-4 | Yes (flat start) |
| Voltage violations (>1.05 pu) | A-4 | 2 buses |
| Thermal overloads (>100%) | A-4 | 1 line |
