---
test_id: P2-3
tool: matpower
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: 2.0477
peak_memory_mb: null
loc: 155
solver: GLPK
timestamp: "2026-03-06T00:00:00Z"
---

# P2-3: Commitment Injection Workflow

## Result: INFORMATIONAL -- Full Pipeline Demonstrated

## Workflow Summary

Three-step pipeline successfully demonstrated:
1. **SCUC** (get commitment) -> 2. **DCOPF** (locked commitment) -> 3. **AC PF** (feasibility check)

All three steps use native MATPOWER/MOST APIs with low effort and no workarounds
(apart from the standard GLPK/PWL workaround for the SCUC stage).

## Step-by-Step Results

### Step 1: SCUC (Get Commitment Schedule)

- **API:** `most(mdi, mpopt)` with `most.uc.run = 1`
- **Output:** `mdo.UC.CommitSched` -- ng x nt binary matrix
- **Result:** Converged, objective = 837,041.61
- **Effort:** LOW -- direct field access, no parsing or conversion needed
- **Friction:** None. The MOST framework provides the commitment schedule as a
  structured output. No need to extract from raw solver variables.

### Step 2: Lock Commitments + DCOPF

- **API:** Set `mpc.gen(g, GEN_STATUS) = 0` for uncommitted generators, then `rundcopf(mpc)`
- **Load scaling:** `mpc.bus(:, PD) *= daily_curve(t)` per period
- **Effort:** LOW -- 5 lines of code per period (scale load, lock gens, solve)

Tested on three representative periods:

| Period | Load Factor | Gens Off | Objective ($/hr) | Total Dispatch (MW) |
|--------|-------------|----------|-------------------|-------------------|
| HE04   | 0.77        | 0        | 24,638.24         | 4,815.8           |
| HE10   | 1.00        | 0        | 41,263.94         | 6,254.2           |
| HE19   | 1.00        | 0        | 41,263.94         | 6,254.2           |

All DCOPF solves converged. Zero generators were off because the UC solution kept
all 10 committed (case39 capacity vs load ratio makes this optimal).

**Friction:** Very low. The `GEN_STATUS` column in the gen matrix is the standard
mechanism for enabling/disabling generators. No special API or mode needed.

### Step 3: AC Power Flow Feasibility Check

- **API:** Inject PG from DCOPF into gen matrix, then `runpf(mpc)`
- **Period tested:** HE19 (peak load, load factor = 1.00)
- **Result:** AC PF converged

| Metric | Value |
|--------|-------|
| AC PF converged | Yes |
| Voltage range | 0.9820 -- 1.0636 pu |
| Max voltage deviation from 1.0 | 0.0636 pu |
| Voltage violations (0.95--1.05 pu) | 5 / 39 buses |
| Reactive power limit violations | 1 / 10 generators |
| AC feasibility | MARGINAL (voltage violations) |

The DC OPF dispatch is AC-feasible (PF converges) but produces some voltage limit
violations. This is expected: DC OPF ignores reactive power and voltage magnitude,
so the AC feasibility check reveals gaps. In a production workflow, an AC OPF or
voltage-corrected dispatch would follow.

**Effort:** LOW -- inject PG values into gen matrix column, call `runpf()`. Three
lines of code.

## Pipeline Capability Assessment

| Step | Capability | Effort | API Friction |
|------|-----------|--------|-------------|
| SCUC (get commitment) | Native (MOST) | Low | None -- structured output |
| Lock commitment + DCOPF | Native | Low | None -- GEN_STATUS column |
| AC PF feasibility | Native | Low | None -- runpf() with injected PG |
| **Overall** | **Fully capable** | **Low** | **Minimal** |

## Key API Patterns

### Commitment Extraction

```matlab
mdo = most(mdi, mpopt);                    % Run SCUC
commit = mdo.UC.CommitSched;               % ng x nt binary matrix
```

### Commitment Injection (per-period DCOPF)

```matlab
mpc_t = loadcase(network_file);
mpc_t.bus(:, PD) *= load_factor(t);        % Scale load
for g = 1:ng
    if commit(g, t) < 0.5
        mpc_t.gen(g, GEN_STATUS) = 0;      % Lock off
    end
end
results = rundcopf(mpc_t, mpopt);          % Solve DCOPF
```

### AC Feasibility Check

```matlab
mpc_ac = mpc_t;
mpc_ac.gen(:, PG) = results.gen(:, PG);    % Inject DCOPF dispatch
results_pf = runpf(mpc_ac, mpopt_pf);      % AC power flow
```

## Observations

1. **No glue code needed:** MATPOWER's consistent struct-based API means the same
   `mpc` struct flows through SCUC, DCOPF, and PF without format conversion.
2. **Per-period vs multi-period:** The per-period DCOPF approach (Step 2) loses
   inter-temporal ramp constraints. For ramp-constrained ED, use MOST with
   `uc.run = 0` and `mdi.UC.CommitSched` injection (as demonstrated in A-6).
3. **AC feasibility gap:** The DC-to-AC gap (voltage violations) is inherent to
   the DC approximation, not a MATPOWER limitation. Production workflows would
   use AC OPF or iterative DC/AC correction.

## Test Script

`evaluations/matpower/tests/p2_readiness/test_p2_3_commitment_injection_tiny.m`
