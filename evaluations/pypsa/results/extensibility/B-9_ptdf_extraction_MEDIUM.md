---
test_id: B-9
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-9: PTDF extraction (MEDIUM -- ACTIVSg10k)

## Result: FAIL

## Details

`SubNetwork.calculate_PTDF()` fails on the 10,000-bus network with a singular matrix error.

**Error:** `RuntimeError: Factor is exactly singular` during `scipy.sparse.linalg.spsolve`
when computing `B_inverse = spsolve(B[1:, 1:], identity)`.

**Root cause:** The ACTIVSg10k MATPOWER case contains branches with zero series impedance
(x = 0), which makes the susceptance matrix B singular. The PTDF computation requires
inverting B, which is impossible when B is singular.

**Stack trace:**

```
sn.calculate_PTDF()
  -> B_inverse = spsolve(csc_matrix(self.B[1:, 1:]), identity)
    -> splu(A).solve
      -> RuntimeError: Factor is exactly singular
```

**Note:** This is a data issue (zero-impedance branches), not a tool limitation. The PTDF
extraction works correctly on the TINY (case39) network. For the MEDIUM network, the user
would need to replace zero impedances with small values before computing PTDF.
