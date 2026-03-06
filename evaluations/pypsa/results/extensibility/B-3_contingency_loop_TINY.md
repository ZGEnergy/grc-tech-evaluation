# B-3: N-1 DCPF Contingency Loop (TINY)

- **Test ID:** B-3
- **Slug:** contingency_loop
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS
- **Workaround durability:** Stable

## Pass Condition

Runs without re-parsing model from file. TINY: all 46 branches.

## Results

| Metric | Value |
|--------|-------|
| Wall clock (all 46 contingencies) | 3.17 s |
| Per-contingency average | 0.069 s |
| Contingencies completed | 46 / 46 |
| Contingencies failed | 0 |
| Base case max line loading | 0.767 |
| LOC | ~25 lines |

### Top 5 Worst Contingencies

| Rank | Contingency | Type | Max Loading | Most Loaded Branch |
|------|-------------|------|-------------|-------------------|
| 1 | L26 | line | 1.604 | L28 |
| 2 | L17 | line | 1.336 | L11 |
| 3 | L22 | line | 1.148 | L28 |
| 4 | L28 | line | 1.148 | L22 |
| 5 | L34 | line | 0.911 | L33 |

## API

PyPSA does not have a dedicated contingency analysis API. The loop is constructed manually by modifying network parameters in-place:

```python
for branch_name in branches:
    orig_x = n.lines.loc[branch_name, "x"]
    n.lines.loc[branch_name, "x"] = 1e10    # effectively disconnect
    n.lpf()                                    # re-solve DCPF
    # collect results...
    n.lines.loc[branch_name, "x"] = orig_x   # restore
```

The network object is modified in-place and re-solved without re-parsing from file. The approach sets reactance to a very large value to effectively remove the branch from the network. This is a stable workaround -- PyPSA's lpf() recomputes the B matrix each call, so parameter changes take effect immediately.

## Observations

- No dedicated `n.lines.active` flag or `remove_branch()` method. Setting `x = 1e10` is the practical approach.
- Each `n.lpf()` call recomputes topology and the B matrix, which adds overhead but ensures correctness after parameter changes.
- All 46 contingencies complete without errors, including cases that create electrical islands.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b3_contingency_loop_tiny.py`
