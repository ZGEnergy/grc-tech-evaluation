---
test_id: B-5
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 2.487
timestamp: 2026-03-05
---

# B-5: Export DCPF Results to CSV [MEDIUM]

## Result: PASS

## Approach
Same as TINY: DCPF solve, then manual CSV export via Julia I/O (DataFrames.jl and CSV.jl not in Project.toml).

## Output
- Bus CSV: 10000 rows (bus_id, va_rad)
- Branch CSV: 12706 rows (branch_id, pf_pu, pt_pu)
- Files written to `results/extensibility/B-5_*_MEDIUM.csv`

## Lines Beyond Solve
4 lines (2 open/write blocks for bus and branch CSVs)

## Timing
- Wall-clock: 2.5s
