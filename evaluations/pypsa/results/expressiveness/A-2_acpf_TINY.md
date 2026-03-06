# A-2: AC Power Flow (TINY)

- **Test ID:** A-2
- **Slug:** acpf
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS

## Pass Condition

Converges. Bus voltage magnitudes and angles, line P/Q flows, and losses accessible as structured output.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.092 s |
| Convergence | Yes (flat start) |
| V magnitude range | 0.982 - 1.064 pu |
| Total line P losses | 31.06 MW |
| Total line Q losses | 923.32 Mvar |

### Output Format

All outputs are pandas DataFrames:

- `n.buses_t.v_mag_pu` — voltage magnitudes (1x39)
- `n.buses_t.v_ang` — voltage angles (1x39)
- `n.lines_t.p0`, `n.lines_t.q0` — sending-end P/Q flows
- `n.lines_t.p1`, `n.lines_t.q1` — receiving-end P/Q flows
- `n.transformers_t.p0`, `n.transformers_t.q0` — transformer flows (1x11)

### Sample Voltages

| Bus | V (pu) | Angle (rad) |
|-----|--------|-------------|
| 1 | 1.0394 | -0.236 |
| 2 | 1.0485 | -0.171 |
| 3 | 1.0307 | -0.214 |
| 4 | 1.0045 | -0.220 |
| 5 | 1.0060 | -0.195 |

### Losses

Line losses computed as `p0 + p1` (sending + receiving end flows). Non-zero losses confirm full AC power flow with resistive losses.

## API

```python
result = n.pf()  # Newton-Raphson AC power flow
# result is a Dict with keys: n_iter, error, converged
```

## LOC

~5 lines beyond network loading.

## Workarounds

None required. Flat start converged on first attempt.

## Errors

None.
