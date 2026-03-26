---
test_id: A-9
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "f98c9cad"
status: partial_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.03
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 561
solver: "HiGHS (via scipy.optimize.linprog)"
timestamp: "2026-03-24T00:00:00Z"
---

# A-9: Solve DC OPF with N-1 contingency flow constraints embedded in optimization

## Result: PARTIAL PASS

## Approach

pandapower 3.4.0 has no native SCOPF function. The test investigated three potential paths:

1. **Native SCOPF API:** No `runscopf()` or equivalent exists. OPF-related functions (`rundcopp`, `runopp`, `runpm_*`) all solve single-period, single-contingency problems.

2. **PYPOWER userfcn callback system:** pandapower bundles PYPOWER which has an `add_userfcn` mechanism that allows injecting custom linear constraints at the `formulation` stage of the OPF. However, pandapower's `rundcopp` does not expose a public API to inject user-defined userfcn callbacks into the ppc before solving. The userfcn system is used internally (e.g., for DC line constraints) but not exposed for user customization. [tool-specific: OPF not extensible through public API]

3. **Post-hoc contingency analysis:** `pandapower.contingency.run_contingency()` exists but is post-hoc -- it runs power flow for each contingency independently after the base-case OPF, not embedding constraints in the optimization.

4. **Manual PTDF-based LP (blocking workaround):** The test constructed a SCOPF LP from scratch using pandapower only for network loading and PTDF computation, with scipy.optimize.linprog (HiGHS backend) as the solver.

### SCOPF construction details

- Extracted PYPOWER PPC data via internal `_pd2ppc()` function
- Computed PTDF matrix via `pandapower.pypower.makePTDF.makePTDF()`
- Computed LODF (Line Outage Distribution Factor) matrix for N-1 contingencies
- Excluded 11 radial branches (LODF denominator near zero = removal causes islanding)
- Built LP with base-case + N-1 contingency flow constraints
- Full SCOPF (all 35 non-radial contingencies) was **infeasible** with 70% branch derating
- Used incremental approach: added contingencies one at a time, skipping those that caused combined infeasibility
- Final solution includes 19 of 35 non-radial contingencies (16 skipped)

## Output

| Metric | Value |
|--------|-------|
| Native SCOPF | No |
| Contingency analysis type | Post-hoc only (not optimization-embedded) |
| SCOPF approach | Manual PTDF-based LP via scipy (blocking workaround) |
| Base LP cost (no contingencies) | 9.481213e+04 |
| SCOPF cost (19 contingencies) | 1.269270e+05 |
| **Cost increase from N-1** | **33.87%** |
| Base-case max loading | 1.000000e+02% |
| Max contingency loading | 1.000000e+02% |
| Full SCOPF feasible | No (infeasible with all 35 contingencies + 70% derating) |
| Contingencies included | 19 / 35 non-radial (11 radial skipped) |
| Contingencies skipped (infeasible) | 16 |
| SCOPF solve time | 1.892035e-02 s |

**SCOPF generator dispatch (MW):**

| Gen | Bus | Dispatch MW | Pmax MW | Tech |
|-----|-----|-------------|---------|------|
| 0 | 30 | 991.99 | 9999.00 | Hydro (ext_grid) |
| 1 | 29 | 359.67 | 1040.00 | Nuclear |
| 2 | 31 | 420.00 | 725.00 | Nuclear |
| 3 | 32 | 592.00 | 652.00 | Coal |
| 4 | 33 | 508.00 | 508.00 | Coal |
| 5 | 34 | 630.00 | 687.00 | Nuclear |
| 6 | 35 | 556.10 | 580.00 | Gas CC |
| 7 | 36 | 231.47 | 564.00 | Nuclear |
| 8 | 37 | 865.00 | 865.00 | Nuclear |
| 9 | 38 | 1100.00 | 1100.00 | Gas CC |

**Cost comparison:** The SCOPF cost is 33.87% higher than the base-case LP (no contingencies), confirming that N-1 constraints bind and alter dispatch. The comparison uses the same linear cost formulation (cp1 only) for fairness. The pandapower quadratic OPF cost (1.569294e+05 via `net.res_cost`) is not directly comparable.

**Skipped contingencies:** 16 contingencies were individually feasible but created combined infeasibility when added to the constraint set. This is a legitimate SCOPF phenomenon -- the intersection of all N-1 constraint sets is empty with 70% branch derating on case39.

## Workarounds

- **What:** Complete SCOPF LP built from scratch using `scipy.optimize.linprog` (HiGHS backend). pandapower is used only for (a) network data loading via `load_pandapower()` and (b) PTDF computation via `pandapower.pypower.makePTDF.makePTDF()`. The entire OPF formulation, LODF computation, and N-1 constraint construction are manual. pandapower's `rundcopp` is not used for the SCOPF solve.
- **Why:** pandapower's PYPOWER OPF solver does not support arbitrary user-defined constraints. The `userfcn` callback system exists internally but is not exposed through a public API for custom constraint injection.
- **Durability:** blocking -- the workaround bypasses pandapower's OPF entirely. It also relies on internal `_pd2ppc()` function (underscore-prefixed = private API) to extract the PYPOWER PPC representation.
- **Grade impact:** Blocking failure on native SCOPF. The manual approach demonstrates that SCOPF is *achievable* by using pandapower as a data container, but the tool's OPF is not extensible enough to support it directly.

## Timing

- **Wall-clock:** 1.03 s (includes network loading, base DC OPF, SCOPF LP construction and solve)
- **Timing source:** measured
- **SCOPF solve time:** 0.019 s (HiGHS LP via scipy)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a9_scopf.py`
