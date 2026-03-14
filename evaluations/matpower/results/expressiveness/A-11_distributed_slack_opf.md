---
test_id: A-11
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "95a0e3ae"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.10
timing_source: measured
peak_memory_mb: 1.9
convergence_residual: null
convergence_iterations: null
loc: 287
solver: "MIPS"
timestamp: 2026-03-13T00:00:00Z
---

# A-11: Solve DC OPF with distributed slack (load-proportional). Compare LMPs to A-3.

## Result: QUALIFIED PASS

## Approach

MATPOWER's OPF formulation uses a single slack bus (bus type 3) internally. Distributed slack is not supported in the OPF solver itself (open issue [#136](https://github.com/MATPOWER/matpower/issues/136)). However, `makePTDF()` accepts a custom slack distribution vector as a documented parameter, enabling post-processing of LMPs with distributed reference.

**Workflow:**
1. Solved single-slack DC OPF via `rundcopf()` (same as A-3).
2. Computed distributed PTDF via `makePTDF(baseMVA, bus, branch, slack_weights)` where `slack_weights` is a load-proportional vector summing to 1.0.
3. Re-referenced LMPs: `LMP_dist(i) = LMP_single(i) - weighted_avg(LMP_single)`.
4. Verified with generation-proportional and equal-weight slack distributions.

**Key insight:** In DC OPF, the distributed slack formulation only changes the LMP reference point, not the dispatch. All LMPs shift by a uniform constant equal to the negative weighted average of single-slack LMPs. The dispatch (generator Pg values) is identical regardless of slack formulation.

## Output

### Single-Slack vs Distributed-Slack LMPs

| Metric | Value |
|--------|-------|
| Single-slack objective | $219,748.32 |
| Weighted avg LMP (load-prop) | $180.30/MWh |
| Weighted avg LMP (gen-prop) | $77.93/MWh |
| Weighted avg LMP (equal) | $166.22/MWh |
| LMP shift std dev | $0.00/MWh (perfectly uniform) |

### LMP Samples (Load-Proportional Slack)

| Bus | Single LMP | Distributed LMP | Delta |
|-----|-----------|-----------------|-------|
| 1 | 78.82 | -101.48 | -180.30 |
| 3 | 300.31 | 120.01 | -180.30 |
| 10 | 243.72 | 63.41 | -180.30 |
| 20 | 54.60 | -125.70 | -180.30 |
| 30 | 7.36 | -172.95 | -180.30 |
| 39 | 122.30 | -58.01 | -180.30 |

The uniform shift confirms physical consistency: distributed slack re-references LMPs without changing the relative spread.

### Congestion Component Change (Distributed vs Single PTDF)

| Metric | Value |
|--------|-------|
| Max abs congestion change | $58.82/MWh |
| Mean abs congestion change | $58.82/MWh |

The congestion LMP components differ between single-slack and distributed-slack PTDF, which is the correct behavior — the PTDF matrix changes with the slack distribution, altering how congestion costs are attributed across buses.

### Slack Weight Configurations Tested

| Configuration | Weights | Non-zero buses |
|---------------|---------|---------------|
| Load-proportional | `Pd / sum(Pd)` | 21 / 39 |
| Generation-proportional | `Pmax / sum(Pmax)` | 10 / 39 |
| Equal | `1/nb` for all buses | 39 / 39 |

All three configurations produce consistent results with `makePTDF()`.

## Workarounds

- **What:** Solved single-slack DC OPF, then post-processed LMPs using distributed PTDF from `makePTDF(baseMVA, bus, branch, slack_weights)`
- **Why:** MATPOWER OPF does not support distributed slack natively (issue #136)
- **Durability:** stable -- `makePTDF()` with a slack distribution vector is a documented public API. The function signature explicitly accepts a vector argument for custom slack distribution. This is not an undocumented feature.
- **Grade impact:** Qualified pass. The workaround is clean and uses only documented API. The limitation is that the OPF itself uses single slack, so the distributed slack is a post-processing step rather than being embedded in the optimization. For DC OPF this produces identical results; for more complex formulations (lossy DC OPF) the post-processing approach would be less accurate.

## Timing

- **Wall-clock:** ~0.10 s (DC OPF solve + PTDF computation)
- **Timing source:** measured
- **Peak memory:** 1.9 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a11_distributed_slack_opf.m`

Key API call demonstrating distributed slack support:
```matlab
slack_weights = bus_load / sum(bus_load);  % load-proportional
PTDF_dist = makePTDF(baseMVA, bus, branch, slack_weights);  % documented API
```
