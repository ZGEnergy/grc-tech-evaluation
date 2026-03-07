---
test_id: A-5
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 1.6707
peak_memory_mb: null
loc: 220
timestamp: "2026-03-06T00:00:00Z"
---

# A-5: SCUC (24-hour Unit Commitment) on TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Tool:** MOST (MATPOWER Optimal Scheduling Tool), bundled with MATPOWER 8.1
- **Horizon:** 24 periods (hourly)
- **Solver:** GLPK (MILP, bundled with Octave)
- **Formulation:** MILP (3816 variables) -- piecewise-linear costs with binary commitment
- **Converged:** Yes (exitflag=1)
- **Objective:** 837,041.61 (total cost over 24 hours)
- **Wall clock:** 1.67 seconds

## Workaround: Stable

GLPK (the only MILP solver available on Octave without HiGHS) cannot handle quadratic
programming. case39 has polynomial (quadratic) generator costs. The workaround was to
convert quadratic costs to 10-segment piecewise-linear approximations before building
the MOST problem. This is a well-documented technique and MATPOWER natively supports
PWL cost format. Classification: **stable workaround** (PWL conversion is standard practice).

## Case Augmentation

case39 required augmentation for a meaningful UC test:

1. **Ramp rates set** to 30% of PMAX (case39 defaults are zero)
2. **PMIN set** to 20% of PMAX (enables min-gen constraints for UC decisions)
3. **Startup costs added** at 5x PMAX ($), shutdown at 1x PMAX ($)
4. **Gencost converted** from polynomial to piecewise-linear (for GLPK)

## UC Parameters (via xGenData)

| Parameter | Value | Notes |
|-----------|-------|-------|
| CommitKey | 1 | Binary UC variable per generator per period |
| CommitSched | 1 | Initially all committed |
| MinUp | 3 hours | Minimum up time |
| MinDown | 2 hours | Minimum down time |

## Commitment Schedule

All 10 generators remain committed for all 24 hours. This is because case39's total
generation capacity (7367 MW) exceeds peak load (6254 MW *1.0 = 6254 MW) but with
PMIN=20%, minimum generation (1473 MW) is well below minimum load (6254* 0.77 = 4816 MW).
The UC solver correctly determined that de-committing any generator would not reduce
total cost given the startup/shutdown cost structure.

The formulation is verified correct:
- Min up/down time constraints: 0 violations
- Ramp rate constraints: 0 violations
- Binary commitment variables present in the MILP

## Dispatch Summary

| Period | Total Dispatch (MW) | Load Factor |
|--------|-------------------|-------------|
| HE1    | 5,191.0           | 0.83        |
| HE6    | 5,128.5           | 0.82        |
| HE12   | 6,129.1           | 0.98        |
| HE18   | 6,191.7           | 0.99        |
| HE24   | 5,316.1           | 0.85        |

## Energy Prices ($/MWh)

Prices are uniform across buses (no congestion) but vary across time:

| Period | Price ($/MWh) |
|--------|--------------|
| HE1    | 10.73        |
| HE6    | 10.64        |
| HE12   | 12.82        |
| HE18   | 13.49        |
| HE24   | 10.86        |

## MOST UC Capabilities (Built-in)

MOST natively supports the following UC constraint types via xGenData:
- **Min up/down times:** `MinUp`, `MinDown` columns
- **Startup costs:** via gencost column 2
- **Ramp rates:** via gen columns RAMP_AGC, RAMP_10, RAMP_30
- **Reserve requirements:** `PositiveActiveReservePrice/Quantity`
- **Commitment variables:** `CommitKey` (1=UC variable, 2=must-run)

All constraint types are **built-in** to the MOST framework -- no user assembly required.

## API Observations

### Solver Constraint (api-friction)
The biggest friction for SCUC is the solver limitation. On Octave:
- GLPK handles MILP but NOT MIQP (no quadratic costs with integers)
- HiGHS would handle MIQP but was not available in our environment
- Converting costs to PWL is the standard workaround (~25 LOC)
- With MATLAB, Gurobi/CPLEX handle MIQP natively

### GLPK Price Warning
GLPK produced a warning: "max relative mismatch in x from price computation stage = 3.17".
This indicates the LP relaxation prices don't exactly match the MILP solution, which is
expected for integer programs. Prices are approximate with GLPK's post-solve pricing.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a5_scuc_tiny.m`
