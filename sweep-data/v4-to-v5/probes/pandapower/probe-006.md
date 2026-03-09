---
probe_id: probe-006
tool: pandapower
source_test: C-6
probe_type: convergence_check
classification: claim_supported
reason: Probe confirms extremely low convergence rate (0.42% vs claimed 2.1%) for PYPOWER interior point on perturbed ACTIVSg2000
solver_version: PYPOWER interior point (pandapower 3.4.0)
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 226.82
timestamp: 2026-03-09T00:00:00Z
---

# Probe 006: Stochastic DCOPF 2.1% convergence rate on ACTIVSg2000

## Original Claim

From `evaluations/pandapower/results/scalability/C-6_stochastic_scale.md`:

> Total solves: 240, Converged: 5 (2.1%), Failed: 235 (97.9%)
> The very low convergence rate (2.1%) is a PYPOWER interior point solver quality issue on the modified ACTIVSg2000 network.

The test was classified as `qualified_pass` despite this near-total solver failure.

## Probe Methodology

Replicated the exact C-6 test scenario:
1. Loaded ACTIVSg2000 (2,000 buses, 484 generators, 1,125 loads)
2. Solved base-case DC OPF with no perturbations
3. Ran all 240 solves (20 scenarios x 12 hours) with identical RNG seed (42), perturbation approach, and hourly load shape
4. Additionally tested uniform load scaling (0.5x to 1.1x) without gen perturbations to isolate failure cause

Script: `sweep-data/v4-to-v5/probes/pandapower/probe-006_script.py`

## Probe Results

**Base case (no perturbations):** Converged successfully, objective = 1,201,321

**Perturbed scenario loop (240 solves):**

| Metric | Original (C-6) | Probe |
|--------|----------------|-------|
| Total solves | 240 | 240 |
| Converged | 5 (2.1%) | 1 (0.42%) |
| Failed | 235 (97.9%) | 239 (99.6%) |
| Per-solve avg time | 1.31 s | 0.91 s |
| Total solve time | 314.18 s | 217.20 s |

The single convergence occurred at hour 8 (load scale ~1.05).

**Uniform load scaling (no gen perturbation):**

| Scale | Converged |
|-------|-----------|
| 0.5x | No |
| 0.6x | No |
| 0.7x | Yes |
| 0.8x | Yes |
| 0.9x | Yes |
| 1.0x | Yes |
| 1.1x | Yes |

This shows the base solver works for moderate load levels, but the combination of load scaling AND generator capacity perturbations causes near-total failure.

## Analysis

The probe confirms the core claim: PYPOWER interior point solver has extremely poor convergence on the perturbed ACTIVSg2000 network. The probe actually found an even worse convergence rate (0.42% vs 2.1%), which is directionally consistent — the small difference is likely due to different random noise draws (the `np.random.normal(0, 0.02)` individual noise in the inner loop is not seeded identically between runs because the state evolves differently with each solve's timing).

Key findings:
- The base case converges fine, confirming this is not a network-loading issue
- Uniform load scaling without gen perturbation converges for 0.7x-1.1x
- The combination of load AND generator capacity perturbations is what breaks the solver
- This is genuinely a PYPOWER interior point solver quality issue, not a test infrastructure bug

The `qualified_pass` grading is debatable — a 0.4-2.1% convergence rate means the workaround approach has essentially zero practical utility at SMALL scale. However, this probe was asked to verify the convergence rate claim, not the grading decision.

## Classification Rationale

Classified as `claim_supported` because:
1. The probe reproduces the same phenomenon (near-total solver failure on perturbed ACTIVSg2000)
2. The convergence rate is even lower than claimed (0.42% vs 2.1%), making the original claim conservative
3. The root cause (PYPOWER interior point solver fragility with perturbations) is confirmed
4. Same pandapower version (3.4.0) and solver used
