---
test_id: B-4
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 5.2382
peak_memory_mb: null
loc: 140
timestamp: "2026-03-06T00:00:00Z"
---

# B-4: Stochastic Scenario Wrapping on TINY

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Scenarios:** 20 (all converged)
- **Horizon:** 12 hours per scenario
- **Method:** For-loop over scenarios, each solved as 12-period deterministic MOST
- **Total wall clock:** 5.24 seconds
- **Mean per-scenario time:** 0.26 seconds
- **Solver:** MIPS (built-in)

## Generator Classification

Generators classified by marginal cost into three resource types:

| Class | Generators | MC Range ($/MWh) |
|-------|-----------|-----------------|
| Baseload | 5, 7, 8 | 10.46 -- 11.90 |
| Intermediate | 2, 4, 6 | 13.22 -- 14.04 |
| Peaker | 1, 3, 9, 10 | 14.80 -- 22.30 |

## Correlated Perturbations

Perturbations are correlated WITHIN resource type (AR(1) process) but independent
BETWEEN types, as required by the test:

| Resource Type | Sigma | Range Observed |
|--------------|-------|---------------|
| Load (all buses) | 0.03 | [0.899, 1.128] |
| Baseload PMAX | 0.02 | [0.945, 1.063] |
| Intermediate PMAX | 0.05 | [0.831, 1.100] |
| Peaker PMAX | 0.08 | [0.708, 1.100] |

## Wrapping Pattern

Each scenario is solved independently using MOST in deterministic mode (single
scenario, 12 periods). The wrapping loop:

1. Generates per-scenario load and generator perturbation timeseries
2. Builds MOST profile structs with scenario-specific values
3. Calls `loadmd()` + `most()` for each scenario
4. Extracts LMPs and dispatch from `mdo.flow(h, 1, 1).mpc`

No model reconstruction is needed between scenarios. Only the profile `values`
arrays change. The `mpc` struct, `xgd`, and solver options are reused.

## Results

### Price Distribution (Hour 6, Peak)

- Mean LMP across scenarios: 13.65 $/MWh
- Std LMP across scenarios: 3.85 $/MWh
- LMP range: [11.04, 38.74] $/MWh

### Dispatch Distribution (Hour 6, Peak)

| Gen | Bus | Mean (MW) | Std (MW) | Min (MW) | Max (MW) |
|-----|-----|-----------|----------|----------|----------|
| 1 | 30 | 620.2 | 43.7 | 536.9 | 717.0 |
| 2 | 31 | 618.8 | 29.6 | 558.0 | 646.0 |
| 3 | 32 | 630.0 | 45.9 | 558.0 | 725.0 |
| 5 | 34 | 508.0 | 0.0 | 508.0 | 508.0 |
| 9 | 38 | 637.7 | 68.1 | 558.0 | 865.0 |
| 10 | 39 | 648.4 | 109.9 | 558.0 | 1080.3 |

Gen 5 (cheapest baseload) runs at PMIN across all scenarios. Gen 10 (most expensive)
shows the widest dispatch variation (110 MW std), absorbing load uncertainty as
the marginal unit.

### Cost Distribution

- Mean: 398,183
- Std: 22,083
- Range: [360,415 -- 442,412]

## Timing

| Metric | Value |
|--------|-------|
| Total wall clock | 5.24 s |
| Mean per-scenario | 0.26 s |
| Min scenario | 0.24 s |
| Max scenario | 0.30 s |
| Overhead ratio | ~0.3% (setup vs solve) |

Per-scenario overhead is minimal. The `loadmd` + `most` call dominates each
iteration. No model reconstruction or re-parsing between scenarios.

## Distinction from A-8

A-8 tested MOST's **native** stochastic support: all 3 scenarios embedded in a
single QP with transition probabilities. B-4 tests the **wrapping** pattern:
a standard for-loop calling the tool's DCOPF API once per scenario. MATPOWER
supports both patterns:

- **A-8 (native):** Single `most()` call, 3 scenarios x 12 periods = 3252 QP variables
- **B-4 (wrapping):** 20 x `most()` calls, each 1 scenario x 12 periods

The wrapping pattern uses MOST in deterministic mode for multi-period linking
(ramp constraints), which is more natural than looping `rundcopf` per hour.

## API Assessment

**Low friction.** The scenario loop requires only changing the profile `values`
arrays between iterations. MOST's profile system accepts timeseries programmatically
as numeric arrays -- no file I/O or serialization needed. The main setup cost is
the initial MOST configuration (xGenData, profiles, transition matrices), which
is identical to A-8 and reusable across scenarios.

## Test Script

`evaluations/matpower/tests/extensibility/test_b4_stochastic_wrapping_tiny.m`
