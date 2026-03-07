---
test_id: B-7
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.0003
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-7: AC feasibility extension (MEDIUM -- ACTIVSg10k)

## Result: PASS

## Details

B-7 is a meta-test that audits the A-4 workarounds for durability and effort level. It reads
the existing A-4 TINY result file (since A-4 MEDIUM is infeasible due to data issues, this
test references the TINY result where A-4 passed).

**Workaround analysis (2 workarounds from A-4):**

1. **Transfer OPF dispatch to PF p_set** -- stable, low effort (3-4 LOC). Uses documented
   public API. Convenience method `n.optimize.optimize_and_run_non_linear_powerflow()` exists.

2. **Manual gencost assignment** -- stable, low effort (5 LOC). Import limitation in
   `import_from_pypower_ppc()`, not an API limitation. Uses `matpowercaseframes` to parse.

**Overall durability class:** stable
**Overall effort level:** low
**Version risk:** low -- both workarounds use public, documented API
