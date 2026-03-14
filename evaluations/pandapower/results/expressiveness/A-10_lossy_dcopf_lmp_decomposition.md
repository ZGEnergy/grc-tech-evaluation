---
test_id: A-10
tool: pandapower
dimension: expressiveness
network: TINY
status: fail
workaround_class: blocking
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "0a550931"
wall_clock_seconds: 0.78
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 246
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-10: Solve DC OPF with loss approximation and decompose LMPs

## Result: FAIL

## Approach

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Inspected `rundcopp()` signature for loss-related parameters -- found only `trafo3w_losses` (controls how 3-winding transformer losses are allocated, not a DC OPF loss approximation).
3. Searched `pandapower` namespace for loss-related public attributes -- found only `runpm_ploss()` (a PandaModels.jl function that minimizes total power losses, not a lossy DC OPF).
4. Inspected the PYPOWER `dcopf_solver` source code -- confirmed no loss modeling in the DC OPF formulation.
5. Ran standard lossless DC OPF with differentiated costs to verify baseline LMP extraction works.
6. Checked `res_bus` columns after OPF -- found `lam_p` and `lam_q` (total LMPs) but no decomposition columns for energy, congestion, or loss components.
7. Checked PYPOWER result structure (`net._ppc["bus"]`) -- 18 columns total, with LAM_P at column 13 providing total LMPs only.

## Output

| Capability | Available |
|---|---|
| Lossless DC OPF | Yes (`rundcopp()`) |
| Lossy DC OPF (loss approximation) | No |
| Total LMPs (LAM_P) | Yes (via `res_bus.lam_p` or `net._ppc`) |
| LMP energy component | No |
| LMP congestion component | No |
| LMP loss component | No |
| Per-line congestion rent | No (no decomposed LMP output) |

**Lossless DC OPF baseline (for reference):**

| Metric | Value |
|---|---|
| Converged | Yes |
| LMP range | $14.00 -- $47.00/MWh |
| LMP sample (bus 0) | $47.00/MWh |

pandapower's DC OPF uses the standard B-theta linearization which ignores network losses entirely. The `res_bus.lam_p` column provides total bus shadow prices on the power balance constraint, but there is no mechanism to decompose these into energy, congestion, and loss components. The PYPOWER backend's bus result matrix has exactly 18 columns (standard PYPOWER format) with no additional decomposition fields.

The PandaModels.jl bridge offers `runpm_ploss()` for loss minimization but this is a different formulation (minimize total losses as an objective) and does not produce lossy LMPs or LMP decomposition.

## Workarounds

- **What:** No workaround available. Lossy DC OPF with LMP decomposition cannot be achieved within pandapower's API.
- **Why:** pandapower's DC OPF formulation is hardcoded as lossless B-theta in the PYPOWER backend. There is no parameter to enable loss approximation, and no output path for LMP decomposition.
- **Durability:** blocking -- the formulation does not exist in the codebase. Achieving this would require either (a) building a custom Pyomo/JuMP model from scratch using pandapower's network data, or (b) forking the PYPOWER solver to add loss terms.
- **Grade impact:** Blocking limitation for LMP decomposition expressiveness.

## Timing

- **Wall-clock:** 0.78 s (includes lossless baseline OPF solve)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a10_lossy_dcopf_lmp_decomposition.py`
