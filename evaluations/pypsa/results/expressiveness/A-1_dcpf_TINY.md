# A-1: DC Power Flow (TINY)

- **Test ID:** A-1
- **Slug:** dcpf
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS

## Pass Condition

Converges. Nodal injections, line flows, and voltage angles accessible as structured output.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.061 s |
| Buses | 39 |
| Lines / Transformers | 35 / 11 |
| Generators | 10 |
| Total generation | 6254.23 MW |
| Total load | 6254.23 MW |
| Power balance | 0.0 MW |

### Output Format

All outputs are pandas DataFrames with time-indexed rows and component-indexed columns:

- `n.buses_t.v_ang` — voltage angles (1x39 DataFrame)
- `n.lines_t.p0` — line active power flows (1x35 DataFrame)
- `n.buses_t.p` — nodal power injections (1x39 DataFrame)
- `n.generators_t.p` — generator dispatch (1x10 DataFrame)

### Sample Voltage Angles (rad)

| Bus 1 | Bus 2 | Bus 3 | Bus 4 | Bus 5 |
|-------|-------|-------|-------|-------|
| -0.215 | -0.141 | -0.192 | -0.203 | -0.181 |

### Sample Line Flows (MW)

| L0 | L1 | L2 | L3 | L4 |
|----|----|----|----|----|
| -178.4 | 80.8 | 333.4 | -261.8 | 54.1 |

## API

```python
n.lpf()  # single call, always converges (linear solve)
```

## LOC

~5 lines beyond network loading (call `n.lpf()`, access results via DataFrame attributes).

## Workarounds

None required.

## Errors

None.
