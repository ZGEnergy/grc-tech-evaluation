---
test_id: F-5
tool: matpower
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: 07cd54c8
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-5: Code Inspectability

## Result: PASS

## Finding

The full execution path from API call to solver invocation is traceable through human-readable .m files. No opaque steps exist. The call chain is well-structured with clear separation between problem setup, formulation, and solve phases.

## Evidence

**Execution trace for `rundcopf()` (DC OPF):**

```
rundcopf(mpc, mpopt)           [lib/rundcopf.m, 75 lines]
  -> runopf(mpc, mpopt)        [lib/runopf.m]
    -> opf(mpc, mpopt)         [lib/opf.m, 305 lines]
      -> opf_setup(mpc, mpopt) [lib/opf_setup.m, 574 lines]
        -> makeBdc(mpc)        [lib/makeBdc.m, 86 lines]  -- B-matrix construction
        -> makeAang(...)       [lib/makeAang.m]            -- angle constraints
        -> makeAvl(...)        [lib/makeAvl.m]             -- var limits
      -> opf_execute(om, mpopt) [lib/opf_execute.m, 296 lines]
        -> dcopf_solver(om)     [lib/dcopf_solver.m, 154 lines]
          -> qps_matpower(...)  [lib/qps_matpower.m]       -- QP/LP dispatch
            -> qps_mips(...)    [mips/lib/qps_mips.m]      -- MIPS solver (or external)
```

**Execution trace for `rundcpf()` (DC power flow):**

```
rundcpf(mpc, mpopt)            [lib/rundcpf.m]
  -> runpf(mpc, mpopt)         [lib/runpf.m]
    -> dcpf(B, Pbus, Va0, ref) [lib/dcpf.m, 46 lines]     -- direct linear solve
      -> makeBdc(mpc)          [lib/makeBdc.m, 86 lines]   -- B-matrix
```

**Module inventory for DCOPF path:**

| Module | Location | Lines | Opaque? |
|--------|----------|-------|---------|
| rundcopf | lib/rundcopf.m | 75 | No |
| opf | lib/opf.m | 305 | No |
| opf_setup | lib/opf_setup.m | 574 | No |
| opf_execute | lib/opf_execute.m | 296 | No |
| dcopf_solver | lib/dcopf_solver.m | 154 | No |
| makeBdc | lib/makeBdc.m | 86 | No |
| qps_matpower | lib/qps_matpower.m | ~200 | No |
| qps_mips (MIPS) | mips/lib/qps_mips.m | ~300 | No |

**Opaque steps:** 0

Every function in the chain is a plain .m text file. The B-matrix construction, constraint assembly, objective function setup, and solver dispatch are all directly readable. Variable naming follows power systems conventions (e.g., `Va` for voltage angles, `Pbus` for bus injections, `Bf` for branch susceptance matrix).

## Implications

MATPOWER achieves the highest level of code inspectability. An auditor can trace from the top-level API call (`rundcopf`) through formulation (`makeBdc`, `opf_setup`) to solver invocation (`qps_mips`) without encountering any compiled code, obfuscated logic, or undocumented intermediate layers. This is a direct consequence of the pure-MATLAB/Octave implementation with no compiled extensions.
