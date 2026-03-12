---
test_id: A-10
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: be7f7108
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 295.82
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 278
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-10: Lossy DC OPF with LMP decomposition (lossy_dcopf_lmp) — SMALL

## Result: PASS

## Approach

Same as TINY: loaded two copies of case_ACTIVSg2000.m via CaseFrames → pypower ppc. Assigned linearly-spaced marginal costs ($10–$100/MWh) to all 544 generators. Used full s_nom (no derating) — 70% derating makes the SMALL network infeasible (same finding as A-9).

Solved lossless baseline DC OPF via `n_lossless.optimize(solver_name="highs")`, then solved lossy DC OPF via `n_lossy.optimize(transmission_losses=3, solver_name="highs")` (3-segment piecewise linearization of I²R losses). Decomposed LMPs into energy and loss components; computed congestion rents from LMP gradient × flow product.

## Output

**Lossless baseline:**
- Objective: $2,980,851/h
- Solve time: ~1.7 s (1,733 simplex iterations)

**Lossy OPF (3-segment piecewise losses):**
- Objective: $3,085,620/h (+3.51% vs lossless — confirms loss effect)
- Implied losses: 1,507.6 MW (2.246% of total load — within 0.5–3% range)
- Total generation: 68,616.8 MW vs total load: 67,109.2 MW
- Solve time: 151.8 s (6,254 simplex iterations — larger model with loss variables)
- Termination: optimal

**LMP decomposition:**
- Slack bus: 7098 (energy component reference: $64.75/MWh)
- Loss component range: [-$49.00, +$605.15]/MWh across buses
- Non-zero loss components: 1,999 of 2,000 buses (99.95%)
- Total congestion rent: $228,540/h

**Consistency checks:**

| Check | Result | Status |
|-------|--------|--------|
| (a) Non-zero loss components | 1,999/2,000 buses | PASS |
| (b) Losses = 2.246% of load | Within 0.5–3% range | PASS |
| (c) Lossy objective ≥ lossless | $3,085,620 ≥ $2,980,851 | PASS |

**Scale comparison vs TINY:**

| Metric | TINY (39 buses) | SMALL (2k buses) |
|--------|-----------------|-----------------|
| Lossless solve | ~0.34 s | ~1.7 s |
| Lossy solve | 0.67 s | 151.8 s |
| Non-zero loss components | 39/39 (100%) | 1,999/2,000 (99.95%) |
| Loss % of load | 0.761% | 2.246% |

The higher loss percentage on SMALL (2.246% vs 0.761% on TINY) reflects ACTIVSg2000's larger geographic extent and higher line impedances relative to load.

## Workarounds

1. **What:** Manually assigned marginal costs.
   - **Why:** `import_from_pypower_ppc` does not import gencost data.
   - **Durability:** stable.
   - **Grade impact:** Low.

2. **What:** Full s_nom used (no branch derating).
   - **Why:** 70% derating makes SMALL network infeasible. ACTIVSg2000 has tight thermal utilization; derating eliminates the feasible dispatch region. Same finding as A-9 SMALL.
   - **Durability:** stable — network configuration choice.
   - **Grade impact:** Low.

3. **What:** Used deprecated integer form `transmission_losses=3` instead of new dict syntax.
   - **Why:** Both forms functional in PyPSA 1.1.2; integer form is consistent with TINY documentation.
   - **Durability:** stable for current version.
   - **Grade impact:** None.

## Timing

- **Wall-clock:** 295.8 s total
- **Load time (both networks):** ~2.5 s
- **Lossless solve:** ~1.7 s
- **Lossy solve:** 151.8 s (dominant — loss piecewise linearization adds 22,442 rows to model)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

**Note on lossy model size:** Lossless LP has 10,707 rows, 3,750 cols. Lossy LP has 33,149 rows, 6,956 cols (+210% rows, +85% cols). The piecewise linearization adds loss tangent constraints per line/transformer per segment, driving the majority of the 151.8s solve time.

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`

Key API:
```python
status_l, cond_l = n_lossy.optimize(
    transmission_losses=3,       # 3-segment piecewise linearization
    solver_name="highs",
    solver_options=SOLVER_OPTIONS,
)
lmps_lossy = n_lossy.buses_t.marginal_price.iloc[0]
implied_losses_mw = total_gen_mw - total_load_mw  # generation surplus = losses
energy_component = lmps_lossy[slack_bus]
loss_components = lmps_lossy - energy_component  # simplified LMP decomposition
```
