---
test_id: B-5
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.955
peak_memory_mb: null
loc: 126
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# B-5: Interoperability (MEDIUM, ACTIVSg 10k-bus)

## Result: PASS

## Approach

Same workflow as TINY: solve DCPF via `compute_dc_pf()`, then export results to
Dict-of-arrays (DataFrame-equivalent). No custom serialization needed.

## Output

- **Bus rows exported:** 10,000
- **Branch rows exported:** 12,706
- **Generator rows exported:** 2,485
- **Export time:** 1.955s (including DCPF solve + Dict construction)
- **Custom serialization needed:** No
- **Export method:** Dict comprehension from solution Dict values

The export scales linearly with network size. At TINY (39 buses) the export was
trivial; at MEDIUM (10,000 buses) it remains trivial -- Dict comprehensions and
DataFrame constructors handle any size.

## Workarounds

None. PowerModels returns plain Dict structures that map trivially to DataFrames
or any other tabular format. The approach is identical to TINY.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch2.jl`
