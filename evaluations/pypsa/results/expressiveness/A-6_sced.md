---
test_id: A-6
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 5577e704
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 3.01
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 453
solver: HiGHS
timestamp: 2026-03-13T00:00:00Z
---

# A-6: SCED — Economic Dispatch with Fixed Commitment

## Result: QUALIFIED PASS

## Approach

Two-stage UC-then-ED workflow using PyPSA 1.1.2:

**Stage 1 (UC/MILP):** Loaded case39.m via shared `matpower_loader.load_pypsa()` and assigned Modified Tiny parameters (differentiated marginal costs: hydro $5, nuclear $10, coal $25, gas $40; ramp rates, min up/down times, startup costs from `gen_temporal_params.csv`). Set `committable=True` for all 10 generators and solved 24-hour horizon with HiGHS MILP (`mip_rel_gap=0.01`).

**Stage 2 (ED/LP):** Reloaded a fresh network with the same parameters, then:
1. Set `committable=False` on all generators (removes binary variables)
2. Applied time-varying `p_min_pu` and `p_max_pu` via `generators_t` DataFrames based on Stage 1 commitment schedule: committed hours get [0.3, 1.0] bounds, decommitted hours get [0.0, 0.0]
3. Solved as pure LP with HiGHS

Ramp constraints (`ramp_limit_up`, `ramp_limit_down`) were preserved from Stage 1 and enforced in Stage 2 independently.

## Output

| Metric | Value |
|--------|-------|
| UC objective | $1,015,773 |
| ED objective | $978,629 |
| Cost difference | 3.66% |
| UC solve time | ~1.5s |
| ED solve time | ~0.5s |
| ED binary variables | 0 (pure LP confirmed) |
| Ramp violations (ED) | 0 |
| Near-limit ramp pairs (>80%) | 5 |
| Cycling generators (UC) | G3, G6, G9 (3 generators) |

**Commitment schedule:** 3 generators cycled (G3/coal, G6/gas CC, G9/gas CC), decommitting during low-load hours. Remaining 7 generators stayed committed for all 24 hours.

**Ramp enforcement in ED stage:** 0 violations across all generator-interval checks. The tightest ramp pair was G3 at hour 7 (447/447 MW, 100% utilization), demonstrating that ramp constraints are binding and actively enforced in the LP ED stage independently of the UC formulation.

**ED dispatch ranges (MW):**

| Generator | Min | Max | Pnom | MC ($/MWh) |
|-----------|-----|-----|------|------------|
| G0 (hydro) | 843 | 900 | 1040 | $5 |
| G1 (nuclear) | 479 | 646 | 646 | $10 |
| G2 (nuclear) | 448 | 725 | 725 | $10 |
| G3 (coal) | 0 | 652 | 652 | $25 |
| G4 (coal) | 152 | 508 | 508 | $25 |
| G5 (nuclear) | 622 | 687 | 687 | $10 |
| G6 (gas CC) | 0 | 472 | 580 | $40 |
| G7 (nuclear) | 169 | 564 | 564 | $10 |
| G8 (nuclear) | 260 | 865 | 865 | $10 |
| G9 (gas CC) | 0 | 330 | 1100 | $40 |

## Workarounds

- **What:** Fixed commitment schedule by setting `committable=False` and applying time-varying `p_min_pu`/`p_max_pu` bounds via `generators_t` DataFrames. Committed hours get [0.3, 1.0] bounds; decommitted hours get [0.0, 0.0].
- **Why:** PyPSA has no single-call API to fix UC decisions and re-solve as LP (e.g., no `fix_commitment()` method). The two-stage separation must be done manually by manipulating generator bounds.
- **Durability:** stable — uses documented public API (`generators_t.p_min_pu`, `generators_t.p_max_pu`, `committable` attribute). The approach is a standard pattern combining public API calls.
- **Grade impact:** Minor. The workaround uses only documented API. The lack of a dedicated `fix_commitment()` convenience method is a usability gap, not an architectural limitation.

## Timing

- **Wall-clock:** 3.01s (total for both stages)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (LP/MILP)
- **CPU cores used:** 1 (threads=1)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a6_sced_tiny.py`
