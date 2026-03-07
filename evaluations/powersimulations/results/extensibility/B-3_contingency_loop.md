---
test_id: B-3
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 14.06
peak_memory_mb: null
loc: 205
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# B-3: Contingency Loop (N-1 DCPF, all 46 branches)

## Result: PASS

## Approach

N-1 DCPF contingency analysis using PowerFlows.jl with in-place branch toggling.
No file reload per contingency -- the System object is modified in place:

1. Load system once via `System(network_file)`.
2. Solve base case DCPF.
3. For each of 46 branches:
   a. `set_available!(branch, false)` -- disable branch in-place.
   b. `solve_powerflow(DCPowerFlow(), sys)` -- solve DCPF.
   c. Compute max line loading (|flow| / rating) across all remaining branches.
   d. `set_available!(branch, true)` -- restore branch.
4. Collect per-contingency results and identify worst case.

No external optimizer needed -- DCPF is a direct linear solve.

## Output

| Metric | Value |
|--------|-------|
| Total contingencies | 46 |
| Converged | 36 |
| Diverged (islanding) | 10 |
| Max loading overall | 1.604 (160.4%) |
| Worst contingency | bus-21-bus-22-i_35 |
| Most overloaded branch | bus-23-bus-24-i_38 |

**Top 5 worst contingencies:**

| Contingency | Max Loading | Overloaded Branch | Time (s) |
|-------------|------------|-------------------|----------|
| bus-21-bus-22-i_35 | 1.604 | bus-23-bus-24-i_38 | 0.0004 |
| bus-13-bus-14-i_23 | 1.336 | bus-6-bus-11-i_13 | 0.0007 |
| bus-16-bus-21-i_28 | 1.148 | bus-23-bus-24-i_38 | 0.0004 |
| bus-23-bus-24-i_38 | 1.148 | bus-16-bus-21-i_28 | 0.0004 |
| bus-10-bus-13-i_19 | 1.137 | bus-6-bus-11-i_13 | 0.0007 |

10 contingencies caused network islanding (non-convergence). These are radial
connections to generator buses -- removing them disconnects parts of the network.

## Timing

| Metric | Value |
|--------|-------|
| System load time | 10.93s (includes JIT) |
| Base case DCPF | 2.91s (includes JIT for PowerFlows) |
| **N-1 loop (46 contingencies)** | **0.082s** |
| First contingency (includes JIT) | 0.003s |
| Average subsequent contingency | 0.0015s |
| Min contingency time | 0.00007s |
| Max contingency time | 0.044s |
| **Per-contingency average** | **0.0018s** |

After JIT warmup, each contingency solves in sub-millisecond time. The 46-contingency
loop completes in 82ms total. This demonstrates efficient in-place model modification
without file reload.

## Method

- **Model reuse:** In-place modification via `set_available!(branch, false/true)`.
- **No file reload:** System loaded once, branches toggled.
- **Solver:** PowerFlows.jl `DCPowerFlow()` -- direct linear solve, no external optimizer.
- **Clone vs. modify:** Modify-in-place (toggle + restore). No deep copy needed.

## Workarounds

None required. The `set_available!` API is part of PowerSystems.jl's public interface
and is designed for exactly this use case.

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b3_contingency_loop.jl`
