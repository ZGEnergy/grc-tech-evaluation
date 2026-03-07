---
test_id: B-9
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.025
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-9: PTDF Extraction

## Result: PASS

## Approach

Extracted the PTDF matrix using PyPSA's native `SubNetwork.calculate_PTDF()` method
and verified it against DCPF-solved flows.

1. Loaded case39 network and ran `n.lpf()` to get reference DCPF flows.
2. Called `n.determine_network_topology()` to identify sub-networks.
3. Called `sn.calculate_PTDF()` on the sub-network object, which computes PTDF = H @ B^-1
   and stores it as `sn.PTDF` (dense numpy ndarray).
4. Built nodal injection vector in the correct column ordering.
5. Computed predicted flows as `PTDF @ injections` and compared against DCPF flows.

Key API calls:

```python
n.determine_network_topology()
sn = n.sub_networks.obj.iloc[0]
sn.calculate_PTDF()
ptdf = sn.PTDF  # numpy array, shape (n_branches, n_buses)
```

**Critical detail:** The PTDF column ordering is `[slack_bus] + list(sn.pvpqs)`, which
differs from `sn.buses_i()`. The injection vector must be constructed in this order for
correct flow predictions. The slack bus column is all zeros (as expected for a DC PTDF
with the slack as reference). This ordering is not documented; it was determined by
reading the `calculate_PTDF` source code and testing.

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | (46, 39) |
| Expected shape | (46, 39) |
| Shape correct | Yes |
| Max flow difference | 1.88e-12 |
| Mean flow difference | 4.21e-13 |
| Flows match (tol=1e-6) | Yes |
| Slack bus | 31 |
| Slack column max(abs) | 0.0 |
| PTDF computation time | 0.023s |

Top 5 largest flows (verification):

| Branch | DCPF Flow (MW) | PTDF Predicted (MW) | Abs Diff |
|--------|---------------|--------------------:|----------|
| Transformer-T10 | -830.00 | -830.00 | 2.27e-13 |
| Transformer-T2 | -650.00 | -650.00 | 1.14e-13 |
| Transformer-T8 | -650.00 | -650.00 | 0.00 |
| Transformer-T6 | -632.00 | -632.00 | 0.00 |
| Transformer-T1 | -625.03 | -625.03 | 4.55e-13 |

## Workarounds

None required. `SubNetwork.calculate_PTDF()` is a native public API method that directly
produces the PTDF matrix as a numpy array. The only non-obvious aspect is the column
ordering, which requires knowledge of the internal bus reordering (slack first, then
pvpqs). This is a documentation gap rather than a workaround.

## Timing

- **Wall-clock:** 0.025s (PTDF computation + flow verification)
- **PTDF computation only:** 0.023s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction.py`
