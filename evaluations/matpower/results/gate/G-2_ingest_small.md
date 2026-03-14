---
test_id: G-2
tool: matpower
dimension: gate
network: SMALL
status: PASS
workaround_class: null
timestamp: "2026-03-14T04:25:17Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "84277a12"
---

# G-2: Ingest ACTIVSg 2k (SMALL)

## Result: PASS

## Network Counts

| Metric     | Expected | Actual | Match |
|------------|----------|--------|-------|
| Buses      | 2000     | 2000   | OK    |
| Branches   | 3206     | 3206   | OK    |
| Generators | 544      | 544    | OK    |

## Load Performance

- Load time: 0.127 s
- Method: `loadcase()` — native MATPOWER function, reads .m case file directly

## Post-Import Audit

| Check                | Result |
|----------------------|--------|
| NaN in bus data      | 0      |
| NaN in branch data   | 0      |
| NaN in gen data      | 0      |
| gencost rows         | 544 (matches gen count) |
| NaN in gencost       | 0      |
| Branch flow limits   | 3206 nonzero, 0 zero (all branches have RATE_A) |
| Slack bus present     | Yes — Bus 7098 (type 3) |

## Notes

The ACTIVSg 2000-bus synthetic grid loads cleanly in MATPOWER. All structural data
is complete with no missing values, all branches have thermal limits defined, and a
single slack bus is present. Cost data is provided for all generators.
