---
probe_id: probe-009
tool: pandapower
source_test: P2-3
probe_type: convergence_check
classification: claim_debunked
reason: No lambda values of 1e25 observed; in_service=False either converges with normal lambdas or throws exception; convergence pattern identical to max_p_mw=0 approach
solver_version: PYPOWER interior point (pandapower 3.4.0)
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 2.23
timestamp: 2026-03-09T00:00:00Z
---

# Probe 009: Lambda values of 1e25 with in_service=False

## Original Claim

From `evaluations/pandapower/results/p2_readiness/P2-3_commitment_injection_TINY.md`:

> **Alternative method:** `net.gen.at[idx, "in_service"] = False` -- this is the natural pandapower API for decommitting elements, but causes the PYPOWER interior point solver to diverge numerically on case39. This appears to be a solver robustness issue: the solver produces lambda values on the order of 1e25, indicating numerical instability in the interior point method when the generator set changes.

The claim has two parts:
1. `in_service=False` causes solver divergence (stated as general pattern)
2. The solver produces lambda values on the order of 1e25 (specific numerical claim)

## Probe Methodology

1. Loaded case39, solved base-case DC OPF, recorded lambda values
2. Tried decommitting each of the 9 generators via `in_service=False`, solved DC OPF, recorded lambdas
3. Tried decommitting each generator via `max_p_mw=0`, solved DC OPF, recorded lambdas
4. Compared convergence patterns and lambda magnitudes between the two approaches

Script: `sweep-data/v4-to-v5/probes/pandapower/probe-009_script.py`

## Probe Results

**Base case (all generators in service):**
- Converged: Yes
- Objective: 41,264
- Lambda range: 13.52 (uniform across all buses)

**in_service=False approach (9 generators tested individually):**

| Gen | Converged | Lambda max abs | Objective |
|-----|-----------|---------------|-----------|
| 0 | Yes | 20.84 | 47,438 |
| 1 | No (exception) | — | — |
| 2 | No (exception) | — | — |
| 3 | No (exception) | — | — |
| 4 | No (exception) | — | — |
| 5 | No (exception) | — | — |
| 6 | Yes | 16.67 | 46,333 |
| 7 | Yes | 28.82 | 47,581 |
| 8 | No (exception) | — | — |

Summary: 3 converged, 6 failed with "Optimal Power Flow did not converge!" exception

**max_p_mw=0 approach (9 generators tested individually):**

| Gen | Converged | Lambda max abs | Objective |
|-----|-----------|---------------|-----------|
| 0 | Yes | 20.84 | 47,438 |
| 1 | No (exception) | — | — |
| 2 | No (exception) | — | — |
| 3 | No (exception) | — | — |
| 4 | No (exception) | — | — |
| 5 | No (exception) | — | — |
| 6 | Yes | 16.67 | 46,333 |
| 7 | Yes | 28.82 | 47,581 |
| 8 | No (exception) | — | — |

Summary: 3 converged, 6 failed — **identical convergence pattern** to in_service=False

## Analysis

The probe contradicts the original claim on both sub-claims:

1. **"in_service=False causes solver divergence"** — Partially true, but misleading. The solver fails for 6 of 9 generators regardless of whether `in_service=False` or `max_p_mw=0` is used. The exact same generators (1,2,3,4,5,8) fail with both methods, and the exact same generators (0,6,7) succeed with both methods. The failure is a property of the network topology when certain generators are removed, not of the decommitment API.

2. **"Lambda values on the order of 1e25"** — Not reproduced. When `in_service=False` converges, lambda values are physically reasonable (16-29 range). When it does not converge, the solver throws an exception rather than returning astronomical lambda values. No lambda value anywhere near 1e25 was observed.

The original test script (P2-3) used the `max_p_mw=0` workaround, claiming it was needed because `in_service=False` doesn't work. But the probe shows both approaches have identical behavior — the same generators converge and the same generators fail. The workaround is not actually a workaround; it just happens that the original test tried a generator that fails with both methods and attributed the failure to `in_service=False`.

## Classification Rationale

Classified as `claim_debunked` because:
1. The specific numerical claim (lambdas of 1e25) is not reproduced — all observed lambdas are in the 13-29 range
2. The behavioral claim (in_service=False causes divergence that max_p_mw=0 avoids) is contradicted — both methods have identical convergence patterns
3. The same pandapower version (3.4.0) and solver were used, ruling out version mismatch
4. The probe exhaustively tested all 9 generators with both methods, providing comprehensive evidence
