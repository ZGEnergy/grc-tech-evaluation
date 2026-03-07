---
test_id: A-3
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.669
peak_memory_mb: null
loc: 124
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-3: Solve DC OPF with gen costs and line flow limits on TINY (IEEE 39-bus)

## Result: PASS

## Approach

Used PowerModels' convenience function `solve_dc_opf` with HiGHS solver and dual extraction enabled.

1. `PowerModels.parse_file("case39.m")` to load network
2. `PowerModels.solve_dc_opf(data, optimizer, setting=Dict("output" => Dict("duals" => true)))` to solve with LMP extraction
3. LMPs extracted from `result["solution"]["bus"][id]["lam_kcl_r"]` (active power balance dual)
4. Optimal dispatch from `result["solution"]["gen"][id]["pg"]`
5. Branch flows from `result["solution"]["branch"][id]["pf"]`

Solver settings: `time_limit=300, presolve="on", threads=1, output_flag=true`.

The case39.m generators have quadratic cost functions (model=2), so HiGHS solves this as a QP.

## Output

- **Termination status:** OPTIMAL
- **Objective value:** 41,263.94 (total generation cost, $/hr)
- **Solve time:** 0.0014s
- **Optimal dispatch (10 generators):**
  - Gens 1, 3, 6, 9, 10 dispatched near 6.61 p.u. (similar marginal costs)
  - Gen 2: 6.46, Gen 4: 6.52, Gen 5: 5.08, Gen 7: 5.80, Gen 8: 5.64
  - Total generation: 62.54 p.u.
- **LMPs (39 buses):**
  - All LMPs approximately -1351.69 $/MWh (nearly uniform -- uncongested network)
  - LMP range: -1351.692 to -1351.692 (spread < 0.001)
  - Negative sign reflects the dual convention (shadow price on equality constraint)
- **Branch flows** accessible from solution dict

## Workarounds

None required. Single function call with duals setting produces complete results.

## Timing

- Wall-clock: 1.669s (including parse and JuMP model build, excludes JIT)
- Solve time: 0.0014s (HiGHS QP solve only)
- Peak memory: not measured
- Iterations: 100 (QP ASM) + 33 (Simplex)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a3_dcopf.jl`
