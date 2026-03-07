---
test_id: A-4
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.433
peak_memory_mb: null
loc: 226
solver: Ipopt
timestamp: "2026-03-06T00:00:00Z"
---

# A-4: AC Feasibility Check on DC OPF Dispatch (TINY, IEEE 39-bus)

## Result: PASS

## Approach

Solved DC OPF to obtain optimal dispatch, then fixed generator active power (Pg) values in the same data dictionary and ran `compute_ac_pf` to check AC feasibility. No file export or reimport was needed -- the entire workflow operates on the in-memory PowerModels data dict.

1. `PowerModels.parse_file("case39.m")` to load network data
2. `PowerModels.solve_dc_opf(data, HiGHS.Optimizer)` with duals enabled to get optimal dispatch
3. Set `data["gen"][id]["pg"] = dc_dispatch[id]` for all generators (in-place modification)
4. `PowerModels.compute_ac_pf(data)` to run Newton-Raphson AC power flow on the fixed dispatch
5. `PowerModels.calc_branch_flow_ac(data)` to compute branch P/Q flows
6. Compare bus voltages against `vmin`/`vmax` bounds for voltage violations
7. Compare apparent branch flows against `rate_a` for thermal violations

### Convergence Protocol

Flat start (default Vm=1.0, Va=0.0) succeeded on first attempt. No warm start or tolerance relaxation was needed.

## Output

- **DC OPF termination:** OPTIMAL (objective: 41,263.94)
- **AC PF convergence:** true (flat start, first attempt)
- **Voltage violations:** 1 bus
  - Bus 36: Vm = 1.0636 p.u. (limit: 1.06) -- overvoltage by 0.0036 p.u.
- **Thermal violations:** 0 branches (no overloads)
- **Voltage magnitude range:** 0.982 to 1.064 p.u. (mean: 1.025)
- **Total active power loss:** 0.458 p.u. (45.8 MW on 100 MVA base)
- **Total reactive power loss:** 0.350 p.u.
- **Dispatch difference (AC vs DC):**
  - Gen 2 (slack): AC dispatch 6.918 p.u. vs DC dispatch 6.460 p.u. (+0.458 p.u. to cover losses)
  - All other generators: identical dispatch (DC Pg values maintained)
  - The slack generator absorbs the 0.458 p.u. active power losses

## Workarounds

None required. The workflow is clean and natural:
- PowerModels' data dict is mutable -- generator Pg values can be set directly
- `compute_ac_pf` operates on the modified dict without any intermediate serialization
- Voltage and thermal limits are available from the data dict for violation checking
- `calc_branch_flow_ac` provides apparent power flows for thermal comparison

## Timing

- Wall-clock: 0.433s (including DC OPF + AC PF, excludes JIT warm-up)
- DC OPF solve: ~0.001s (HiGHS QP)
- AC PF solve: managed internally by NLsolve
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a4_ac_feasibility.jl`
