# B-9: PTDF Matrix Extraction (TINY)

- **Test ID:** B-9
- **Slug:** ptdf_extraction
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

Compute PTDF matrix. Verify dimensions (branches x buses). Verify flow predictions match DCPF.

## Results

| Metric | Value |
|--------|-------|
| Wall clock (topology + PTDF calculation) | 0.016 s |
| PTDF shape | (46, 39) = branches x buses |
| PTDF type | numpy ndarray (float64) |
| PTDF density | 0.898 |
| PTDF value range | [-1.0, 1.0] |
| Max prediction error | 1.88e-12 MW |
| Mean prediction error | 0.0 MW (rounded) |
| LOC | 5 lines |

### Dimensions

| Component | Count |
|-----------|-------|
| Sub-networks | 1 |
| Branches (rows) | 46 (35 lines + 11 transformers) |
| Buses (columns) | 39 |

### Flow Prediction Verification

| Branch | Actual (MW) | Predicted (MW) | Error (MW) |
|--------|------------|----------------|------------|
| Line:L0 | -178.354 | -178.354 | ~0 |
| Line:L1 | 80.754 | 80.754 | ~0 |
| Line:L2 | 333.430 | 333.430 | ~0 |
| Line:L3 | -261.784 | -261.784 | ~0 |
| Line:L4 | 54.115 | 54.115 | ~0 |

Prediction error is at machine precision (< 2e-12 MW) across all 46 branches.

### PTDF Bus Ordering

The PTDF matrix columns follow `sub.buses_o` ordering (slack bus first, then non-slack). The slack bus column is all zeros (flows are defined relative to the slack bus).

## API

```python
n.determine_network_topology()
sub = n.sub_networks.obj[n.sub_networks.index[0]]
sub.calculate_PTDF()
ptdf = sub.PTDF  # numpy array (branches x buses)
```

PTDF is computed via `B_inverse = B[1:,1:]^{-1}` (slack row/column removed), then `PTDF = H * B_inverse` where H is the branch-bus incidence matrix weighted by branch susceptance. The result is a dense numpy array.

### Usage Note

PTDF columns correspond to `sub.buses_o` bus ordering (not `n.buses.index` order). The injection vector must be constructed in this order for correct flow prediction:

```python
buses_o = list(sub.buses_o)
p_inj = np.array([bus_injection[b] for b in buses_o])
flows = ptdf @ p_inj
```

## Observations

- PTDF calculation is a native PyPSA API method, not a workaround.
- BODF (Branch Outage Distribution Factor) is also available via `sub.calculate_BODF()`.
- The bus ordering requirement (`buses_o` vs `buses_i`) is a minor API friction point that is not well-documented.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b9_ptdf_extraction_tiny.py`
