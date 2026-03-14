---
test_id: P2-3
tool: matpower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-14T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "94cd2962"
---

# P2-3: Commitment Injection Workflow (Lock UC -> DCOPF -> AC Feasibility)

## Result: INFORMATIONAL

## Capability Per Step

The three-step workflow (lock UC, solve DCOPF, check AC feasibility) is fully supported
using MATPOWER's public API. Each step was functionally demonstrated in prior evaluation
tests.

| Step | Capability | API | Demonstrated In |
|------|-----------|-----|-----------------|
| 1. Lock UC schedule | Yes | `mpc.gen(:, GEN_STATUS) = commitment_vector` | A-6 (SCED) |
| 2. Solve DCOPF | Yes | `rundcopf(mpc, mpopt)` | A-3 (DCOPF), A-6 (SCED) |
| 3. AC feasibility check | Yes | `runpf(mpc_from_dcopf, mpopt)` | A-4 (AC feasibility) |

### Step 1: Lock UC Schedule

Commitment is injected by setting `GEN_STATUS` (column 8 of the `gen` matrix) to 0
(decommitted) or 1 (committed) for each generator. This is a direct matrix write --
no special API call needed:

```matlab
define_constants;
mpc.gen(g, GEN_STATUS) = 0;  % decommit generator g
mpc.gen(g, GEN_STATUS) = 1;  % commit generator g
```

Decommitted generators are excluded from the dispatch problem entirely. MATPOWER's
OPF and PF solvers both respect `GEN_STATUS`.

**MOST alternative:** For MOST-based workflows, commitment can be fixed via `CommitKey`
in the `xGenData` table: `CommitKey = 2` (forced on) or `CommitKey = -1` (forced off).
This was demonstrated in A-5 (SCUC).

### Step 2: Solve DCOPF with Fixed Commitment

With commitment locked via `GEN_STATUS`, `rundcopf(mpc, mpopt)` solves the economic
dispatch as an LP/QP over the committed generators only. Ramp constraints can be enforced
by tightening `PMAX`/`PMIN` bounds based on the previous period's dispatch:

```matlab
mpc.gen(g, PMAX) = min(original_pmax, prev_dispatch + ramp_limit);
mpc.gen(g, PMIN) = max(original_pmin, prev_dispatch - ramp_limit);
result = rundcopf(mpc, mpopt);
```

This was demonstrated for 24 periods in A-6, averaging 0.039 s per period on the
39-bus case.

### Step 3: AC Feasibility Check

The DCOPF result struct is directly usable as input to `runpf()` (AC power flow). The
workflow transfers the dispatch from DCOPF to ACPF within the same `mpc` struct -- no
file export/reimport needed:

```matlab
mpc_ac = results_dc;
mpc_ac.bus(:, VM) = 1.0;    % flat start voltage magnitudes
mpc_ac.bus(:, VA) = 0;      % flat start angles
mpopt_ac = mpoption('pf.enforce_q_lims', 1);
results_ac = runpf(mpc_ac, mpopt_ac);
```

AC feasibility outputs include:
- Voltage violations (buses outside `[VMIN, VMAX]`)
- Thermal violations (branch flows exceeding `RATE_A`)
- Reactive power limit violations
- System losses

This was demonstrated in A-4, where the 39-bus case showed 3 thermal violations and
1 voltage violation from DC-to-AC mismatch.

## Effort Level

**Zero additional effort.** All three steps use documented, stable MATPOWER API functions.
The workflow requires no custom code beyond straightforward matrix manipulation of the
`mpc` struct. A complete UC-lock -> DCOPF -> ACPF pipeline can be implemented in
approximately 20 lines of Octave/MATLAB.

## API Friction

**Low friction.** Key characteristics:

1. **No serialization barrier.** The `mpc` struct flows directly between steps. DCOPF
   output is the same struct type as ACPF input. No format conversion, file I/O, or
   data model translation needed.

2. **Commitment injection is a matrix write.** Setting `GEN_STATUS` is a single array
   assignment. No API ceremony (no builder pattern, no validation step, no commit call).

3. **Ramp constraints require manual bound tightening.** MATPOWER's single-period
   `rundcopf` does not have built-in inter-temporal ramp constraints. These must be
   enforced by adjusting `PMAX`/`PMIN` before each period's solve. This is documented
   practice but adds ~5 lines of code per period. MOST provides built-in ramp handling
   for multi-period problems.

4. **AC feasibility requires flat-start reset.** The DCOPF result populates voltage
   angles with DC approximation values. For Newton-Raphson convergence, voltage
   magnitudes should be reset to 1.0 pu and angles to 0 before running ACPF. This is
   a 2-line operation but is not documented as a recommended practice -- it was
   discovered empirically in A-4.

## End-to-End Workflow Summary

```matlab
%% Complete UC-lock -> DCOPF -> AC feasibility workflow
define_constants;
mpc = loadcase('case39');
mpopt = mpoption('verbose', 0, 'out.all', 0);

% Step 1: Lock commitment (from external UC solution)
commitment = [1 1 1 1 1 1 0 1 1 1];  % G7 decommitted
for g = 1:size(mpc.gen, 1)
    mpc.gen(g, GEN_STATUS) = commitment(g);
end

% Step 2: Solve DCOPF with locked commitment
results_dc = rundcopf(mpc, mpopt);

% Step 3: AC feasibility check
mpc_ac = results_dc;
mpc_ac.bus(:, VM) = 1.0;
mpc_ac.bus(:, VA) = 0;
mpopt_ac = mpoption(mpopt, 'pf.enforce_q_lims', 1);
results_ac = runpf(mpc_ac, mpopt_ac);

% Extract feasibility metrics
v_violations = sum(results_ac.bus(:, VM) > results_ac.bus(:, VMAX) | ...
                   results_ac.bus(:, VM) < results_ac.bus(:, VMIN));
thermal_violations = sum(abs(results_ac.branch(:, PF)) > results_ac.branch(:, RATE_A));
```
