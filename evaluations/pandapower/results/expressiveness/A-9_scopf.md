---
test_id: A-9
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "e3ccffc8"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 0.83
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 257
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-13T00:00:00Z"
---

# A-9: Solve DC OPF with N-1 contingency flow constraints embedded in optimization

## Result: FAIL

## Approach

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Applied differentiated generator costs from Modified Tiny data (same as A-3).
3. Applied 70% branch derating (same as A-3).
4. Investigated whether pandapower can solve SCOPF — DC OPF with N-1 contingency flow limits embedded in the optimization (not post-hoc).

### Capability investigation

**Native SCOPF:** pandapower has no `runscopf()` or equivalent function. The OPF-related functions found in the API are:

| Function | Description | SCOPF? |
|---|---|---|
| `pp.rundcopp()` | DC OPF (single period, no contingency constraints) | No |
| `pp.runopp()` | AC OPF (single period, no contingency constraints) | No |
| `pp.runpm_ac_opf()` | AC OPF via PandaModels.jl Julia bridge | No |
| `pp.runpm_dc_opf()` | DC OPF via PandaModels.jl Julia bridge | No |
| `pp.runpm_storage_opf()` | Storage OPF via Julia bridge | No |

**Contingency analysis:** pandapower has `pandapower.contingency.run_contingency()` and `run_contingency_ls2g()`, but these perform **post-hoc** N-1 checking — they run a power flow for each contingency case independently after the base-case OPF is solved. Contingency constraints are NOT part of the optimization.

**Custom constraint injection:** pandapower's PYPOWER OPF solver does not support arbitrary user-defined constraints. The OPF formulation is hard-coded in the PYPOWER interior-point method. There is no API to inject additional linear constraints (such as PTDF-based contingency flow limits) into the optimization problem.

**PandaModels.jl bridge:** Not installed in the evaluation environment. Even if available, PowerModels.jl does not have a native SCOPF formulation either — it would require custom JuMP constraint construction, making the pandapower bridge irrelevant (one would build the model directly in JuMP).

### Base-case DC OPF (for reference)

To provide a comparison baseline, a standard DC OPF was solved (equivalent to A-3):

- **Converged:** Yes
- **Total generation:** 6,254.23 MW
- **N-1 contingencies possible:** 35 lines

A post-hoc contingency analysis was attempted via `run_contingency()` but produced an API error (`'list' object has no attribute 'items'`), indicating the function's expected input format differs from a simple list of line indices. This further illustrates the friction in using pandapower's contingency infrastructure.

## Output

No SCOPF solution was produced. The test confirmed:

1. No native SCOPF function exists in pandapower 3.4.0
2. Contingency analysis (`run_contingency`) is post-hoc, not optimization-embedded
3. The PYPOWER OPF solver does not support user-injected constraints
4. PandaModels.jl bridge is not available and would not resolve the gap

**Comparison with A-3 (unconstrained DC OPF):** Since SCOPF could not be solved, no dispatch/cost comparison with A-3 is possible. In a valid SCOPF, the objective would be higher than A-3's because the feasible region is smaller (N-1 constraints restrict dispatch options).

## Workarounds

- **What:** To achieve SCOPF with pandapower, one would need to build a complete custom optimization model from scratch using Pyomo, scipy.optimize, or another modeling framework. This model would:
  1. Construct the PTDF matrix (available via `pandapower.pypower.makePTDF.makePTDF()`)
  2. Formulate DC OPF constraints manually (power balance, generator limits, base-case flow limits)
  3. Compute contingency PTDFs for each N-1 case (line outage distribution factors)
  4. Add contingency flow constraints for all N-1 cases
  5. Solve the resulting LP
  This approach does not use pandapower's OPF solver at all — pandapower serves only as a data container and PTDF calculator.
- **Why:** pandapower's OPF formulation is not extensible. The PYPOWER interior-point solver is a black box with no constraint injection API.
- **Durability:** blocking — the workaround bypasses pandapower's OPF entirely and builds a parallel optimization model
- **Grade impact:** Blocking failure on SCOPF. The manual approach would be classified as "user-assembled from scratch" rather than "built-in" or "API-accessible."

## Timing

- **Wall-clock:** 0.83 s (includes network loading, base-case DC OPF solve, and contingency analysis attempt)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER DC OPF solver

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a9_scopf.py`

Key code showing the absence of SCOPF:

```python
# Check available OPF functions — none include SCOPF
opf_functions = [
    f for f in dir(pp)
    if "opf" in f.lower() or "opp" in f.lower() or "scopf" in f.lower()
]
# Result: ['OPFNotConverged', 'add_storage_opf_settings', 'opf', 'opf_task',
#           'rundcopp', 'runopp', 'runpm_ac_opf', 'runpm_dc_opf', 'runpm_storage_opf']

# PandaModels.jl bridge not available
import pandamodels  # ImportError
```
