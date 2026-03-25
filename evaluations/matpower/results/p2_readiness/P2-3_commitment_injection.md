---
test_id: P2-3
tool: matpower
dimension: p2_readiness
network: N/A
protocol_version: v11
skill_version: v2
test_hash: "94cd2962"
status: informational
workaround_class: null
timestamp: 2026-03-24T12:00:00Z
---

# P2-3: Commitment Injection Workflow

## Capability Per Step

The three-stage workflow (lock UC, solve DCOPF, AC feasibility) maps cleanly to MATPOWER's
existing API surface. Each stage uses a single well-documented function call.

### Stage 1: Lock UC Commitment

**Capability:** YES -- direct via `GEN_STATUS` field.

Unit commitment decisions are injected by setting `mpc.gen(i, GEN_STATUS) = 0` for
decommitted generators and `= 1` for committed generators. This is a single column in the
generator matrix (column 8, constant `GEN_STATUS` from `idx_gen`). No wrapper function is
needed -- it is a direct matrix assignment.

When using MOST for the UC stage, the commitment schedule is available in the output
`mdo.results.CommitSched` (an ng x nt matrix). This can be transferred to per-period `mpc`
structs by setting `GEN_STATUS` accordingly.

The A-5 evaluation confirmed that MOST solves SCUC successfully via `most()` with
`most.uc.run = 1`. The A-6 evaluation confirmed that the commitment schedule from A-5 can
be injected into per-period `rundcopf()` calls by toggling `GEN_STATUS`.

### Stage 2: Solve DCOPF with Locked Commitment

**Capability:** YES -- `rundcopf(mpc, mpopt)`.

With decommitted generators marked via `GEN_STATUS = 0`, `rundcopf()` solves the DC OPF
over committed generators only. MATPOWER's `ext2int()` automatically removes out-of-service
generators from the internal problem formulation, so no manual filtering is needed.

Ramp constraints are not natively enforced across periods by `rundcopf()` (it solves
single-period snapshots). The A-6 evaluation implemented inter-period ramp enforcement by
tightening `PMAX`/`PMIN` bounds based on the previous period's dispatch:

```octave
mpc.gen(i, PMAX) = min(PMAX_orig, Pg_prev + ramp_limit);
mpc.gen(i, PMIN) = max(PMIN_orig, Pg_prev - ramp_limit);
```

Alternatively, MOST handles inter-period ramp constraints natively via `RAMP_10`/`RAMP_30`
fields in the generator data, but this bundles UC and ED into a single formulation rather
than a clean two-stage separation.

### Stage 3: AC Feasibility Check

**Capability:** YES -- `runpf(mpc, mpopt)`.

The DCOPF solution (dispatch, voltage angles) is passed to `runpf()` for AC power flow
validation. The generator `PG` values from the DCOPF result are used as-is; `runpf()`
solves for voltage magnitudes, reactive power, and losses. Convergence of the AC power flow
confirms that the DCOPF dispatch is AC-feasible.

## Functional Probe

Verified on IEEE 9-bus case:

1. **Lock UC:** Generator 3 decommitted (`GEN_STATUS = 0`).
2. **DCOPF:** Converged successfully. Dispatch: G1=127.56 MW, G2=187.44 MW, G3=0.00 MW.
   Total cost: $6,388.97.
3. **AC feasibility:** Newton-Raphson power flow converged. Voltage range: 1.0007-1.0400 pu
   (within limits). AC-feasible.

## Effort Level

**Low.** The three-stage workflow requires no custom extensions, no workarounds, and no
non-obvious API patterns. Each stage is a single function call with standard arguments.
The only manual work is transferring the commitment schedule (a vector of 0/1 values) into
the `GEN_STATUS` column and, for multi-period problems, tightening ramp bounds between
periods.

## API Friction

**Minimal.** The main friction point is the absence of built-in inter-period ramp
enforcement in `rundcopf()`. Users must manually tighten generator bounds for sequential
DCOPF calls (as demonstrated in A-6). This is straightforward (~5 lines of code per period)
but requires awareness that `rundcopf()` is a single-snapshot solver.

MOST eliminates this friction entirely for users who prefer a bundled UC+ED formulation,
but at the cost of losing the clean stage separation that the commitment injection workflow
demands.

## Sources

- A-5 result (`evaluations/matpower/results/expressiveness/A-5_scuc.md`) -- MOST SCUC
- A-6 result (`evaluations/matpower/results/expressiveness/A-6_sced.md`) -- SCED with locked commitment
- Functional probe run in devcontainer on 2026-03-24
