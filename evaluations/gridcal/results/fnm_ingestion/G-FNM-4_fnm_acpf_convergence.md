---
test_id: G-FNM-4
tool: gridcal
dimension: fnm_ingestion
network: LARGE
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 214.76
timing_source: measured
peak_memory_mb: 2042.5
convergence_residual: 15.826
convergence_iterations: 200
loc: 346
solver: NR/LM/HELM
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: v1
test_hash: "4aa892c7"
input_path: matpower
relaxation_level_achieved: "infeasible"
dcpf_init_mean_deg: 110.2609
dcpf_init_max_abs_deg: 179.9973
---

# G-FNM-4: ACPF convergence test -- DCPF warm-start + progressive relaxation on FNM

## Result: INFORMATIONAL

ACPF does not converge on the 27,862-bus FNM main island under any solver or
relaxation configuration tested. Four solver algorithms were exercised at three
branch rate relaxation levels (0%, 10%, 20%) -- all 12 combinations failed to
achieve genuine convergence. The best residual was 15.83 (Levenberg-Marquardt,
200 iterations), far above the 1e-6 tolerance. This is an informational finding
with no gate consequence.

## Approach

### Input path

G-FNM-1 established that GridCal cannot ingest the intermediate CSV tables. The
MATPOWER fallback path was used: `data/fnm/reference/cleaned/fnm_main_island.m`
(27,862-bus main island, type-4 isolated buses removed).

### DCPF warm-start

DC power flow solved successfully in 2.39 seconds. The DCPF solution provided
initial voltage angles for the ACPF warm start. Initial conditions: VM=1.0 pu
for all buses, VA from DCPF angles.

```python
import VeraGridEngine as vge
from VeraGridEngine.enumerations import SolverType

grid = vge.open_file(matpower_file)
dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
dc_results = vge.power_flow(grid, dc_opts)

# Set initial guess from DCPF
for i, bus in enumerate(grid.buses):
    bus.Vm0 = 1.0
    bus.Va0 = np.angle(dc_results.voltage[i], deg=False)
```

### ACPF solver configurations

Four solver algorithms were tested at each relaxation level:

| Solver | Description | Max Iter | Controls |
|--------|-------------|----------|----------|
| NR (no controls) | Newton-Raphson, Q-limits/taps disabled | 200 | None |
| NR (with controls) | Newton-Raphson, full control loop | 200 | Q, taps, remote voltage |
| LM | Levenberg-Marquardt | 200 | None |
| HELM | Holomorphic Embedding Load Flow | 100 | None |

GridCal ACPF is configured via `PowerFlowOptions`:

```python
ac_opts = vge.PowerFlowOptions(
    solver_type=SolverType.NR,
    initialize_with_existing_solution=True,
    retry_with_other_methods=False,
    max_iter=200,
    tolerance=1e-6,
    control_q=False,
)
ac_results = vge.power_flow(grid, ac_opts)
```

### Branch rate relaxation

Branch thermal ratings were scaled by 1.0x (0%), 1.1x (10%), and 1.2x (20%).
As expected, this had zero effect on ACPF convergence -- thermal ratings are OPF
constraints, not power flow equation parameters. The ACPF Jacobian and bus power
mismatches are identical across all relaxation levels.

## Output

### DCPF warm-start metrics

| Metric | Value |
|--------|-------|
| DCPF solve time | 2.39 seconds |
| Nonzero-angle buses | 27,858 / 27,862 |
| Mean |VA| | 110.26 deg |
| Max |VA| | 179.997 deg |

### ACPF convergence summary (0% relaxation)

| Solver | Converged | Iterations | Final Residual | VM Range | Wall-clock |
|--------|-----------|------------|----------------|----------|------------|
| NR (no controls) | No | 200 | 614.95 | [0.001, 12.77] | 14.4s |
| NR (with controls) | No | 200 | 614.95 | [0.001, 12.77] | 12.5s |
| LM | No | 200 | 15.83 | [0.032, 1.57] | 28.3s |
| HELM | No | 1 | 94,856 | [0.313, 299.75] | 2.5s |

