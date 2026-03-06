# Observation: api-friction (expressiveness)

## Source Tests
A-3, A-4, A-5, A-6, A-8, A-9, A-11

## Findings

### 1. Gencost Not Imported (A-3, A-5)
`import_from_pypower_ppc()` explicitly ignores gencost data. All generators get `marginal_cost=0` and `marginal_cost_quadratic=0`. Users must manually parse and assign costs from the CaseFrames gencost DataFrame.

**Severity:** Moderate. The workaround is stable and ~5 lines of code, but it's a common surprise for users coming from MATPOWER.

### 2. MIQP Not Supported by HiGHS (A-5)
HiGHS cannot solve mixed-integer quadratic programs. When `committable=True` with `marginal_cost_quadratic > 0`, HiGHS returns status "unknown" with zero objective. No error is raised — the failure is silent.

**Severity:** High for UC problems with quadratic costs. SCIP may handle MIQP, or costs must be linearized.

### 3. distribute_slack Silently Ignored in optimize() (A-11)
Passing `distribute_slack=True` to `n.optimize()` does not raise an error. The parameter flows through `**kwargs` to `solver_options` and then to HiGHS, which logs "Option 'distribute_slack' is unknown" but continues. The parameter has no effect.

**Severity:** High. Silent parameter swallowing is a common source of bugs.

### 4. set_scenarios() Incompatible with pypower Import (A-8)
`n.set_scenarios()` works with networks built via `n.add()` but crashes with pypower-imported networks due to MultiIndex/flat-index incompatibility in `find_bus_controls()`.

**Severity:** High for users who import MATPOWER cases and want stochastic optimization.

### 5. SCOPF branch_outages Format Underdocumented (A-9)
The `branch_outages` parameter accepts line name strings but the handling of transformer names is unclear. Passing tuples or MultiIndex objects produced errors. Only plain line name strings worked.

**Severity:** Low-moderate. Lines-only contingencies are the common case.
