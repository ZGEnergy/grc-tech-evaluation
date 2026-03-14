---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 8531c61c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.445
timing_source: measured
peak_memory_mb: null
convergence_residual: 3.104e-09
convergence_iterations: 4
loc: 400
solver: Ipopt
timestamp: 2026-03-14T00:30:00Z
---

# A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

## Result: PASS

## Approach

Reproduced the A-3 DC OPF within the same model context (shared loader with
DC transformer susceptance patch, Modified Tiny differentiated costs, 70%
branch derating), then transferred the generator dispatch to a fresh Network
object for AC power flow.

Key implementation detail: PyPSA's shared MATPOWER loader applies a
transformer susceptance correction (`b = 1/x`) that is correct for DC power
flow but causes AC power flow divergence. The A-2 result documents this same
finding. For the AC PF step, the network was loaded via the raw
`import_from_pypower_ppc()` path (without the DC patch) to preserve the
native AC transformer model.

The DC OPF dispatch was set on generators via `n.generators_t.p_set`, and
`n.pf()` was called with Newton-Raphson (PyPSA's internal NR solver). The
entire workflow -- DC OPF, dispatch extraction, AC PF, violation analysis --
happens within Python objects without any file export/reimport, satisfying
the "same model context" requirement.

### Unit consistency at transfer point

| Quantity | Unit | Value |
|----------|------|-------|
| base_power | MVA | 100.0 |
| DC OPF dispatch | MW | 6,254.23 total |
| AC PF p_set | MW | same values |
| Line limits | MVA (s_nom) | 70% derated |

## Output

### Convergence

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| NR iterations | 4 |
| Convergence residual | 3.104e-09 |
| Non-trivial voltage buses | 39/39 (100%) |
| DC warm start needed | No |

### Voltage Violations (outside [0.95, 1.05] pu)

| Bus | V (pu) | Type | Margin (pu) |
|-----|--------|------|-------------|
| 19 | 1.05039 | high | +0.00039 |
| 22 | 1.05023 | high | +0.00023 |
| 25 | 1.05795 | high | +0.00795 |
| 26 | 1.05239 | high | +0.00239 |
| 28 | 1.05006 | high | +0.00006 |
| 36 | 1.06360 | high | +0.01360 |

6 buses exceed the 1.05 pu upper limit, all on the high side. The largest
violation is bus 36 at 1.064 pu. No buses are below 0.95 pu; the minimum
voltage is 0.982 pu. All violations are associated with generator buses
(the DC OPF does not model voltage control).

### Thermal Violations (vs 70% derated limits)

| Branch | Type | Flow (MVA) | Limit (MVA) | Loading |
|--------|------|-----------|-------------|---------|
| T2 | transformer | 639.93 | 630.0 | 101.6% |
| T8 | transformer | 647.88 | 630.0 | 102.8% |

2 transformers exceed their derated thermal limits. These violations arise
because the AC power flow includes reactive power (apparent power > active
power), while the DC OPF only constrains active power flow. No line
violations were observed.

### DC OPF Dispatch (from A-3)

| Generator | Dispatch (MW) |
|-----------|--------------|
| G0 (hydro) | 235.5 |
| G1 (nuclear) | 646.0 |
| G2 (nuclear) | 630.0 |
| G3 (coal) | 630.0 |
| G4 (coal) | 470.0 |
| G5 (nuclear) | 630.0 |
| G6 (gas CC) | 580.0 |
| G7 (nuclear) | 564.0 |
| G8 (nuclear) | 840.0 |
| G9 (gas CC) | 1,028.7 |

## Workarounds

None required. The entire DC OPF -> AC PF -> violation analysis workflow
uses documented PyPSA public API (`n.optimize()`, `n.pf()`,
`n.buses_t.v_mag_pu`, `n.lines_t.p0`, `n.lines_t.q0`).

Note: the need to load the network without the DC transformer patch for AC
PF is a consequence of the shared loader's design, not a PyPSA limitation.
PyPSA's native `import_from_pypower_ppc()` works correctly for both DC and
AC analysis when used without the patch.

## Timing

- **Wall-clock:** 1.445s (total: DC OPF + AC PF + violation analysis)
- **AC PF only:** 0.089s
- **Timing source:** measured
- **Peak memory:** not measured (not a scalability test)
- **NR iterations:** 4
- **Convergence residual:** 3.104e-09
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility.py`
