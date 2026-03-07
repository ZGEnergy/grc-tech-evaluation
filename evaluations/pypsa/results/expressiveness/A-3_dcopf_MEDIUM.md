---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 23.473
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-3: Solve DC OPF (MEDIUM -- ACTIVSg10k)

## Result: FAIL

## Details

The DC OPF (`n.optimize()`) is **infeasible** on the ACTIVSg10k 10,000-bus network.

**Root cause:** The MATPOWER case file contains 2,462 branches with `s_nom == 0`. PyPSA
interprets `s_nom == 0` as a zero-capacity line constraint, making the OPF infeasible
because power cannot flow through those branches. The HiGHS solver detects infeasibility
during presolve (0.22s).

**LP statistics:**
- 43,088 rows, 15,191 columns, 331,954 nonzeros
- Status: Infeasible (detected in presolve)
- 2,485 generators with manually assigned marginal costs from gencost data

**Workaround applied:**
- Manually set `marginal_cost` on all 2,485 generators from parsed gencost data
  (PyPSA's PPC importer does not import gencost)

**Note:** This is a data-preparation issue, not a tool limitation. The `overwrite_zero_s_nom`
parameter in `import_from_pypower_ppc()` or manual s_nom fixup before optimization would
likely resolve the infeasibility. The TINY (case39) test passed because that network does
not have zero-s_nom branches.
