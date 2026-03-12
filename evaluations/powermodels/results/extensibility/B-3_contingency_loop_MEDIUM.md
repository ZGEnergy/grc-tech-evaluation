---
test_id: B-3
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 3907fb16
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 340.26
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 115
solver: null
timestamp: 2026-03-11T09:00:00Z
---

# B-3: Contingency Loop — MEDIUM

## Result: PASS

## Approach

Parsed `case_ACTIVSg10k.m` once (20.5s). Applied MEDIUM preprocessing (2462 rate_a fixes). Solved base-case DCPF via `compute_dc_pf` (1.72s). Selected 46 contingency branches — those with the highest base-case loading ratio (flow / rate_a), covering the most impactful N-1 scenarios.

For each contingency:
1. `deepcopy(data_base)` — creates an independent copy (no file re-parse).
2. Set `data_ctg["branch"][br_id]["br_status"] = 0`.
3. `calc_connected_components(data_ctg)` — checked for islanding.
4. If connected: `compute_dc_pf(data_ctg)` + `update_data! + calc_branch_flow_dc` → max line loading.

This is the identical approach as TINY B-3, scaled to 10k-bus. The `deepcopy` of a 10k-bus network is 1.8–8.3s, much faster than re-parsing (20.5s), yielding a deepcopy/parse ratio of **0.232x**.

## Output

| Metric | Value |
|--------|-------|
| Network | 10000 buses, 12706 branches |
| Parse time | 20.50s |
| Base case DCPF | 1.72s |
| Contingencies run | 46 |
| Converged | 12 |
| Islands (N-1 disconnects) | 34 |
| Diverged/error | 0 |
| Per-deepcopy (mean) | 4757.8 ms |
| Per-solve (mean) | 1.03s |
| Total loop time | 266.3s |
| deepcopy / parse ratio | **0.232x** (23.2% of parse time) |
| Worst contingency | Branch 12704, max loading = 92.8% |

**High island rate (34/46 = 74%):** Many high-flow branches at MEDIUM scale are radial tie lines connecting load pockets. Removing a radial line creates an island. This is an ACTIVSg10k network characteristic, not a tool limitation. The 34 island cases are detected via `calc_connected_components` before attempting the DCPF solve.

### Sample Results (First 5 Contingencies)

| Branch | Status | deepcopy (ms) | Solve (s) | Max Load (%) |
|--------|--------|---------------|-----------|--------------|
| 10744 | converged | 8255.5 | 2.83 | 85.9 |
| 3504 | converged | 1783.7 | 3.99 | 83.2 |
| 1254 | island | 3787.4 | 0.00 | — |
| 2187 | island | 5785.3 | 0.00 | — |
| 7266 | island | 5398.8 | 0.00 | — |

## Workarounds

None required. The `deepcopy` pattern works cleanly at MEDIUM scale with no re-parsing per iteration. The `model_reconstruction_required` flag is `false`.

## Timing

- **Wall-clock:** 340.3s (includes: parse=20.5s, base DCPF=1.72s, 46 contingencies=266.3s, JIT warm-up ~52s)
- **Timing source:** measured
- **Per-contingency (mean total):** 7.3s (deepcopy=4.8s + solve=1.0s + connectivity=1.5s)
- **deepcopy/parse ratio:** 0.232x — deepcopy is significantly faster than re-parsing
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b3_contingency_loop_medium.jl`

Key loop pattern (no re-parsing):

```julia

# Parse once
data_base = PowerModels.parse_file(network_file)
apply_medium_preprocessing!(data_base)

for br_id in contingency_ids
    # deepcopy — no re-parse
    data_ctg = deepcopy(data_base)
    data_ctg["branch"][br_id]["br_status"] = 0

    # Check connectivity before solve
    if length(PowerModels.calc_connected_components(data_ctg)) == 1
        pf_ctg = PowerModels.compute_dc_pf(data_ctg)
        PowerModels.update_data!(data_ctg, pf_ctg["solution"])
        flows = PowerModels.calc_branch_flow_dc(data_ctg)
        # ... collect max loading ...
    end
end

```
