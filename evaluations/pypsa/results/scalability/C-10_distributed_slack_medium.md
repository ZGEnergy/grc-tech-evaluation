---
test_id: C-10
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 01f7b63a
status: partial_pass
workaround_class: blocking
blocked_by: A-11
wall_clock_seconds: 698.17
timing_source: measured
peak_memory_mb: 4406.3
cpu_threads_used: 1
cpu_threads_available: 32
loc: 221
solver: highs
timestamp: 2026-03-24T12:00:00Z
---

# C-10: Distributed Slack DC OPF on MEDIUM

## Result: PARTIAL PASS

Distributed slack DC OPF is architecturally blocked in PyPSA 1.1.2. This is a
cascaded finding from A-11: PyPSA's linopy-based DC OPF formulation uses line-flow
variables (Line-s) with Kirchhoff Voltage Law cycle constraints, not bus angle
variables. Without Bus-v_ang variables, there is no angle reference constraint to
distribute across generators. Single-slack DC OPF completes successfully (objective
$1,306,775; 6,017 distinct LMPs).

## Approach

1. Loaded ACTIVSg10k via shared `matpower_loader.load_pypsa()` with
   `overwrite_zero_s_nom=99999.0`.
2. Ran single-slack DC OPF with HiGHS as baseline — recorded objective and LMPs.
3. Inspected linopy model variables: confirmed `Bus-v_ang` absent; only
   `Generator-p`, `Line-s`, `Transformer-s` present.
4. Attempted distributed slack AC PF (`n.pf(distribute_slack=True)`) as alternative
   demonstration — this is the only distributed slack capability PyPSA offers, but it
   operates in the PF domain (no LMPs, no optimization).

## Output

### Single-Slack DC OPF (Baseline)

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Status | Optimal |
| Objective | $1,306,775.11 |
| Wall-clock (n.optimize) | 634.2s |
| HiGHS internal solve | ~7.9s (5,346 simplex iterations) |
| Peak memory | 4,406.3 MB |

### LMP Statistics (Single-Slack)

| Metric | Value |
|--------|-------|
| Mean LMP | $19.54/MWh |
| Min LMP | -$23.79/MWh |
| Max LMP | $195.07/MWh |
| Std deviation | $3.43 |
| Distinct LMP values | 6,017 |

Note: ACTIVSg10k has no binding branch constraints in base-case DCOPF (per
cross-tool-watchpoints.md). The 6,017 distinct LMP values and negative LMPs suggest
the gencost-derived marginal costs create locational price differentiation, though the
network is uncongested.

### Architecture Check

| Variable | Present in linopy model |
|----------|------------------------|
| Generator-p | yes |
| Line-s | yes |
| Transformer-s | yes |
| Bus-v_ang | **no** |

**Distributed slack OPF status:** BLOCKED [tool-specific]

PyPSA's DC OPF KVL is expressed via line-flow variables with cycle constraints, not
bus angle variables. There is no angle reference constraint to distribute. This is an
architectural design choice in PyPSA/linopy, not a solver limitation.

### Distributed Slack AC PF (Alternative)

| Metric | Value |
|--------|-------|
| Converged | no |
| Iterations | 59 (max) |
| Residual | NaN |
| Wall-clock | 54.7s |
| Peak memory | 2,098.8 MB |

The AC PF with distributed slack did not converge on ACTIVSg10k with the OPF dispatch
as starting point. This is expected for a large network with AC PF from a DC dispatch
point. Even if it had converged, AC PF does not produce dual variables (LMPs), so no
LMP comparison with the single-slack OPF would be possible.

## Workarounds

- **What:** Distributed slack DC OPF is not achievable in PyPSA 1.1.2.
- **Why:** The linopy model formulation uses line-flow variables (not bus angles).
  There is no angle reference constraint to distribute across generators.
- **Durability:** blocking — requires architectural change to PyPSA's OPF formulation
  to introduce bus angle variables.
- **Grade impact:** C-10 scores partial_pass. The single-slack OPF works correctly at
  MEDIUM scale, demonstrating solver scalability, but the distributed slack capability
  is absent for OPF.
- **Cascaded from:** A-11 (distributed slack partial_pass/blocking on TINY)

## Timing

- **Wall-clock (total):** 698.17s
- **Single-slack OPF:** 634.2s (HiGHS internal: ~7.9s, linopy overhead: ~626s)
- **Distributed slack AC PF:** 54.7s (non-convergent)
- **Timing source:** measured
- **Peak memory:** 4,406.3 MB (single-slack OPF)
- **CPU threads used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c10_distributed_slack_medium.py`
