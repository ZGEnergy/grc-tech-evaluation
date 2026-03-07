---
test_id: A-9
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.2624
peak_memory_mb: null
loc: 180
timestamp: "2026-03-06T00:00:00Z"
---

# A-9: SCOPF (Security-Constrained OPF) on TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Tool:** MOST with `security_constraints = 1`
- **Contingencies:** 35 N-1 branch outages (11 bridge branches excluded)
- **Solver:** MIPS (built-in QP solver)
- **Formulation:** Single QP with 2,514 variables and 4,455 constraints
- **Converged:** Yes (exitflag=1)
- **Objective:** 41,277.63 $/hr (vs 41,263.94 base OPF)
- **Thermal relaxation:** None required (1.0x RATE_A)
- **Wall clock:** 1.26 seconds

## Method: MOST with Contingency Table

MATPOWER does **not** have a standalone `runscopf()` function. However, MOST (the companion
scheduling tool) natively supports security-constrained optimization via its contingency
table mechanism. The contingency constraints are embedded in the optimization formulation
(preventive SCOPF), not checked post-hoc.

### Contingency Table Format

```matlab
% label  prob    type       row  column     chgtype  newvalue
contab = [
    1    0.002   CT_TBRCH    1   BR_STATUS  CT_REP   0;   % trip branch 1
    2    0.002   CT_TBRCH    2   BR_STATUS  CT_REP   0;   % trip branch 2
    ...
];
mdi = loadmd(mpc, [], xgd, [], contab);
mpopt = mpoption(mpopt, 'most.security_constraints', 1);
mdo = most(mdi, mpopt);
```

This is a **native capability** of the MOST companion package. No custom constraint assembly
or callback functions are needed. The `contab` format supports branch outages, generator
outages, and load changes.

## Bridge Branch Filtering

IEEE 39-bus has 11 bridge branches (removing them disconnects generator buses from the
network, making SCOPF infeasible). These were identified programmatically via BFS connectivity
check and excluded:

| Branch | From | To  | Type |
|--------|------|-----|------|
| 5      | 2    | 30  | Radial gen bus 30 |
| 14     | 6    | 31  | Radial gen bus 31 |
| 20     | 10   | 32  | Radial gen bus 32 |
| 27     | 16   | 19  | Bridge |
| 32     | 19   | 20  | Bridge |
| 33     | 19   | 33  | Radial gen bus 33 |
| 34     | 20   | 34  | Radial gen bus 34 |
| 37     | 22   | 35  | Radial gen bus 35 |
| 39     | 23   | 36  | Radial gen bus 36 |
| 41     | 25   | 37  | Radial gen bus 37 |
| 46     | 29   | 38  | Radial gen bus 38 |

This filtering required ~40 lines of graph analysis code. MOST does not automatically
detect infeasible contingencies.

## Results Comparison

### Dispatch
Base-case dispatch is identical between SCOPF and unconstrained DC OPF. No N-1 contingency
caused binding post-contingency flow constraints that required preventive re-dispatch.
This is consistent with the case39 topology where RATE_A limits (480-1800 MVA) are generous
relative to the operating point.

### Cost

| Metric | Base OPF | SCOPF | Difference |
|--------|----------|-------|------------|
| Objective ($/hr) | 41,263.94 | 41,277.63 | +13.69 (0.03%) |

The small cost increase comes from the reserve/delta price terms in the xGenData structure,
not from dispatch re-optimization.

### LMPs

| Metric | Base OPF | SCOPF |
|--------|----------|-------|
| LMP (uniform) | 13.5169 $/MWh | 12.5707 $/MWh |

LMPs differ between base OPF and SCOPF due to the contingency constraint dual variables
affecting the marginal cost calculation, even though dispatch is unchanged.

### Post-Contingency Flows
- Max post-contingency flow/RATE_A ratio: 1.0000 (just at limit)
- Worst contingency: #28 (branch 3, bus 2->3)
- All 35 contingency flow limits respected simultaneously

## API Observations

### Ease of Use
SCOPF via MOST requires:
1. Building a contingency table (`contab`) -- straightforward tabular format
2. Creating xGenData with reserve offers -- same as stochastic MOST
3. Setting `most.security_constraints = 1` in options
4. Calling `loadmd` + `most` -- standard MOST workflow

The total additional code over a standard DC OPF is ~80 lines (including bridge detection).
Without bridge detection, ~40 lines.

### Not a Standalone SCOPF
MATPOWER's core library has no `runscopf()`. The SCOPF capability is accessed only through
MOST, which requires learning the MOST data structures (xGenData, loadmd, contingency table).
For users who only need single-period SCOPF without multi-period scheduling, this is
over-engineered but functional.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a9_scopf_tiny.m`
