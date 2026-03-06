---
test_id: C-1
tool: powermodels
dimension: scalability
network: MEDIUM
status: pass
wall_clock_seconds: 16.84
peak_memory_mb: 8.3
timestamp: 2026-03-05
---

# C-1: DCPF at MEDIUM (10000 buses)

## Result: PASS

## Timing
- Wall-clock: 16.84s (including 13.67s parse time)
- Solve time (compute_dc_pf only): 0.35s
- Parse time: 13.67s
- Peak memory: 8.3 MB (solve only)
- CPU cores: 1 (single-threaded)

## Output
- Network: 10,000 buses, 12,706 branches, 2,485 generators
- Non-zero bus angles: 9,999 of 10,000
- Branch flows computed: 12,706
- Max flow: 18.51 p.u.
- Mean flow: 0.89 p.u.

## Method
`PowerModels.compute_dc_pf(data)` -- native non-JuMP solver (direct sparse linear solve).

## Analysis
DC power flow scales very well to 10k buses. The solve itself takes only 0.35s; the dominant cost is parsing the MATPOWER file (13.67s). The native solver avoids JuMP model construction overhead entirely, making it fast for repeated evaluations (e.g., contingency sweeps).
