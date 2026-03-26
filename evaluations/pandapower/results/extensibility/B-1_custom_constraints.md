---
test_id: B-1
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "fececf15"
status: partial_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 1.11
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 401
solver: "PYPOWER interior-point (bundled)"
timestamp: "2026-03-24T00:00:00Z"
---

# B-1: Add flow gate limit to DC OPF and assert on dual value

## Result: PARTIAL PASS

## Approach

pandapower's native DC OPF (`rundcopp`) uses the bundled PYPOWER interior-point solver, which supports custom linear constraints via the inherited PYPOWER `userfcn` callback mechanism. However, pandapower does not document or expose this mechanism in its own API.

The approach required:

1. **Replicating `_optimal_powerflow`:** pandapower's internal `_optimal_powerflow` function (in `optimal_powerflow.py`) orchestrates the DC OPF pipeline: DataFrame-to-ppc conversion, OPF model setup, solver call, and result extraction. To inject a custom userfcn, this function was replicated with the addition of an `add_userfcn('formulation', callback)` call before the solver runs.

2. **Monkey-patching `pandapower.run._optimal_powerflow`:** Since `rundcopp` calls `_optimal_powerflow` via a module-level import in `pandapower.run`, the reference in that module's namespace was temporarily replaced with the custom version.

3. **Building the constraint using `Bf` matrix:** The flow gate constraint was formulated as a linear constraint on the `[Va, Pg]` OPF variables using the `Bf` (branch-from) admittance matrix from `makeBdc()`. The constraint takes the form `-limit - Pfinj <= Bf_row @ Va <= limit - Pfinj`, which correctly accounts for phase-shifter injection corrections.

4. **Capturing duals:** pandapower discards the PYPOWER result dict (containing `mu`, `lin`, `var` duals) during result extraction back to DataFrames. The custom `_optimal_powerflow` captures `result['lin']['mu']` before it is discarded, allowing extraction of the flowgate constraint dual.

**Verification with non-binding and binding cases:**

| Case | Flow Gate Limit | Objective | Dual | Gate Flow |
|------|----------------|-----------|------|-----------|
| Baseline (no gate) | -- | $156,929 | -- | -1333.2 MW |
| Non-binding (2x) | 2666.4 MW | $156,929 | 0.0 | -1333.2 MW |
| Binding (50%) | 666.6 MW | $202,401 | -19,573.3 | -666.6 MW |

## Output

- **Baseline objective:** $156,929.39
- **Non-binding gate limit:** 2666.4 MW (2x unconstrained flow)
  - Objective: $156,929.39 (unchanged from baseline)
  - Flow gate dual: 0.0 (correct: not binding)
- **Binding gate limit:** 666.6 MW (50% of unconstrained flow)
  - Objective: $202,400.59 (29.0% increase)
  - Flow gate dual: -19,573.27 (nonzero: binding)
  - Constrained flow: -666.6 MW (matches limit)
- **Gate branch:** ppc index 36, from bus 5 to bus 30

The dual correctly reflects binding status: zero when non-binding, nonzero when binding. The objective increases when the constraint binds, confirming the constraint is active in the optimization.

## Workarounds

- **What:** Replicated pandapower's internal `_optimal_powerflow` function to inject a PYPOWER `userfcn` callback and capture the PYPOWER result dict (containing constraint duals). Required monkey-patching `pandapower.run._optimal_powerflow`.
- **Why:** pandapower does not expose the PYPOWER userfcn mechanism in its public API. The `add_userfcn` call is only made internally for dcline constraints. Additionally, pandapower discards the PYPOWER result dict containing constraint duals (`mu`, `lin`, `var`) during result extraction. [tool-specific: no public custom constraint API]
- **Durability:** fragile -- The workaround depends on the internal structure of `_optimal_powerflow` (undocumented private function), the PYPOWER `opf_model.add_constraints` interface, and the internal result dict structure. Any refactoring of the OPF pipeline would break this approach.
- **Grade impact:** Full capability is demonstrated (constraint injection + dual extraction both work correctly), but the mechanism requires replicating an internal function and monkey-patching a private module reference. This is a fragile workaround, resulting in partial_pass rather than qualified_pass.

## Timing

- **Wall-clock:** 1.11 s (3 OPF solves: baseline + non-binding + binding)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported by PYPOWER DC OPF
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b1_custom_constraints.py`

Key code pattern for injecting the userfcn:

```python
from pandapower.pypower.add_userfcn import add_userfcn
from pandapower.pypower.makeBdc import makeBdc

_, Bf, Pbusinj, Pfinj, *_ = makeBdc(ppci["bus"], ppci["branch"])
ppci = add_userfcn(ppci, "formulation", _add_flowgate_constraint, args=userfcn_args)
```

And the constraint callback:

```python
def _add_flowgate_constraint(om, args):
    A_gate = hstack([Bf[gate_idx, :], zeros(1, ng)], format="csr")
    om.add_constraints("flowgate", A_gate, l, u, ["Va", "Pg"])
    return om
```
