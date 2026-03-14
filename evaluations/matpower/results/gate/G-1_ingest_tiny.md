---
test_id: G-1
tool: matpower
dimension: gate
network: TINY
status: PASS
workaround_class: null
timestamp: "2026-03-14T04:25:17Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "0a74adbf"
---

# G-1: Ingest IEEE 39-bus (TINY)

## Result: PASS

## Network Counts

| Metric     | Expected | Actual | Match |
|------------|----------|--------|-------|
| Buses      | 39       | 39     | OK    |
| Branches   | 46       | 46     | OK    |
| Generators | 10       | 10     | OK    |

## Load Performance

- Load time: 0.015 s
- Method: `loadcase()` — native MATPOWER function, reads .m case file directly

## Post-Import Audit

| Check                | Result |
|----------------------|--------|
| NaN in bus data      | 0      |
| NaN in branch data   | 0      |
| NaN in gen data      | 0      |
| gencost rows         | 10 (matches gen count) |
| NaN in gencost       | 0      |
| Branch flow limits   | 46 nonzero, 0 zero (all branches have RATE_A) |
| Slack bus present     | Yes — Bus 31 (type 3) |

## Notes

MATPOWER loads its native .m case format without any conversion or adaptation. The
IEEE 39-bus (New England) test case is a standard MATPOWER distribution case. All
structural data is complete with no missing values, all branches have thermal limits
defined, and a single slack bus is present.
