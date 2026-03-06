# A-10: Lossy DC OPF with LMP Decomposition (TINY)

- **Test ID:** A-10
- **Slug:** lossy_dcopf_lmp
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS

## Pass Condition

Loss-inclusive LMPs with non-zero loss components. LMP decomposition extractable.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.720 s |
| Solver status | optimal |
| Lossless cost (A-3) | 41261.94 |
| Lossy cost | 41859.54 |
| Cost increase | 597.60 (+1.4%) |
| Loss segments | 3 (piecewise-linear) |
| Total lossless gen | 6254.23 MW |
| Total lossy gen | 6297.34 MW |
| Generation increase (losses) | 43.11 MW |

### LMP Decomposition

| Component | Method | Range |
|-----------|--------|-------|
| Energy | Slack bus LMP | 13.86 |
| Congestion | Lossless LMP - energy | -0.0001 to +0.0002 |
| Loss | Lossy LMP - lossless LMP | -0.241 to +0.663 |

All 39 buses have non-zero loss components in their LMPs.

### Sample LMPs (first 5 buses)

| Bus | Lossless | Lossy | Loss Component |
|-----|----------|-------|----------------|
| 1 | 13.517 | 14.091 | +0.573 |
| 2 | 13.517 | 13.709 | +0.191 |
| 3 | 13.517 | 13.861 | +0.344 |
| 4 | 13.517 | 13.925 | +0.408 |
| 5 | 13.517 | 13.889 | +0.372 |

Loss components vary by bus location, with buses electrically distant from generation having higher loss marginals.

## API

```python
n.optimize(
    solver_name="highs",
    transmission_losses=3,  # 3-segment piecewise-linear approximation
)
```

Single parameter addition to standard DC OPF call. PyPSA 1.1.2 also supports `transmission_losses=True` for secant-based losses (newer method).

### LMP Decomposition Method

PyPSA does not provide built-in LMP decomposition. The decomposition is computed by comparing lossy and lossless OPF results:
- **Energy component:** LMP at the slack/reference bus
- **Congestion component:** Lossless LMP minus energy component
- **Loss component:** Lossy LMP minus lossless LMP

## LOC

~5 lines beyond A-3 (add `transmission_losses=3` parameter, compare with lossless run for decomposition).

## Workarounds

None required. Native `transmission_losses` parameter works out of the box.

## Errors

None.
