---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 1734eea4
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.100
timing_source: measured
peak_memory_mb: null
convergence_residual: 1.891e-09
convergence_iterations: 4
loc: 333
solver: scipy (Newton-Raphson)
timestamp: 2026-03-11T00:00:00Z
---

# A-4: AC Feasibility Check (ac_feasibility)

## Result: PASS

## Approach

Loaded IEEE 39-bus network using the standard three-step MATPOWER ingestion (CaseFrames → ppc dict → `import_from_pypower_ppc`). Set generator active power dispatch to the A-3 DC OPF optimal solution via `n.generators_t.p_set` — all 10 generators dispatched within the same model context (no file export or reimport). Ran `n.pf(snapshots=[snapshot])` (Newton-Raphson AC power flow, flat start) to obtain the AC solution. Checked voltage magnitudes against [0.95, 1.05] pu bounds and line/transformer flows against `s_nom` limits.

The "same model context" requirement is fully met: the dispatch from A-3 was applied via in-memory DataFrame assignment and the AC PF run immediately. No serialization or file I/O was needed.

Convergence result extraction required understanding the `pf()` return structure: PyPSA v1.1.2 returns a `Dict` with top-level keys `n_iter`, `error`, `converged` (each a DataFrame), not a dict-of-sub-networks with `.converged` attributes.

## Output

**AC Power Flow:** Converged in 4 Newton-Raphson iterations, residual = 1.891e-09 (well below tolerance)

**Dispatch applied (from A-3):**

| Generator | Dispatch (MW) |
|-----------|--------------|
| G0 | 465.3 |
| G1 | 646.0 |
| G2 | 630.0 |
| G3 | 630.0 |
| G4 | 470.0 |
| G5 | 630.0 |
| G6 | 580.0 |
| G7 | 262.9 |
| G8 | 840.0 |
| G9 | 1100.0 |

**Voltage violations (outside [0.95, 1.05] pu):** 6 buses

| Bus | Voltage (pu) | Violation |
|-----|-------------|-----------|
| 2   | 1.0543 | high (+0.004) |
| 19  | 1.0507 | high (+0.001) |
| 22  | 1.0505 | high (+0.001) |
| 25  | 1.0526 | high (+0.003) |
| 26  | 1.0511 | high (+0.001) |
| 36  | 1.0636 | high (+0.014) |

- Voltage range: 0.982 – 1.0636 pu
- All violations are slight over-voltages (DC OPF dispatch does not enforce AC voltage limits)
- 100% of buses have non-flat-start voltages (convergence quality: excellent)

**Thermal limit violations:** 0 (no line or transformer thermal violations at DC OPF dispatch)

## Workarounds

None required. The same model context requirement is natively satisfied by PyPSA's in-memory architecture — `generators_t.p_set` can be set between solves without any export/reimport cycle.

The A-3 result file showed only the non-zero or notable dispatched generators; the actual complete dispatch (all 10 generators producing) was obtained by re-running the A-3 test script.

## Timing

- **Wall-clock:** 1.100 s (full test including network load + PF)
- **PF solve time:** ~0.087 s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 4 NR iterations
- **Convergence residual:** 1.891e-09 (flat start → 4 iterations to convergence)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility_tiny.py`

Key API pattern:
```python
# Same model context: set dispatch in-memory, then run PF
p_set_df = pd.DataFrame(a3_dispatch, index=[snapshot])
n.generators_t.p_set = p_set_df
pf_result = n.pf(snapshots=[snapshot])

# Read convergence from pf() return Dict
converged = bool(pf_result["converged"].values.flatten()[0])
n_iter = int(pf_result["n_iter"].values.flatten()[0])
residual = float(pf_result["error"].values.flatten()[0])
```
