---
test_id: C-1
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: d84017fa
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.09
timing_source: measured
peak_memory_mb: 555.0
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 167
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T20:45:00Z
---

# C-1: DCPF Scale MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded `case_ACTIVSg10k.m` with MEDIUM preprocessing (2,462 branches rate_a set to 9999 MVA, 0 zero-reactance fixes) and solved DC power flow using `PowerModels.compute_dc_pf(data)`. This function solves the B-matrix linear system directly via Julia's backslash operator -- no JuMP, no external optimizer. JIT warm-up was performed on `case39.m` before the timed run.

**Workaround:** `compute_dc_pf` does not populate `result["solution"]["branch"]`. Branch flows must be computed manually from bus voltage angles using `(va_from - va_to - shift) / (br_x * tap)`.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators | 2,485 |
| Base MVA | 100 |
| Preprocessing: br_x=0 fixed | 0 |
| Preprocessing: rate_a=0/Inf fixed | 2,462 (19.4%) |
| Termination status | Bool=true (converged) |
| Non-zero bus angles | 9,999 / 10,000 (slack bus = 0 by definition) |
| Non-zero branch flows | 11,990 / 12,706 |
| Angle range | -2.253099e+01 deg to +1.059947e+02 deg |
| Flow range | -1.853747e+03 to +3.711890e+04 MW |

### Timing Breakdown

| Phase | Time (s) |
|-------|----------|
| Network parse (`parse_file`) | 1.65 |
| DCPF solve (`compute_dc_pf`) | 2.273221e-01 |
| Branch flow post-processing | 4.084897e-02 |
| **Total** | **2.09** |

The underlying linear algebra solve is very fast (0.23s) for a 10,000-bus system. The branch flow post-processing (manual formula over 12,706 branches) adds only 0.04s. Total wall-clock is dominated by network parsing (1.65s).

## Workarounds

- **What:** `compute_dc_pf` does not populate `result["solution"]["branch"]`. Branch flows must be computed manually from bus voltage angles using `(va_from - va_to - shift) / (br_x * tap)`.
- **Why:** `compute_dc_pf` is a lightweight linear-algebra solver that only writes bus voltage angles to the solution dict. It does not post-process branch flows.
- **Durability:** stable -- uses only documented public data dict fields (`br_x`, `tap`, `shift`, `f_bus`, `t_bus`). Scales cleanly to 12,706 branches in 0.04s.
- **Grade impact:** Minor. The data is accessible, requires ~10 lines of post-processing. Does not prevent extracting correct branch flows at scale. Same workaround documented in A-1 TINY and A-1 MEDIUM.

## Timing

- **Wall-clock:** 2.09s (post-JIT warm-up on case39, includes parse + solve + branch flow post-processing)
- **Timing source:** measured
- **Peak memory:** 555.0 MB RSS (delta ~100 MB from JIT baseline of ~455 MB)
- **Solver iterations:** N/A (direct linear algebra, no iterative solver)
- **Convergence residual:** N/A (exact linear solve via Julia backslash)
- **CPU cores used:** 1 / 32 available

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c1_dcpf_scale_medium.jl`

Key API calls:

```julia
data = PowerModels.parse_file("case_ACTIVSg10k.m")
# Preprocessing: rate_a fix
for (_, branch) in data["branch"]
    if get(branch, "rate_a", 0.0) == 0.0 || isinf(get(branch, "rate_a", 0.0))
        branch["rate_a"] = 9999.0 / base_mva
    end
end

result = PowerModels.compute_dc_pf(data)
converged = result["termination_status"] == true  # Bool
va = result["solution"]["bus"][bus_id]["va"]       # radians

# Branch flows NOT in solution -- compute manually:
pf_pu = (va_from - va_to - shift) / (br_x * tap)
pf_mw = pf_pu * base_mva
```
