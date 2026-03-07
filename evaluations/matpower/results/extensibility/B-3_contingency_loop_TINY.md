---
test_id: B-3
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 2.3769
peak_memory_mb: null
loc: 75
timestamp: "2026-03-06T13:00:00Z"
---

# B-3: Contingency Loop (N-1 DCPF) on TINY (IEEE 39-bus)

## Result: PASS

## Approach

Load the case struct once with `loadcase()`, then iterate over all 46 branches.
For each contingency:
1. Set `mpc.branch(k, BR_STATUS) = 0` (disable branch -- in-place struct mutation)
2. Solve `rundcpf(mpc, mpopt)` (DCPF on the modified struct)
3. Record max line loading from `results.branch(:, PF)`
4. Set `mpc.branch(k, BR_STATUS) = 1` (restore branch)

No file re-reading, no model re-instantiation, no object reconstruction. The mpc
struct is modified in place and passed directly to the solver each iteration.

## Results

- **Contingencies:** 46 (all branches)
- **Converged:** 35/46 (76%)
- **Diverged:** 11/46 (24%) -- all radial generator stub branches causing islanding
- **Total loop time:** 2.21 s (avg 0.048 s/contingency)
- **Total wall clock:** 2.38 s (including base case and reporting)

### Worst Contingency

Outage of branch 35 (21->22): max loading 192.5% on branch 38 (23->24) at 962.50 MW.

### Top 10 Most Severe Contingencies

| Rank | Outaged Br | From->To | Max Loading | Most-Loaded Br | Flow (MW) |
|------|-----------|----------|-------------|----------------|-----------|
| 1    | 35        | 21->22   | 192.5%      | 38 (23->24)    | 962.50    |
| 2    | 38        | 23->24   | 192.5%      | 35 (21->22)    | 962.50    |
| 3    | 12        | 6->7     | 186.3%      | 10 (5->6)      | 931.55    |
| 4    | 42        | 26->27   | 166.0%      | 46 (29->38)    | 830.00    |
| 5    | 43        | 26->28   | 166.0%      | 46 (29->38)    | 830.00    |
| 6    | 1         | 1->2     | 166.0%      | 46 (29->38)    | 830.00    |
| 7    | 2         | 1->39    | 166.0%      | 46 (29->38)    | 830.00    |
| 8    | 3         | 2->3     | 166.0%      | 46 (29->38)    | 830.00    |
| 9    | 4         | 2->25    | 166.0%      | 46 (29->38)    | 830.00    |
| 10   | 6         | 3->4     | 166.0%      | 46 (29->38)    | 830.00    |

### Diverged Contingencies (Islanding)

All 11 failures are radial branches connecting a single generator to the network:
- Branch 5 (2->30), 14 (6->31), 20 (10->32), 27 (16->19), 32 (19->20),
  33 (19->33), 34 (20->34), 37 (22->35), 39 (23->36), 41 (25->37), 46 (29->38)

These outages create electrically isolated islands, causing the DC power flow
B-matrix to become singular. This is expected physical behavior, not a tool defect.

### Timing

| Metric | Value |
|--------|-------|
| Min per-contingency | 0.034 s |
| Max per-contingency | 0.069 s |
| Mean per-contingency | 0.048 s |
| Total loop (46 ctg) | 2.21 s |

## API Friction Analysis

**Near-zero friction.** The in-place struct modification pattern is the simplest
possible contingency loop:
- No model "rebuild" or "update" step required
- No special contingency API needed
- Direct matrix element access: `mpc.branch(k, BR_STATUS) = 0`
- Standard solver call: `rundcpf(mpc, mpopt)`

The singular-matrix warnings for islanding contingencies are emitted by Octave's
linear solver, not caught cleanly by MATPOWER. The `results.success` flag correctly
reports failure, but the warnings are noisy. Suppressing them would require
`warning('off', ...)` wrappers.

## Observations

- **arch-quality:** The mpc struct's mutability is a strength for contingency analysis.
  No intermediate "model object" rebuild step is needed between iterations.
- **api-friction:** Essentially none. The pattern is a textbook for-loop with
  one-line enable/disable. MATPOWER does not provide a built-in N-1 screening
  function, but the manual loop is trivial (~15 lines of core logic).

## Test Script

`evaluations/matpower/tests/extensibility/test_b3_contingency_loop_tiny.m`
