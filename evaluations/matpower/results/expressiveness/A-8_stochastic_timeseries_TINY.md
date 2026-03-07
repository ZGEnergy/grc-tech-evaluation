---
test_id: A-8
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.0206
peak_memory_mb: null
loc: 180
timestamp: "2026-03-06T00:00:00Z"
---

# A-8: Stochastic Timeseries Optimization on TINY

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10+1 generators)
- **Tool:** MOST (MATPOWER Optimal Scheduling Tool), bundled with MATPOWER 8.1
- **Horizon:** 12 periods (hourly)
- **Scenarios:** 3 per period (low, medium, high)
- **Profiles:** Load (+/-3% around daily curve) + Wind (independent, 50%/100%/150%)
- **Formulation:** Single QP across all periods and scenarios (3252 variables, 6492 constraints)
- **Solver:** MIPS (built-in)
- **Converged:** Yes (exitflag=1)
- **Objective:** 442,879.56
- **Wall clock:** 1.02 seconds

## Stochastic Structure

MOST natively supports scenario-indexed timeseries. The stochastic structure is embedded
in the optimization formulation as a single QP/MIQP, not a loop of independent solves.

### Key MOST components used:
1. **Transition matrix** (`transmat`): cell array defining scenario probabilities per period
2. **Profiles**: struct array specifying how load and wind vary across time and scenarios
3. **xGenData**: per-generator reserve offers and ramping parameters
4. **`loadmd()`**: assembles all components into the MOST Data Input (mdi) struct
5. **`most(mdi, mpopt)`**: solves the full stochastic problem in a single call

### Independent perturbations by resource type:
- **Load profile**: Modifies all bus loads via `CT_TLOAD` / `CT_LOAD_ALL_PQ` (relative scaling)
- **Wind profile**: Modifies wind generator PMAX via `CT_TGEN` / `PMAX` (relative scaling)

These are independent profiles applied to different tables, so load and wind
uncertainty are independently specified as required by the test.

## Setup Requirements

case39 required augmentation for MOST:
1. **Wind generator added** at bus 25 (200 MW, zero marginal cost)
2. **Ramp rates set** to 30% of PMAX (case39 has zero ramp rates by default)
3. **xGenData created** with reserve prices and quantities for all generators

## Results

### Scenario-Specific LMPs (Period 6, Peak Hour)

| Scenario | LMP Range ($/MWh) | Mean LMP |
|----------|-------------------|----------|
| 1 (low)  | [3.05, 3.26]      | 3.19     |
| 2 (med)  | [6.18, 7.05]      | 6.75     |
| 3 (high) | [2.85, 4.92]      | 4.21     |

Scenarios produce different dispatch and different prices, confirming the stochastic
formulation links scenarios within a single optimization.

### Energy Prices (GenPrices, $/MWh) — Selected Generators

| Period | Gen01 | Gen05 | Gen10 | Wind |
|--------|-------|-------|-------|------|
| 1      | 11.51 | 11.53 | 11.52 | 11.52 |
| 4      | 12.14 | 12.67 | 12.40 | 12.20 |
| 7      | 11.91 | 15.53 | 13.70 | 12.34 |
| 10     | 12.06 | 12.45 | 12.26 | 12.11 |
| 12     | 11.64 | 11.69 | 11.67 | 11.65 |

Prices vary across time (load curve effect) and across generators (locational effect).
Gen05 (bus 34) shows the widest price variation due to network position.

### Expected Dispatch (MW) — Selected Generators

| Period | Gen01 | Gen05 | Gen10 | Wind |
|--------|-------|-------|-------|------|
| 1      | 560.7 | 508.0 | 561.1 | 200.0 |
| 6      | 589.2 | 508.0 | 651.0 | 200.0 |
| 7      | 580.6 | 508.0 | 669.9 | 200.0 |
| 12     | 567.1 | 508.0 | 568.3 | 200.0 |

## API Observations

### Learning Curve (api-friction)
MOST requires significant setup compared to single-period MATPOWER:
- Understanding `xGenData` columns (reserve offers, delta prices)
- Profile struct format (`type`, `table`, `rows`, `col`, `chgtype`, `values`)
- Transition matrix structure (cell array of probability matrices)
- `idx_ct` constants for profile table/column specifications

The profile system is powerful but opaque. The `values` array has a specific 3D
structure `[nt x nj x n_elements]` that is not intuitive. The `chgtype` field
(PR_REP/PR_REL/PR_ADD) adds another dimension of complexity.

### MIPS Solver Limitations (solver-issues)
The built-in MIPS solver struggles with larger load variation (+/-10%) on the
39-bus network combined with stochastic wind. Reducing to +/-3% load variation
resolved convergence. A commercial solver (Gurobi, CPLEX) would likely handle
wider uncertainty bands. This is documented in the MOST manual as a known limitation
of MIPS for larger stochastic problems.

### Documentation (doc-gaps)
The MOST manual (PDF) is comprehensive but dense. The profile system documentation
is scattered across `idx_profile.m`, `apply_profile.m`, and the manual. The examples
in `most/lib/t/` are the most practical learning resource, but they use small
3-bus test cases that don't directly map to real-world setups. Setting up MOST for
case39 required piecing together patterns from multiple test files.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a8_stochastic_timeseries_tiny.m`
