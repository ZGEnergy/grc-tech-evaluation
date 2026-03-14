---
test_id: G-3
tool: matpower
dimension: gate
network: MEDIUM
status: PASS
workaround_class: null
timestamp: "2026-03-14T04:25:17Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "2da513c6"
---

# G-3: Ingest ACTIVSg 10k (MEDIUM)

## Result: PASS

## Network Counts

| Metric     | Expected | Actual | Match |
|------------|----------|--------|-------|
| Buses      | 10000    | 10000  | OK    |
| Branches   | 12706    | 12706  | OK    |
| Generators | 2485     | 2485   | OK    |

## Load Performance

- Load time: 0.691 s
- Method: `loadcase()` — native MATPOWER function, reads .m case file directly

## Post-Import Audit

| Check                | Result |
|----------------------|--------|
| NaN in bus data      | 0      |
| NaN in branch data   | 0      |
| NaN in gen data      | 0      |
| gencost rows         | 2485 (matches gen count) |
| NaN in gencost       | 0      |
| Branch flow limits   | 10244 nonzero, 2462 zero (of 12706) |
| Slack bus present     | Yes — Bus 40845 (type 3) |

## Notes

The ACTIVSg 10000-bus synthetic grid loads cleanly in MATPOWER. All structural data
is complete with no missing values and cost data is provided for all generators. A
single slack bus is present.

Of the 12706 branches, 2462 (19.4%) have zero RATE_A (no thermal limit specified).
This is expected for this test case and does not constitute a data quality failure --
zero RATE_A in MATPOWER is interpreted as unconstrained (infinite capacity). These
branches will not produce binding flow constraints in OPF formulations but will
correctly participate in power flow calculations.
