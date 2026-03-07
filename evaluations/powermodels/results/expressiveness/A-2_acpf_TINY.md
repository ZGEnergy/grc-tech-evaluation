---
test_id: A-2
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.309
peak_memory_mb: null
loc: 144
solver: NLsolve
timestamp: "2026-03-06T00:00:00Z"
---

# A-2: Solve ACPF (Newton-Raphson) on TINY (IEEE 39-bus)

## Result: PASS

## Approach

Used PowerModels' native `compute_ac_pf(data)` function, which uses NLsolve.jl (Newton's method) in polar coordinates without JuMP. Convergence protocol followed:

1. `PowerModels.parse_file("case39.m")` to load network
2. `PowerModels.compute_ac_pf(data)` -- flat start (all Vm=1.0, Va=0.0)
3. Converged on first attempt (flat start succeeded)
4. `PowerModels.update_data!(data_solved, sol)` + `PowerModels.calc_branch_flow_ac(data_solved)` for P/Q flows

No warm start or tolerance relaxation was needed.

## Output

- **Convergence:** true (flat start, NLsolve Newton)
- **39 bus voltages** extracted:
  - Vm range: 0.982 to 1.064 p.u.
  - Va sample: Bus 1: -0.2363 rad, Bus 2: -0.1708 rad
- **46 branch P/Q flows** computed via `calc_branch_flow_ac`:
  - Each branch has `pf`, `pt`, `qf`, `qt` (from/to active/reactive)
  - Branch losses: `p_loss = pf + pt`, `q_loss = qf + qt`
- **Total system losses:**
  - Active power loss: 0.4364 p.u. (43.64 MW on 100 MVA base)
  - Reactive power loss: -1.1216 p.u. (net reactive generation from line charging)
- **Sample branch 3:** pf=3.199, pt=-3.186, p_loss=0.013 p.u.

## Workarounds

None required. `compute_ac_pf` converged with default flat start on IEEE 39-bus.

## Timing

- Wall-clock: 0.309s (including parse, excludes JIT warm-up)
- Peak memory: not measured
- Iterations: managed internally by NLsolve

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a2_acpf.jl`
