---
test_id: B-9
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "d8e7210b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.12
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 255
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# B-9: Compute PTDF matrix and verify against DCPF flows

## Result: PASS

## Approach

pandapower provides PTDF computation via the inherited PYPOWER function `pandapower.pypower.makePTDF.makePTDF()`. The function takes the PYPOWER-format bus and branch arrays from the internal `net._ppc` representation and returns the full nbr x nb PTDF matrix.

**Workflow:**
1. Loaded case39 network and solved DCPF via `pp.rundcpp(net)`
2. Extracted internal PYPOWER representation from `net._ppc`
3. Computed PTDF matrix via `makePTDF(baseMVA, bus, branch)`
4. Reconstructed bus injections and DCPF branch flows from `makeBdc` matrices
5. Compared PTDF-predicted flows against DCPF flows

**Phase-shifter handling:** The case39 network as loaded by pandapower's `from_mpc` converter has zero phase-shifting transformers in the internal PYPOWER representation (all SHIFT values are 0.0). pandapower promotes branches with non-unity tap ratios to transformer elements, but the SHIFT angle column remains zero. Therefore, no Pbusinj/Pfinj corrections were needed, and the raw PTDF comparison is valid.

## Output

### PTDF Matrix Properties

| Property | Value |
|----------|-------|
| Shape | 46 x 39 (branches x buses) |
| Compute time | 0.6 ms |
| Rank | 38 (= nb - 1, as expected) |
| Min value | -1.000 |
| Max value | 1.000 |
| Sparsity | 39.2% of entries below 1e-10 |

### Flow Validation

| Comparison | Max Diff (MW) | Mean Diff (MW) | Within 1e-6? |
|------------|--------------|----------------|--------------|
| Raw (H @ Pinj) | 1.59e-12 | 3.29e-13 | Yes |
| Corrected (H @ Pinj + Pfinj) | 1.59e-12 | 3.29e-13 | Yes |

The PTDF-predicted flows match DCPF flows to machine precision (max error ~1.6 picowatts). The raw and corrected comparisons are identical because there are no phase-shifting transformers.

### Worst Branch

| Property | Value |
|----------|-------|
| Branch index | 11 |
| From bus | 5 |
| To bus | 10 |
| Max difference | 1.59e-12 MW |
| Phase shifter? | No |

### Phase-Shifter Analysis

The case39 network has 0 phase-shifting transformers in the internal PYPOWER representation. While pandapower promotes 11 branches with non-unity tap ratios to transformer elements, these have zero SHIFT angle, so no Pbusinj/Pfinj correction is needed.

### Sample DCPF Flows vs PTDF Predictions (first 5 branches)

| Branch | DCPF Flow (MW) | PTDF Flow (MW) | Diff (MW) |
|--------|---------------|----------------|-----------|
| 0 | -178.354 | -178.354 | 1.14e-13 |
| 1 | 80.754 | 80.754 | 1.42e-14 |
| 2 | 333.430 | 333.430 | 5.68e-14 |
| 3 | -261.784 | -261.784 | 5.68e-14 |
| 4 | 54.115 | 54.115 | 2.13e-14 |

## Workarounds

None required. The PTDF matrix is accessible via a native API function (`makePTDF`) that is part of pandapower's PYPOWER subsystem. The function is documented (inherits PYPOWER documentation) and takes standard PYPOWER bus/branch arrays. Access to these arrays requires the internal `net._ppc` attribute (set after solving DCPF), but this is the standard pandapower pattern for accessing PYPOWER-level data.

## Timing

- **Wall-clock:** 1.12 s (network load + DCPF solve + PTDF computation + validation)
- **Timing source:** measured
- **PTDF computation:** 0.6 ms
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b9_ptdf_extraction.py`

Key API call:

```python
from pandapower.pypower.makePTDF import makePTDF

ppc = net._ppc
H = makePTDF(ppc["baseMVA"], ppc["bus"], ppc["branch"])
# H is a numpy array of shape (nbr, nb)
```
