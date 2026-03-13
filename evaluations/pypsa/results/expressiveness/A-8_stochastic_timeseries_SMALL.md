---
test_id: A-8
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 14062ed9
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 535.4
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 335
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-8: Stochastic Multi-period DCOPF (stochastic_timeseries) — SMALL

## Result: QUALIFIED PASS

## Approach

Same blocking limitation as TINY: PyPSA 1.1.2 has no native two-stage stochastic programming formulation. The scenario loop (3 independent LP solves) is the best available approach. Implemented 3 scenarios × 12 periods, each on the full case_ACTIVSg2000.m network (2000 buses, 544 generators + 2 added renewables).

**Setup:**
- Base network: case_ACTIVSg2000.m (2000 buses, 544 thermal generators)
- Added: 200 MW wind generator at bus 1006, 150 MW solar generator at bus 1019 (marginal_cost=0)
- Thermal generators: uniform $30/MWh marginal cost
- 12-hour horizon (12 snapshots per scenario)
- Load scale factors: S1=1.00, S2=0.95, S3=1.05
- Scenario-specific renewable CFs: sinusoidal profile × scenario multiplier

Per-scenario LP has 128,532 rows, 45,024 cols (10 constraints per bus × 12 periods plus branch limits).

## Output

**Native stochastic check (same as TINY):**
- `n.set_snapshots(MultiIndex)`: accepted (but NOT a stochastic formulation)
- `pypsa.optimization` stochastic methods: 0 found
- Non-anticipativity constraints: not supported
- Scenario-weighted objective: not supported

**Scenario loop results (3 scenarios × 12 periods on SMALL):**

| Scenario | Load scale | Objective ($) | Wind avg (MW) | Solve time (s) |
|---------|-----------|---------------|---------------|----------------|
| S1 | 1.00 | 19,761,531 | 42.0 | 116.0 |
| S2 | 0.95 | 18,771,290 | 42.0 | 180.7 |
| S3 | 1.05 | 20,751,772 | 42.0 | 229.9 |

- Successful scenarios: 3/3 (all optimal)
- Objective std across scenarios: $991,241 (reflects 5% load variation)
- Total scenario loop: ~527 s (dominant cost: LP construction + HiGHS per scenario)

**Scale comparison vs TINY:**

| Metric | TINY (39 buses) | SMALL (2k buses) |
|--------|-----------------|-----------------|
| Network size | 39 buses | 2,000 buses |
| Per-scenario solve | ~0.4 s | 175 s (avg) |
| Scenario LP rows | ~480 | 128,532 |
| All 3 scenarios | 1.2 s | 527 s |

The ~440× per-scenario slowdown (TINY → SMALL) is roughly proportional to the LP size increase (~270× more rows). Scenario 3 took 30% longer than S1 — likely due to the higher load causing tighter constraints requiring more dual simplex iterations.

**Stochastic formulation gap (unchanged from TINY):**

| Capability | PyPSA 1.1.2 |
|-----------|------------|
| Independent scenario LPs | Yes |
| Scenario-weighted objective (Σ_s w_s × f_s) | No |
| Non-anticipativity constraints | No |
| Two-stage stochastic programming | No |
| Architecture path | Custom linopy multi-model (complex) |

## Workarounds

- **What:** Scenario loop — 3 separate LP solves per scenario; scenarios are not coupled.
- **Why:** PyPSA 1.1.2 has no native two-stage stochastic programming formulation at any network size. `n.optimize()` has no `scenario_weights` or `non_anticipativity` parameters. `n.set_snapshots(MultiIndex)` accepts scenario indices but treats them as independent time periods.
- **Durability:** blocking — cannot achieve a true stochastic OPF (first-stage shared decisions, non-anticipativity constraints) without modifying PyPSA's source code or building a custom linopy multi-model outside PyPSA's API. This is consistent with the TINY finding; SMALL scale does not change the architectural limitation.
- **Grade impact:** Blocking expressiveness gap for stochastic OPF. The scenario loop is a valid Monte Carlo analysis tool but not stochastic optimization.

## Timing

- **Wall-clock:** 535.4 s total (all 3 scenarios + overhead)
- **Per-scenario times:** S1=116.0 s, S2=180.7 s, S3=229.9 s
- **Timing source:** measured
- **Peak memory:** not measured (each scenario: ~2 GB estimated from base DCPF)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a8_stochastic_timeseries.py`

Key finding (same as TINY — no native stochastic):
```python
import pypsa.optimization as opt_mod
stochastic_attrs = [a for a in dir(opt_mod) if "stochast" in a.lower() or "scenario" in a.lower()]
# → [] (empty list — no stochastic methods in PyPSA optimization module)
```
