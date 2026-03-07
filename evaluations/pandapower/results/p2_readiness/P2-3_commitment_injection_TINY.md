---
test_id: P2-3
tool: pandapower
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: 1.82
peak_memory_mb: null
loc: 170
solver: PYPOWER interior point (DC OPF) + Newton-Raphson (ACPF)
timestamp: 2026-03-06T00:00:00Z
---

# P2-3: Commitment injection (simulated SCUC -> DCOPF -> ACPF)

## Result: INFORMATIONAL

## Finding

pandapower can accept externally-determined generator commitment schedules and execute the DCOPF + ACPF feasibility pipeline, but with caveats around the PYPOWER solver's numerical robustness when generators are decommitted.

## Evidence

### Prerequisite: A-5 (SCUC)

A-5 FAILED -- pandapower has no native SCUC capability. This test simulates an external SCUC schedule by manually decommitting generators.

### Step 1: Commitment Injection

**Method tested:** Set `net.gen.at[idx, "max_p_mw"] = 0` and `min_p_mw = 0` for decommitted generators.

**Alternative method:** `net.gen.at[idx, "in_service"] = False` -- this is the natural pandapower API for decommitting elements, but causes the PYPOWER interior point solver to diverge numerically on case39. This appears to be a solver robustness issue: the solver produces lambda values on the order of 1e25, indicating numerical instability in the interior point method when the generator set changes.

**Effort level:** Low -- single DataFrame cell assignment per generator. No model rebuild required.

### Step 2: DCOPF with Fixed Commitment

Decommitted generator 6 (bus 36, 564 MW capacity). The PYPOWER solver was sensitive to which generator was decommitted -- several choices caused solver divergence. A trial loop found gen 6 as a feasible decommitment.

| Metric | Value |
|--------|-------|
| DCOPF converged | Yes |
| Objective | 46,333.27 |
| Gen 6 dispatch | ~0 MW (effectively decommitted) |
| Total generation | 6,254.23 MW |
| Total load | 6,254.23 MW |
| LMP range | 16.67 (uniform) |

### Step 3: ACPF Feasibility Check

Fixed generator dispatch to DCOPF values, then ran AC power flow with flat start.

| Metric | Value |
|--------|-------|
| ACPF converged | Yes |
| V min / V max | 0.982 / 1.064 pu |
| Buses with V > 1.05 | 2 |
| Buses with V < 0.95 | 0 |
| Max line loading | 78.7% |
| Overloaded lines | 0 |
| Slack bus P difference | +45.2 MW (losses) |

### Capability Summary

| Step | Capability | API Friction |
|------|------------|-------------|
| Commitment injection | Yes | Low -- DataFrame assignment |
| DCOPF with commitments | Yes (with caveats) | Medium -- solver sensitivity |
| ACPF feasibility check | Yes | Low -- same-model workflow |
| Full pipeline | Yes | Medium overall |

### API Friction Details

1. **`in_service=False` causes solver divergence:** The natural pandapower decommitment API (`in_service=False`) does not work reliably with the PYPOWER interior point solver on this case. The workaround of setting `max_p_mw=0` achieves the same effect but is less semantically clear.

2. **Solver sensitivity:** The PYPOWER interior point solver is numerically fragile for certain generator configurations. Not all single-gen decommitments converge -- the test had to try multiple generators to find one that works. This is a solver limitation, not an API limitation.

3. **No commitment constraint API:** There is no formal "commitment" concept in pandapower. Decommitment must be simulated via power limits or in_service flags. This is expected for a steady-state tool without SCUC.

## Workarounds

The `max_p_mw=0` approach for decommitting generators (instead of `in_service=False`) is a workaround for PYPOWER solver fragility. Classification: **stable** -- uses documented public API (`max_p_mw` is a standard gen parameter) in a non-obvious way.

## Timing

- **Wall-clock:** 1.82 s (including trial loop for feasible decommitment)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/p2_readiness/test_p2_3_commitment_injection.py`