### ACPF convergence summary (10% relaxation -- identical results)

| Solver | Converged | Iterations | Final Residual |
|--------|-----------|------------|----------------|
| NR (no controls) | No | 200 | 614.95 |
| NR (with controls) | No | 200 | 614.95 |
| LM | No | 200 | 15.83 |
| HELM | No | 1 | 94,856 |

### ACPF convergence summary (20% relaxation -- identical results)

| Solver | Converged | Iterations | Final Residual |
|--------|-----------|------------|----------------|
| NR (no controls) | No | 200 | 614.95 |
| NR (with controls) | No | 200 | 614.95 |
| LM | No | 200 | 15.83 |
| HELM | No | 1 | 94,856 |

### Solver behavior notes

1. **Newton-Raphson** stalled at a residual of ~615 MVA after 200 iterations.
   Both with and without Q-limit and tap controls, the residual remained
   identical, suggesting the stall is in the basic power balance equations
   rather than control interactions. The voltage profile shows extreme values
   (VM from 0.001 to 12.77 pu) indicating oscillation without convergence.

2. **Levenberg-Marquardt** achieved the lowest residual (15.83 MVA) and the
   most plausible voltage profile (VM from 0.032 to 1.57 pu). However, it
   did not achieve the 1e-6 tolerance. LM's damping mechanism prevented the
   wild oscillations seen in NR but was insufficient for full convergence.

3. **HELM** diverged immediately (1 iteration, residual 94,856). The
   holomorphic embedding method produces voltages up to 300 pu, indicating
   the Pade approximant series failed to converge for this network.

4. **False convergence with retry:** When `retry_with_other_methods=True`, the
   solver reports `converged=True` after 1 iteration with a residual of 582.
   This was diagnosed as false convergence -- the retry mechanism falls back
   to a method that terminates early without achieving actual convergence.
   This finding was excluded from the results by using `retry_with_other_methods=False`
   for all solver configurations.

### Relaxation level achieved

`infeasible` -- ACPF did not converge at 0%, 10%, or 20% relaxation with any
solver configuration.

## Workarounds

None applicable. ACPF convergence failure on a 27,862-bus network loaded via
MATPOWER fallback is a diagnostic finding. Potential contributing factors:

1. **Network conditioning:** The FNM main island is a large, complex transmission
   network with diverse voltage levels and many transformers. ACPF convergence
   on such networks is challenging for any tool.

2. **Data path fidelity:** The MATPOWER format flattens transformer data, losing
   tap control modes, winding impedance detail, and switched shunt discrete
   steps. These fields are ACPF-critical (Tier 2 in the field criticality
   matrix) and their absence may degrade convergence.

3. **Q-limit interpretation:** The MATPOWER case may encode generator Q-limits
   in a way that GridCal interprets differently than MATPOWER, potentially
   constraining reactive support at buses that need it for voltage stability.

## Timing

- **Total wall-clock:** 214.76 seconds (all 12 attempts)
- **Timing source:** measured
- **Peak memory:** 2,042.5 MB
- **DCPF solve time:** 2.39 seconds
- **Best ACPF attempt:** LM, 28.3 seconds (200 iterations, residual 15.83)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/fnm_ingestion/test_g_fnm_4_fnm_acpf_convergence.py`

Key implementation details:
- Uses `initialize_with_existing_solution=True` (not `use_stored_guess`) per
  the actual VeraGridEngine API.
- Disables `retry_with_other_methods` to prevent false convergence reporting.
- Tests 4 solver algorithms (NR, NR+controls, LM, HELM) at 3 relaxation levels.
- Validates convergence quality by checking both `converged` flag and residual
  magnitude -- a residual > 1.0 with reported convergence is classified as
  false convergence.
