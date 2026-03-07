---
test_id: B-9
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.60
peak_memory_mb: null
loc: 130
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-9: PTDF matrix extraction and flow verification

## Result: PASS

## Approach

1. Loaded IEEE 39-bus network and ran DCPF via `pp.rundcpp(net)`.
2. Extracted internal `ppc` arrays from `net._ppc` (baseMVA, bus, branch arrays).
3. Computed PTDF matrix via `pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch, slack)`.
4. Built bus injection vector from solved `ppc` gen and bus arrays.
5. Predicted branch flows as `PTDF @ Pbus` and compared against DCPF-solved branch flows.

## Output

### PTDF Matrix Dimensions

| Metric | Value |
|--------|-------|
| PTDF shape | (46, 39) |
| Expected shape | (n_branch x n_bus) = (46, 39) |
| Dimensions correct | Yes |

### PTDF Matrix Statistics

| Metric | Value |
|--------|-------|
| Min value | -1.000 |
| Max value | 1.000 |
| Mean value | -0.0045 |
| Nonzero fraction | 96.7% |
| Slack column all zeros | Yes (correct) |

### Flow Prediction Accuracy

| Metric | Value |
|--------|-------|
| Max abs difference (pu) | 1.07e-14 |
| Mean abs difference (pu) | 3.29e-15 |
| Tolerance | 1e-6 |
| Match quality | Exact (within machine epsilon) |

### Sample Flow Comparison (first 5 branches)

| Branch | DCPF Flow (MW) | PTDF Predicted (MW) | Diff (MW) |
|--------|----------------|---------------------|-----------|
| 0 | -178.35 | -178.35 | 1.78e-13 |
| 1 | 80.75 | 80.75 | 2.11e-13 |
| 2 | 333.43 | 333.43 | 5.33e-13 |
| 3 | -261.78 | -261.78 | 3.55e-13 |
| 4 | 54.12 | 54.12 | 1.07e-12 |

### API Access Method

```python
from pandapower.pypower.makePTDF import makePTDF

net = from_mpc(network_file, f_hz=60)
pp.rundcpp(net)

ppc = net._ppc
PTDF = makePTDF(ppc["baseMVA"], ppc["bus"], ppc["branch"], slack_bus_idx)
```

**Access level:** Semi-internal. `makePTDF` is a public function in a public submodule (`pandapower.pypower.makePTDF`), but its input arrays come from `net._ppc` (underscore-prefixed internal attribute). The function itself is well-documented and supports distributed slack via weight vectors, sparse solvers, and branch subsetting.

## Workarounds

None required. The PTDF computation is native to pandapower's PYPOWER subsystem. The only nuance is that input arrays must be extracted from the internal `_ppc` structure after running a power flow. This is a common pattern in pandapower and is referenced in documentation and examples.

## Timing

- **Wall-clock:** 0.60 s (including DCPF solve + PTDF computation + verification)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b9_ptdf_extraction.py`
