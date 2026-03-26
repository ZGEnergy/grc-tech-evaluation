---
test_id: C-8
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "8dd35bb3"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 372
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-8: SCOPF (N-1, 50 contingencies) on MEDIUM

## Result: FAIL

## Approach

pandapower has no native SCOPF capability. Test A-9 (TINY, 39 buses) demonstrated that
SCOPF can be achieved manually using PTDF/LODF construction + `scipy.optimize.linprog`
(HiGHS backend), with pandapower serving only as a data container and PTDF calculator.

This test attempted to scale that manual approach to the ACTIVSg10k network (10,000 buses,
12,706 branches, ~1,937 active generators). Three attempts were made with progressively
more aggressive memory optimizations:

### Attempt 1: Full constraint matrix (dense)

Constructed constraint matrix with all 12,675 limited branches and 50 contingencies.
Matrix dimensions: ~1.3M rows x 1,937 cols. Dense size: ~20 GB.
Result: Process killed (OOM) during matrix construction.

### Attempt 2: Sparse constraint matrix

Used `scipy.sparse.vstack` to build constraints incrementally. Each contingency block
still requires a dense `np.outer` product of size (n_monitored x n_gen) before conversion
to sparse.
Result: Process killed (OOM) — accumulated ~32 GB during block construction.

### Attempt 3: Monitored branches only (loading > 30%)

Filtered to branches with base-case loading > 30% to reduce constraint count.
ACTIVSg10k's uncongested profile (max loading ~77%) still produced several thousand
monitored branches. Each contingency block still generated hundreds of MB of dense
intermediate matrices.
Result: Process killed (OOM) at ~32 GB after ~15 minutes.

### Root Cause Analysis

The SCOPF constraint matrix at 10k-bus scale requires O(n\_contingencies \* n\_branches \* n\_gen)
storage. With 50 contingencies, ~12,000 branches, and ~2,000 generators:

- Each contingency PTDF modification: outer product of (n\_monitored,) x (n\_gen,) = large dense matrix
- Total: ~50 \* n\_monitored \* 1937 \* 8 bytes = multi-GB even with branch filtering
- The PTDF matrix itself (12,706 x 10,000) is ~1 GB

A production SCOPF solver would use Benders decomposition (solve base + contingency subproblems
iteratively) rather than building the full constraint matrix. This is infeasible to construct
manually in Python/NumPy at this scale.

Additionally, the ACTIVSg10k network is largely uncongested (max base-case loading ~77% even
with 90% branch derating), which means N-1 contingency constraints would not produce
meaningful redispatch even if the solve completed.

## Output

| Aspect | Finding |
|--------|---------|
| Native SCOPF | No [tool-specific] |
| Manual approach at TINY (A-9) | Worked (partial_pass) |
| Manual approach at MEDIUM | OOM at ~32 GB [tool-specific: no native SCOPF forces full matrix construction] |
| Benders decomposition available | No [tool-specific] |
| Network congestion | Uncongested (max loading ~77%) |
| Time before OOM kill | ~15 minutes |

## Workarounds

- **What:** Manual PTDF/LODF + scipy LP construction. Works at TINY scale (A-9) but infeasible at MEDIUM due to memory requirements for the full constraint matrix.
- **Why:** pandapower has no native SCOPF and no Benders decomposition. The only path is to construct the full N-1 constraint matrix, which scales as O(contingencies x branches x generators).
- **Durability:** blocking -- no SCOPF path exists at MEDIUM scale, even with the manual workaround that works at TINY [tool-specific: no native SCOPF or iterative decomposition].
- **Grade impact:** Blocking failure. SCOPF at scale is not achievable with pandapower.

## Timing

- **Wall-clock:** N/A (process killed at ~15 minutes)
- **Timing source:** estimated (not completed)
- **Peak memory:** ~32 GB before OOM kill
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c8_scopf_medium.py`
