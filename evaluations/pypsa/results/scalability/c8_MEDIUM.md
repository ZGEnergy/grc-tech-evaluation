---
test_id: c8
tool: pypsa
dimension: scalability
network: MEDIUM
status: fail
wall_clock_seconds: 23.04
peak_memory_mb: 2114.14
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# C-8: SCOPF on MEDIUM (ACTIVSg 10k) with 500 Line Contingencies

## Result: FAIL

## Approach
Loaded the ACTIVSg 10k-bus network with gencost data. Selected the top 500 lines by base-case DCPF flow magnitude. Called `n.optimize.optimize_security_constrained(branch_outages=top_500_lines)` with HiGHS.

Two attempts were made:
1. **Attempt 1 (s_nom=9999)**: The PTDF-based security constraint matrix contained 8,894 inf values from the high s_nom on zero-rated branches. HiGHS refused to solve: "Cannot solve a model with a |value| exceeding 1e+15 in constraint matrix."
2. **Attempt 2 (s_nom=max of non-zero)**: Used the maximum existing non-zero s_nom instead of 9999. Still produced 6,810 inf values in the constraint matrix from disconnected sub-components when certain lines are outaged.

Both attempts failed because some of the 500 monitored line outages create disconnected sub-networks, producing infinite PTDF sensitivity factors that HiGHS cannot handle.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Contingencies | 500 |
| SCOPF model rows | 12,749,089 |
| SCOPF model cols | 15,191 |
| SCOPF model nonzeros | 21,719,229 |
| Inf values in matrix | 6,810-8,894 |
| HiGHS status | Not Set (refused) |
| Wall-clock | 23.04s (model build only) |
| Peak memory | 2,114.14 MB |

## Timing
- Wall-clock: 23.04s (model building, solver refused immediately)
- Peak memory: 2,114.14 MB
- CPU cores: 1

## Notes
- PyPSA's `optimize_security_constrained()` method uses PTDF-based security constraints. When a line outage creates a disconnected sub-network, the PTDF entries become infinite, making the LP infeasible.
- The ACTIVSg 10k case has many radial branches whose outage disconnects parts of the network. These lines should be filtered from the contingency list, but `optimize_security_constrained()` does not do this automatically.
- A workaround would be to pre-filter contingencies to exclude lines whose outage disconnects the network (i.e., bridge edges in the graph). However, this was not implemented as it would require custom graph analysis code beyond what PyPSA provides.
- The SCOPF functionality itself works correctly -- the failure is due to the combination of the specific network topology and the contingency selection, not a PyPSA bug.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c8_scopf_scale.py`
