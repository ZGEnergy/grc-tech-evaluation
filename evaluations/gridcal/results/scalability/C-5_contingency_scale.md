---
test_id: C-5
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 575.29
peak_memory_mb: 72.55
loc: 65
solver: "Direct (SolverType.Linear)"
timestamp: 2026-03-06T04:00:00Z
---

# C-5: Contingency Sweep Scale (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

N-M contingency sweep with graph-distance scoping (x=5, m=4). Manual `branch.active` toggle and re-solve loop using NetworkX for graph distance. Candidates capped at 10 branches (from 90 in the neighborhood) to keep total cases at 385.

## Output

| Metric | Value |
|--------|-------|
| Total wall clock | 575.29s (~9.6 min) |
| Peak memory (sweep) | 72.55 MB |
| Cases evaluated | 385 |
| Center bus | index 1385 (degree 20) |
| Buses within distance 5 | 67 |
| Candidate branches (total) | 90 |
| Candidate branches (used) | 10 |
| All cases converged | Yes |

### Results by Contingency Order

| Order | Cases | Max Load Loss (MW) | Non-converged |
|-------|-------|-------------------|---------------|
| N-1 | 10 | 6.36 | 0 |
| N-2 | 45 | 10.07 | 0 |
| N-3 | 120 | 12.92 | 0 |
| N-4 | 210 | 13.16 | 0 |

## Scaling

Each DCPF solve takes ~1.5s on the 10k-bus network. With 385 cases, total time is ~575s. The graph-distance scoping limits the combinatorial explosion. No pruning occurred (all N-1 contingencies had measurable load loss > 1e-3 MW), so all 385 combinations were evaluated.

## Workarounds

Manual `branch.active` toggle and re-solve loop with NetworkX graph distance scoping. Same stable workaround as expressiveness and extensibility tiers. GridCal has no native N-M contingency sweep API.

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c5_contingency_scale.py`
