---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 8531c61c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.107
timing_source: measured
peak_memory_mb: null
convergence_residual: 1.891e-09
convergence_iterations: 4
convergence_evidence_quality: residual_reported
loc: 346
solver: PyPSA-internal-NR
timestamp: 2026-03-24T12:00:00Z
---

# A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

## Result: PASS

## Approach

Loaded IEEE 39-bus network via `import_from_pypower_ppc()` (raw path, no DC
transformer susceptance patch), then fixed generator active power to the A-3
DC OPF dispatch values via `n.generators_t.p_set`. Ran `n.pf()` with
Newton-Raphson AC power flow (flat start: v_mag=1.0 pu, v_ang=0.0 rad).

The entire workflow -- network loading, dispatch assignment, AC PF,
violation analysis -- happens within Python objects without any file
export/reimport, satisfying the "same model context" requirement.

### Unit consistency at transfer point

| Quantity | Unit | Value |
|----------|------|-------|
| base_power | MVA | 100.0 |
| DC OPF dispatch | MW | 6,254.23 total |
| AC PF p_set | MW | same values |
| Line limits | MVA (s_nom) | full ratings (no derating for AC PF) |

## Output

### Convergence

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| NR iterations | 4 |
| Convergence residual | 1.891e-09 |
| Non-trivial voltage buses | 39/39 (100%) |
| DC warm start needed | No |
| Evidence quality | residual_reported |

### Voltage Violations (outside [0.95, 1.05] pu)

| Bus | V (pu) | Type | Margin (pu) |
|-----|--------|------|-------------|
| 2 | 1.0543 | high | +0.0043 |
| 19 | 1.0507 | high | +0.0007 |
| 22 | 1.0505 | high | +0.0005 |
| 25 | 1.0526 | high | +0.0026 |
| 26 | 1.0511 | high | +0.0011 |
| 36 | 1.0636 | high | +0.0136 |

6 buses exceed the 1.05 pu upper limit, all on the high side. The largest
violation is bus 36 at 1.064 pu. No buses are below 0.95 pu; the minimum
voltage is 0.982 pu (bus 31). All violations are associated with generator
buses (the DC OPF does not model voltage control).

### Thermal Violations

No thermal violations observed against full (underated) branch ratings.
All line and transformer flows remain within s_nom limits. The DC OPF
dispatch produces a physically feasible AC solution on this network.

### DC OPF Dispatch (from A-3)

| Generator | Dispatch (MW) |
|-----------|--------------|
| G0 (hydro) | 465.3 |
| G1 (nuclear) | 646.0 |
| G2 (nuclear) | 630.0 |
| G3 (coal) | 630.0 |
| G4 (coal) | 470.0 |
| G5 (nuclear) | 630.0 |
| G6 (gas CC) | 580.0 |
| G7 (nuclear) | 262.9 |
| G8 (nuclear) | 840.0 |
| G9 (gas CC) | 1,100.0 |

## Workarounds

None required. The entire DC OPF -> AC PF -> violation analysis workflow
uses documented PyPSA public API (`n.optimize()`, `n.pf()`,
`n.buses_t.v_mag_pu`, `n.lines_t.p0`).

## Timing

- **Wall-clock:** 2.107s (total: network load + dispatch assignment + AC PF + violation analysis)
- **AC PF only:** 0.128s
- **Timing source:** measured
- **Peak memory:** not measured (not a scalability test)
- **NR iterations:** 4
- **Convergence residual:** 1.891e-09
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility_tiny.py`
