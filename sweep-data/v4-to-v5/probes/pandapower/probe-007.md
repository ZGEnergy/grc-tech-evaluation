---
probe_id: probe-007
tool: pandapower
source_test: A-3
probe_type: formulation_audit
classification: claim_supported
reason: LMPs are truly uniform (std=6e-12); no branch exceeds 85% loading; artificial congestion produces LMP spread (16.3--24.4), confirming the base case simply has no binding constraints
solver_version: pandapower 3.4.0 (PYPOWER interior point)
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 14.20
timestamp: 2026-03-09T00:00:00Z
---

# Probe 007: Uniform LMPs across all 10,000 buses on MEDIUM DCOPF

## Original Claim

From `evaluations/pandapower/results/expressiveness/A-3_dcopf.md`:

> LMP range: 20.738 -- 20.738
> LMP mean: 20.738
> LMPs are nearly uniform across all buses (~20.738), indicating no binding line constraints in the DC OPF solution.

## Probe Methodology

1. Loaded ACTIVSg10k and solved DC OPF via `pp.rundcopp(net)`
2. Extracted LMP distribution from `net.res_bus["lam_p"]`
3. Analyzed branch loading from both pandapower results and internal ppc arrays
4. Ran congestion experiment: reduced line limits to 90% of DCPF flow on top 5 lines, re-solved DC OPF to verify LMPs change when constraints bind

Scripts: `sweep-data/v4-to-v5/probes/pandapower/probe-007_script.py`, `probe-007_congestion.py`

## Probe Results

### Base Case LMPs

| Metric | Original (A-3) | Probe |
|--------|----------------|-------|
| LMP min | 20.738 | 20.737729 |
| LMP max | 20.738 | 20.737729 |
| LMP mean | 20.738 | 20.737729 |
| LMP std | -- | 5.977e-12 |
| Unique LMPs (6dp) | 1 | 1 |
| All identical (1e-6) | Yes | Yes |
| Objective | 2,437,763.82 | 2,437,763.82 |

LMPs are truly uniform to machine precision (std = 6e-12).

### Branch Loading (Base Case)

| Metric | Lines | Transformers | All (ppc) |
|--------|-------|-------------|-----------|
| Count | 9,726 | 975 | 12,706 |
| Max loading | 76.89% | 76.93% | 84.90% |
| Mean loading | 16.30% | -- | 17.70% |
| Branches > 90% | 0 | 0 | 0 |
| Branches > 95% | 0 | 0 | 0 |

No branch exceeds 85% loading. The network has ample transmission capacity for the base case load.

Top 3 loaded branches:
1. Branch 12340: 84.90% (226 MW flow, 266 MW limit)
2. Branch 12212: 79.89% (397 MW flow, 496 MW limit)
3. Branch 9843: 76.93% (133 MW flow, 173 MW limit)

### Congestion Experiment
Reduced line limits on the 5 highest-flow lines to 90% of their DCPF flow (forcing binding constraints):

| Metric | Base Case | Congested Case |
|--------|-----------|----------------|
| Converged | Yes | Yes |
| LMP min | 20.738 | 16.325 |
| LMP max | 20.738 | 24.363 |
| LMP std | 6e-12 | 1.332 |
| Unique LMPs | 1 | 4,225 |
| LMPs uniform | Yes | No |

When constraints bind, LMPs spread from 16.3 to 24.4 across 4,225 distinct values, confirming that pandapower's DC OPF correctly produces differentiated LMPs in the presence of congestion.

## Analysis

The claim is fully supported. The uniform LMP of 20.738 is not a bug or modeling error -- it is the correct economic result for a network with no binding transmission constraints. Key evidence:

1. **No binding constraints exist.** The most loaded branch is at only 84.9% of its limit. With no branches at or near 100%, there are no congestion rents, so all buses see the same marginal cost.

2. **The solver correctly differentiates LMPs when congestion is present.** The congestion experiment proves the OPF formulation includes line limits and produces spatially varying LMPs when those limits bind.

3. **The ACTIVSg10k has generous transmission capacity** relative to its load pattern. This is a property of the test case, not a limitation of pandapower.

The original evaluation correctly diagnosed the cause ("no binding line constraints") and appropriately reported the result as a `qualified_pass` (the qualification being solver choice, not the uniform LMPs).

## Classification Rationale

Classified as `claim_supported` because:
1. The uniform LMP value is reproduced exactly (20.737729, std = 6e-12)
2. Branch loading analysis confirms no constraints are near binding (max 84.9%)
3. The congestion experiment demonstrates LMPs correctly vary when constraints do bind (LMP range 16.3--24.4)
4. The original attribution to "no binding line constraints" is verified as correct
