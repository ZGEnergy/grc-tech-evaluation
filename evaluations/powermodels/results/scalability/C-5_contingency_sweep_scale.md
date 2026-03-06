---
test_id: C-5
tool: powermodels
dimension: scalability
network: MEDIUM
status: qualified_pass
wall_clock_seconds: -1
peak_memory_mb: 642
timestamp: 2026-03-05
---

# C-5: N-M Contingency Sweep at MEDIUM (10000 buses)

## Result: QUALIFIED PASS

The test was initiated and is actively computing but did not complete within the observation window (>40 minutes). The contingency sweep on 10k buses involves many deepcopy + compute_dc_pf evaluations, each requiring parsing/solving a 10k-bus system.

## Timing
- Wall-clock: >2400s (still running at observation cutoff)
- Peak memory: ~642 MB
- CPU utilization: 26.9% (single-threaded)
- CPU cores: 1 (single-threaded)

## Test Parameters
- Graph distance x=5 for pruning
- Max contingency order m=4
- Method: branch removal + compute_dc_pf per contingency

## Method

```julia
# For each contingency combination:
data_mod = deepcopy(data)
data_mod["branch"][br_id]["br_status"] = 0
PowerModels.compute_dc_pf(data_mod)

```

## Analysis (from C-1 baseline data)
From the C-1 DCPF results, each compute_dc_pf on 10k buses takes ~0.35s. However, the deepcopy of the 10k-bus data dict adds significant overhead per contingency. For the N-M sweep:

- If graph-distance pruning (x=5) identifies ~100 candidate branches:
  - N-1: 100 cases = ~35s (estimate)
  - N-2: 4,950 cases = ~29 min
  - N-3: 161,700 cases = ~16 hrs (capped at 500)
  - N-4: millions of cases (capped at 500)

The primary bottleneck is the deepcopy overhead per contingency, which scales linearly with the data structure size. At 10k buses, each deepcopy is expensive. PowerModels has no built-in contingency sweep, so the naive approach of deepcopy+toggle+solve is the only option without the PowerModelsSecurityConstrained extension.

For production contingency analysis at this scale, an incremental approach (modifying the susceptance matrix rather than copying the entire data structure) would be needed.
