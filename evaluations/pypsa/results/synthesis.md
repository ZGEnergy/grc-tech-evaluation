# PyPSA -- Phase 1 Evaluation Synthesis

**Contract:** FA714626C0006 | Grid Research Company LLC
**Tool:** PyPSA 1.1.2 (with linopy 0.6.4, highspy 1.13.1)
**Evaluation Date:** 2026-03-05
**Reference Networks:** IEEE 39-bus (TINY), ACTIVSg 2000 (SMALL), ACTIVSg 10000 (MEDIUM)

---

## Executive Summary

PyPSA is a well-engineered, actively maintained Python library for power system optimization and analysis. It demonstrates strong native support for most target problem formulations (DCPF, ACPF, DC OPF, SCUC, SCED, SCOPF, lossy OPF) with a clean pandas-based data model and a well-abstracted solver interface via linopy. The primary weaknesses are: (1) distributed slack is absent from the optimization API, (2) stochastic optimization crashes on imported networks due to a MultiIndex bug, (3) the pypower import path silently drops generator cost data, and (4) model construction and post-solve overhead dominate wall-clock times at 10k-bus scale, making some workflows impractical without workarounds. The supply chain is clean -- MIT-licensed with one manageable GPL dependency (Levenshtein, replaceable). The tool is ready for Phase 2 with noted gaps in PSS/E parsing and piecewise-linear cost curves (PR in progress).

---

## Grade Recommendations

| Criterion | Recommended Grade | Confidence | Key Evidence |
|-----------|------------------|------------|--------------|
| Problem Expressiveness | B+ | High | 9/11 formulations work natively. SCOPF and lossy OPF are native strengths. Distributed slack OPF absent from optimize (FAIL A-11). Stochastic crashes on imported networks (PARTIAL A-8). |
| Extensibility | A- | High | All 9 sub-questions PASS across all tiers. Documented linopy extension API. Clean architecture. Minor friction: PTDF bus ordering undocumented, no built-in branch toggle. |
| Scalability | B | Medium | DCPF/DCOPF/PTDF work at 10k. ACPF fails on MEDIUM (data issues). SCUC times out on SMALL with HiGHS. Post-solve SVD hangs at 10k scale. Only HiGHS available in test environment. |
| Workforce Accessibility | B+ | High | Clean core API. Good docs for standard workflows. Silent failure patterns (gencost drop, kwargs swallowing, invalid bus types) are concerning. Import path friction for MATPOWER cases. |
| Maturity & Sustainability | A- | High | 30 releases in 24 months. 327 commits in 12 months. 99+ contributors. Same-day issue resolution. TU Berlin institutional backing + OET commercial entity. Top-3 contributor concentration at 55%. |
| Supply Chain (Gate) | A- | High | MIT license. All deps permissive except Levenshtein (GPL-2.0, replaceable). Full source available. HiGHS (MIT) bundled. Air-gap installable. 248 compiled .so files but all from standard scientific Python stack. **GATE: PASS** |

---

## Per-Criterion Detail

### Criterion 1: Problem Expressiveness

Recommended Grade: **B+**

#### Strengths

- DCPF, ACPF, DC OPF, AC feasibility check, SCUC, SCED, contingency sweep, SCOPF, and lossy OPF all work natively or with minimal stable workarounds on TINY
- SCOPF is a native API (`optimize_security_constrained`) using PTDF-based contingency constraints -- this is the correct preventive formulation used by ISOs
- Lossy OPF with LMP decomposition works via a single `transmission_losses` parameter; LMP decomposition into energy, congestion, and loss components is achievable
- Unit commitment constraints (min up/down time, startup/shutdown costs, ramp limits) are all built-in generator attributes
- Quadratic cost curves supported natively via `marginal_cost_quadratic`

#### Weaknesses

- **Distributed slack OPF (A-11): FAIL** -- `distribute_slack` parameter exists only in `n.pf()`, not `n.optimize()`. The parameter is silently swallowed by `**kwargs` if passed to optimize, producing no error. This is a meaningful gap for Phase 2 ISO congestion pattern reproduction.
- **Stochastic optimization (A-8): PARTIAL** -- Native `set_scenarios()` API exists but crashes on pypower-imported networks due to a MultiIndex bug in `find_bus_controls()`. Only works with networks built via `n.add()`.
- **SCUC on SMALL (A-5): FAIL** -- HiGHS cannot solve the 544-generator, 24-hour MILP within 300s. This is a solver limitation (HiGHS MIP performance) rather than a PyPSA formulation issue, but it limits practical SCUC at scale with the bundled solver.
- **SCED on SMALL (A-6): FAIL** -- Cascading failure from A-5 (Stage 1 SCUC timeout prevents Stage 2 ED).

#### Workarounds Required

| Workaround | Class | Tests Affected | LOC Impact |
|------------|-------|----------------|------------|
| Manual gencost assignment from CaseFrames | Stable | A-3, A-5, A-9, A-10 | +5 lines |
| Manual N-M contingency sweep loop | Stable | A-7 | +120 lines |
| Manual UC/ED two-stage separation | Stable | A-6 | +10 lines |
| Deterministic scenario loop (set_scenarios bug) | Stable (loses joint optimization) | A-8 | +15 lines |

#### Evidence Summary

| Test | Tier | Status | Wall Clock | Notes |
|------|------|--------|------------|-------|
| A-1 DCPF | TINY | PASS | 0.06s | Native `n.lpf()` |
| A-1 DCPF | MEDIUM | PASS | 47.4s | 10k buses, perfect power balance |
| A-2 ACPF | TINY | PASS | 0.09s | Newton-Raphson, flat start converged |
| A-2 ACPF | MEDIUM | PASS | 60.0s | Converged (ambiguous convergence reporting) |
| A-3 DCOPF | TINY | PASS | 0.35s | HiGHS optimal, LMPs extracted |
| A-3 DCOPF | MEDIUM | PASS | 468.0s | 18.6s solver, rest model build + post-processing |
| A-4 AC feasibility | TINY | PASS | 0.42s | 5 voltage violations, 0 thermal |
| A-4 AC feasibility | MEDIUM | PASS | 25.0s | 62 voltage violations, 0 thermal |
| A-5 SCUC | TINY | PASS | 1.46s | 0.097% MIP gap, native UC constraints |
| A-5 SCUC | SMALL | FAIL | 396.9s | HiGHS timeout, no feasible solution |
| A-6 SCED | TINY | PASS | 1.82s | Two-stage UC+ED, ramp constraints binding |
| A-6 SCED | SMALL | FAIL | 0s | Cascading from A-5 SCUC failure |
| A-7 Contingency | TINY | PASS | 48.8s | 617 cases, 96.2% pruning |
| A-7 Contingency | MEDIUM | QUALIFIED PASS | 606.4s | 65 of 12,706 N-1 cases in 10min |
| A-8 Stochastic | TINY | PARTIAL | 0.34s | set_scenarios crashes on imported networks |
| A-8 Stochastic | SMALL | QUALIFIED PASS | 1382.1s | Deterministic loop workaround, solver timeouts |
| A-9 SCOPF | TINY | PASS | 0.46s | Native API, 1.7% cost increase over DCOPF |
| A-9 SCOPF | SMALL | PASS | 131.7s | 100 contingencies, optimal |
| A-10 Lossy OPF | TINY | PASS | 0.72s | Native `transmission_losses`, LMP decomposition |
| A-10 Lossy OPF | SMALL | PASS | 51.5s | 1998/2000 buses with nonzero loss component |
| A-11 Distributed slack | TINY | FAIL | -- | Not in optimize API |
| A-11 Distributed slack | SMALL | FAIL | -- | Same limitation |

#### Grade Rationale

PyPSA passes 9 of 11 formulation types at TINY scale (7 clean PASS + 1 PARTIAL + 1 QUALIFIED PASS for SCOPF), with 1 FAIL (distributed slack) and the stochastic feature partially broken. At SMALL/MEDIUM scale, SCOPF and lossy OPF scale well; SCUC and stochastic hit solver limitations. The rubric defines B as "most types supported, one or two require companion package or workaround." PyPSA exceeds B because SCOPF (the most complex formulation) is natively supported and works at scale, and lossy OPF with LMP decomposition is a single-parameter addition. The distributed slack gap and stochastic bug prevent an A-. B+ is the appropriate grade: strong native coverage with one meaningful gap (distributed slack) and one fragile feature (stochastic on imported networks).

---

### Criterion 2: Extensibility

Recommended Grade: **A-**

#### Strengths

- **Documented extension API**: The `create_model()` / `add_constraints()` / `solve_model()` workflow provides clean algebraic access to the optimization model via linopy. Custom flow gate constraints require only 4-6 lines of constraint code.
- **Graph access**: `n.graph()` returns a standard NetworkX graph. Full NetworkX algorithm library available (BFS, DFS, shortest path, centrality). 5 LOC at all scales.
- **Contingency loop**: `n.lines.active` flag allows branch deactivation without model reconstruction. `n.lpf()` recomputes topology each call. Works at all scales (46 branches TINY, 100 branches MEDIUM).
- **Stochastic wrapping**: Timeseries injection via `n.loads_t.p_set` DataFrame assignment. 50 scenarios x 24 hours works cleanly on TINY and SMALL.
- **Interoperability**: All results are native pandas DataFrames. Export is 4 lines of `.to_csv()`. No custom serialization.
- **PTDF extraction**: Native `sub.calculate_PTDF()` produces numpy array. 12,706 x 10,000 matrix computed in 31.6s on MEDIUM.
- **Reference bus control**: Simple attribute change on `n.generators.control`. LMPs correctly invariant to slack bus choice in lossless DCOPF.
- **Clean architecture**: Five well-separated layers (data model, PF solver, optimization formulation, solver interface, results). linopy provides solver-agnostic algebraic modeling.

#### Weaknesses

- LMP shadow prices not auto-assigned when using the manual `create_model()` / `solve_model()` workflow (must extract duals manually from `n.model.constraints`)
- PTDF bus ordering follows `sub.buses_o`, not `n.buses.index` -- undocumented, causes silent incorrect results if ordering is wrong
- No built-in branch enable/disable flag for contingency analysis (B-3 uses `x=1e10` workaround on TINY, `active` flag on MEDIUM -- inconsistency in test implementations)
- `pypsa.optimization.constraints` module at 2159 lines could benefit from decomposition

#### Workarounds Required

| Workaround | Class | Tests Affected |
|------------|-------|----------------|
| Branch disconnection via `x=1e10` or `active=False` | Stable | B-3 |
| Manual dual extraction for LMPs in custom constraint workflow | Stable | B-1 |
| Zero-impedance transformer fix (`x=1e-4`) on MEDIUM | Stable | B-1, B-7, B-9 |

#### Evidence Summary

| Test | Tier | Status | Key Finding |
|------|------|--------|-------------|
| B-1 Custom constraints | TINY | PASS | 6 LOC for flow gate via linopy |
| B-1 Custom constraints | MEDIUM | PASS | $12,942 cost increase, constraint binding |
| B-2 Graph access | TINY | PASS | NetworkX BFS, 20 buses at depth 3 |
| B-2 Graph access | MEDIUM | PASS | 10k nodes, 12,706 edges, 0.11s |
| B-3 Contingency loop | TINY | PASS | 46 contingencies in 3.17s |
| B-3 Contingency loop | MEDIUM | PASS | 100 contingencies in 1422.7s |
| B-4 Stochastic wrapping | TINY | PASS | 50 scenarios x 24h in 5.9s |
| B-4 Stochastic wrapping | SMALL | PASS | 50 scenarios x 24h in 589.1s |
| B-5 Interoperability | TINY | PASS | 4 LOC, CSV round-trip verified |
| B-5 Interoperability | MEDIUM | PASS | 4 LOC, 279 KB total CSV output |
| B-6 Code architecture | -- | PASS | 5 clean layers, linopy abstraction |
| B-7 AC feasibility ext | TINY | PASS | Same-model DC OPF -> AC PF, 1 violation |
| B-7 AC feasibility ext | MEDIUM | PASS | 62 voltage violations, same-model context |
| B-8 Reference bus config | TINY | PASS | LMPs invariant to slack bus choice |
| B-8 Reference bus config | SMALL | PASS | Same invariance confirmed at 2k buses |
| B-9 PTDF extraction | TINY | PASS | 46x39 matrix, 1.88e-12 MW max error |
| B-9 PTDF extraction | MEDIUM | PASS | 12706x10000 matrix, 969 MB, 31.6s |

#### Grade Rationale

All 9 sub-questions pass at all tested tiers. The extension API is documented, the graph access is native, PTDF is a first-class API, and results interoperability is trivial. The one minor caveat preventing a full A is the undocumented PTDF bus ordering issue (silent incorrect results) and the missing auto-assignment of LMPs in the custom constraint workflow. These are real friction points but do not affect core extensibility workflows. A- is appropriate.

---

### Criterion 3: Scalability

Recommended Grade: **B**

#### Strengths

- DCPF works at 10k buses (34.3s, 2.1 GB) -- `n.lpf()` uses sparse LU decomposition
- DCOPF solves optimally at 10k buses (HiGHS in 15.7s, effective presolve reduces 43k rows to 4.8k)
- PTDF matrix computed at 10k scale (12,706 x 10,000 in 31.6s, 5 GB peak memory)
- Solver interface cleanly abstracted via linopy -- swap is a parameter change, zero reformulation
- HiGHS LP shows 3.6x speedup with 16 threads vs 1 thread on 10k DCOPF
- Memory requirements workstation-tractable: 2-5 GB for 10k-bus DC problems

#### Weaknesses

- **ACPF fails at 10k (C-2: FAIL)**: Newton-Raphson does not converge on MEDIUM with flat start, DC warm start, or relaxed tolerance. Root cause: zero-impedance transformers in ACTIVSg10k create singular admittance matrix.
- **SCUC times out at 2k (C-4: QUALIFIED PASS)**: HiGHS reaches 300s limit on 544-generator 24-hour MILP (39,168 binary variables) without finding a feasible solution. SCIP not available for comparison.
- **Post-solve SVD hangs at 10k**: After HiGHS solves optimally in ~10s, `n.optimize()` enters shadow-price SVD computation consuming 500%+ CPU and 3.7+ GB RAM for >5 minutes. Makes `n.optimize()` impractical above ~5k buses without workaround (`create_model()` + `model.solve()`).
- **SCOPF fails at 10k with 500 contingencies (C-8: FAIL)**: Bridge edges in ACTIVSg10k produce infinite PTDF entries. PyPSA does not auto-filter bridge edges from contingency list.
- **Distributed slack not available in optimize (C-10: FAIL)**: Same limitation as A-11.
- **Only HiGHS available in test environment**: GLPK, SCIP, CBC not installed. Multi-solver comparison could not be completed.
- **Contingency sweep slow at 10k**: ~40s per case for `lpf()` due to full topology re-analysis. Estimated 3.3 hours for 295 cases.
- **Model construction time dominates**: DCOPF on MEDIUM takes 468s total but only 18.6s in solver. The remaining time is model build and post-processing.

#### Evidence Summary

| Test | Status | Wall Clock | Memory | Key Metric |
|------|--------|------------|--------|------------|
| C-1 DCPF MEDIUM | PASS | 34.3s | 2,099 MB | Sparse LU, singular matrix warning |
| C-2 ACPF MEDIUM | FAIL | 138.9s | -- | Non-convergence, zero-impedance branches |
| C-3 DCOPF MEDIUM (HiGHS) | QUALIFIED PASS | 15.7s solver | 2,113 MB | GLPK not installed |
| C-4 SCUC SMALL (HiGHS) | QUALIFIED PASS | 637.0s | 3,654 MB | Timeout, no feasible solution |
| C-5 Contingency MEDIUM | QUALIFIED PASS | ~40s/case | 2,099 MB | 59 of 295 cases in 40 min |
| C-6 Stochastic DCPF SMALL | PASS | 1,247.8s | 112 MB | 50 scenarios, all converged |
| C-7 Solver swap MEDIUM | QUALIFIED PASS | 8.9s solver | 2,880 MB | Only HiGHS available |
| C-8 SCOPF MEDIUM 500 | FAIL | 23.0s | 2,114 MB | PTDF singularity from bridge edges |
| C-9 PTDF MEDIUM | PASS | 31.6s | 4,967 MB | 12706x10000 dense matrix |
| C-10 Distributed slack | FAIL | -- | -- | Not supported in optimize |

#### Grade Rationale

PyPSA demonstrates workable performance at 10k buses for DC problems (PF, OPF, PTDF). However, the combination of ACPF non-convergence, SCUC timeout, SCOPF failure at scale, post-solve SVD hanging, and distributed slack absence represents multiple caveats. The solver swap mechanism is clean but could not be verified with alternative solvers. The rubric defines B as "adequate at 10k with caveats." Three outright FAILs (C-2, C-8, C-10) and three QUALIFIED PASSes (C-3, C-4, C-5) with significant caveats place this squarely at B. The ACPF and SCOPF failures are partially attributable to the ACTIVSg10k data quality (zero-impedance branches), but PyPSA's lack of robust handling for this common MATPOWER pattern is itself a scalability concern.

---

### Criterion 4: Workforce Accessibility

Recommended Grade: **B+**

#### Strengths

- Clean core API: `n.lpf()`, `n.pf()`, `n.optimize()` are intuitive single-call entry points
- Pandas-based data model: all inputs and outputs are DataFrames, familiar to Python analysts
- Getting-started examples work correctly on v1.1.2 (D-3: PASS)
- Good NaN detection: linopy catches NaN costs with a clear `ValueError` (D-4)
- Concise code volume: median 176 LOC across test implementations, minimum 110 LOC for DCPF
- Time to first solve: ~1.25s from import to DCPF result (warm cache)
- Comprehensive documentation for core PF and optimization workflows

#### Weaknesses

- **Silent failure patterns** (D-4):
  - Invalid bus types silently accepted with no validation
  - `n.optimize(distribute_slack=True)` silently ignored via `**kwargs`
  - MIQP with HiGHS returns "unknown" status instead of raising an error
- **Import path friction** (D-1):
  - No native MATPOWER `.m` file reader; requires `matpowercaseframes` intermediary
  - `import_from_pypower_ppc()` silently drops gencost data
  - `import_from_pandapower_net()` crashes on case39 (multi-generator bus bug)
  - 87-package dependency footprint
- **Documentation gaps** (D-2):
  - 5 of 9 A-tests completable from docs alone; 4 require discovery
  - `set_scenarios()` crash on imported networks undocumented
  - `distribute_slack` absence from `optimize()` undocumented
  - HiGHS MIQP limitation not documented in UC section
- **Infeasibility diagnostics**: Solver returns "infeasible" with no identification of which constraint caused the problem
- **Contingency sweep code volume**: A-7 requires 276 LOC (57% above median) due to absent built-in function

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 Install-to-first-solve | QUALIFIED PASS | 1.25s solve time, but import path friction (no native .m reader, gencost dropped) |
| D-2 Documentation audit | QUALIFIED PASS | 5/9 A-tests from docs alone; silent-failure patterns undocumented |
| D-3 Example verification | PASS | Getting-started example produces correct results |
| D-4 Error quality | QUALIFIED PASS | Good NaN detection; poor infeasibility diagnostics; invalid bus types silently accepted |
| D-5 Code volume | INFORMATIONAL | Median 176 LOC; outlier A-7 at 276 LOC |

#### Grade Rationale

The core API is clean and the pandas-based data model is a significant accessibility advantage for Python-literate analysts. Documentation covers standard workflows adequately. However, the silent failure patterns (kwargs swallowing, gencost drop, invalid bus type acceptance) create debugging burden and correctness risks that a power-systems engineer should not have to discover through trial and error. This is above B (rough edges, gaps for advanced use cases) but below A (actionable diagnostics throughout). B+ reflects the clean core API offset by the silent-failure patterns that affect trust.

---

### Criterion 5: Maturity & Sustainability

Recommended Grade: **A-**

#### Strengths

- **Release cadence** (E-1: PASS): ~30 releases in 24 months. v1.0.0 milestone reached October 2025, indicating maturity inflection. Most recent release v1.1.2 on 2026-02-23.
- **Commit activity** (E-2: PASS): 327 commits in 12 months, ~27/month. Daily-level activity with no dormancy gaps.
- **Issue tracker** (E-5: PASS): Median resolution time of 0 days for recent issues. 117 open issues, actively triaged. Maintainers respond same-day.
- **CI and testing** (E-6: PASS): Multi-OS (Ubuntu/macOS/Windows), multi-Python (3.11-3.14) test matrix. Codecov integration. mypy strict mode. Warnings-as-errors policy. Daily cron builds.
- **Operational adoption** (E-7: QUALIFIED PASS): Used by TransnetBW, ENTSO-E, TenneT, IEA, Canada Energy Regulator, Saudi Aramco, Shell, GIZ. 27+ universities. No ISO/RTO real-time operations deployment (expected -- planning tool).

#### Weaknesses

- **Contributor concentration** (E-3: QUALIFIED PASS): Top 3 contributors (fneum, FabianHofmann, nworbmot/Tom Brown) hold 54.9% of commits. All affiliated with TU Berlin. Bus factor effectively 3 with institutional concentration.
- **Funding model** (E-4: QUALIFIED PASS): Grant-dependent (DFG, EU Horizon). OET commercial entity is relatively new. No endowment-style permanent funding. Loss of Tom Brown's group would significantly impact development.

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 Release cadence | PASS | 30 releases / 24 months, v1.0.0 milestone |
| E-2 Commit activity | PASS | 327 commits / 12 months, daily activity |
| E-3 Contributor concentration | QUALIFIED PASS | Top 3 = 55%, all TU Berlin |
| E-4 Funding model | QUALIFIED PASS | DFG + EU grants + OET; grant-dependent |
| E-5 Issue tracker | PASS | 0-day median resolution |
| E-6 CI/test coverage | PASS | Multi-OS, multi-Python, mypy strict, Codecov |
| E-7 Operational adoption | QUALIFIED PASS | TSOs, government agencies, energy companies; no ISO operations |

#### Grade Rationale

PyPSA demonstrates engineering maturity well above typical academic projects: CI discipline, release cadence, issue responsiveness, and breadth of adoption are all strong. The top-3 contributor concentration at TU Berlin and grant-dependent funding are the primary risks. The presence of OET as a commercial entity and 99+ total contributors mitigate but do not eliminate the bus-factor concern. A- reflects excellent maturity metrics with a notable institutional concentration risk.

---

### Criterion 6: Supply Chain (Gate)

Recommended Grade: **A-**

GATE RESULT: **PASS**

#### Strengths

- **Core license** (F-1: PASS): MIT License -- fully permissive, no copyleft obligations
- **linopy** (optimization layer): MIT License
- **HiGHS** (solver): MIT License, bundled in highspy wheel, no commercial solver required
- **Full dependency enumeration** (F-2: PASS): 89 packages in uv.lock, all resolved with SHA256 hashes
- **Code inspectability** (F-5: PASS): Pure Python from PyPSA API through linopy to solver invocation. HiGHS C++ source fully available. No proprietary or obfuscated code anywhere in the chain.
- **Distribution integrity** (F-6: PASS): PyPI + conda-forge, automated release pipeline, hash-verified lock file
- **Air-gap installability** (F-7: PASS): All 89 packages available as pre-built wheels. HiGHS bundled. No runtime internet or license server required.
- **Solver sufficiency** (F-8: PASS): HiGHS handles LP/MIP/QP. No commercial solver needed for any target use case.
- **Getting-started integrity** (F-9: PASS): Version pinning documented, `uv.lock` provides deterministic reproduction.

#### Weaknesses

- **GPL dependency** (F-3: QUALIFIED PASS): `levenshtein` (0.27.3) is GPL-2.0-or-later. It is a direct PyPSA dependency used for fuzzy string matching (component name matching). Replaceable with `rapidfuzz` (MIT) without affecting computational functionality.
- **Compiled extensions** (F-4: QUALIFIED PASS): 248 `.so` files across 25 packages. All from standard scientific Python stack (numpy, scipy, pandas, highspy). All source available. PyPSA itself and linopy are pure Python.

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 Core license | PASS | MIT |
| F-2 Dependency tree | PASS | 89 packages, fully enumerated in uv.lock |
| F-3 License audit | QUALIFIED PASS | 1 GPL dep (levenshtein), replaceable |
| F-4 Compiled extensions | QUALIFIED PASS | 248 .so files, all standard stack, all source available |
| F-5 Code inspectability | PASS | Pure Python through to solver; HiGHS source available |
| F-6 Distribution integrity | PASS | PyPI + automated release + hash verification |
| F-7 Air-gap installability | PASS | All deps as pre-built wheels, no runtime connectivity |
| F-8 Solver sufficiency | PASS | HiGHS (MIT) sufficient for all formulations |
| F-9 Getting-started integrity | PASS | Version pinning documented, uv.lock for reproducibility |

#### Grade Rationale

The supply chain is overwhelmingly clean. MIT-licensed core with MIT-licensed solver. Every line of code from API to solver invocation is inspectable. The single GPL dependency (Levenshtein) is used for non-critical string matching and is trivially replaceable. The 248 compiled extensions are a large count but all come from well-established, widely-audited scientific Python packages. This prevents a full A (the rubric requires "no items needing scrutiny" for A, and the GPL dep plus compiled extension count warrant scrutiny). A- is appropriate: strong supply chain with one manageable GPL issue to document in procurement.

---

## Cross-Cutting Observations

### API Friction Patterns

Four recurring friction patterns emerged across multiple evaluation dimensions:

1. **Silent parameter swallowing**: `n.optimize()` accepts arbitrary `**kwargs` that flow to solver options. Unknown parameters (like `distribute_slack`) are silently ignored by HiGHS with only a log-level warning. This affects A-11, D-4.

2. **Import path data loss**: `import_from_pypower_ppc()` silently drops gencost data, areas, and component status. This affects every OPF test (A-3, A-5, A-6, A-9, A-10) and is the single most common friction point.

3. **Zero-impedance branch handling**: ACTIVSg10k contains transformers with x=0, which PyPSA does not handle gracefully. This causes singular matrices (C-1, C-2, C-9), PTDF overflow (C-8), and requires manual fixes across scalability and extensibility tests.

4. **Post-solve overhead**: `n.optimize()` post-processing (shadow-price SVD) dominates wall-clock time on large networks. The solver itself is fast (8-18s on 10k) but total `optimize()` time exceeds 500s due to model build and post-solve. This is the primary scalability bottleneck.

### Documentation Gaps

| Gap | Affected Tests | Severity |
|-----|---------------|----------|
| gencost silently dropped by pypower import | A-3, A-5, A-6, A-9, A-10 | High -- no warning in docs |
| `distribute_slack` absent from `optimize()` | A-11, C-10 | High -- `**kwargs` masks the gap |
| `set_scenarios()` crash on imported networks | A-8 | High -- undocumented bug |
| PTDF bus ordering (`buses_o` vs `buses_i`) | B-9 | Medium -- silent incorrect results |
| HiGHS MIQP limitation | A-5 | Medium -- silently wrong results |
| SCOPF `branch_outages` format for transformers | A-9 | Low-medium |

### Solver Ecosystem

- Only HiGHS was available in the test environment. GLPK, SCIP, and CBC were not installed.
- HiGHS performs well for LP (15.7s on 10k-bus DCOPF) but struggles with large MILPs (timeout on 544-generator SCUC).
- HiGHS cannot solve MIQP problems (quadratic costs + integer variables) -- silently returns "unknown" status.
- The linopy solver-swap mechanism is confirmed clean: changing `solver_name` parameter only, no reformulation.
- For production deployment, SCIP or a commercial solver would be needed for large-scale SCUC/MILP problems.

---

## Items Requiring Human Spot-Check

1. **A-2 ACPF MEDIUM convergence ambiguity**: Test reports "PASS" but notes PyPSA logged "Power flow did not converge" while voltage magnitudes are populated with reasonable values. A human should verify whether this constitutes actual convergence or a false positive. The C-2 scalability test on the same network reports FAIL. These results may be inconsistent.

2. **A-5/A-6 SMALL FAIL attribution**: The SCUC/SCED failures on SMALL are attributed to HiGHS MIP solver limitations. A human should determine whether this should be attributed to PyPSA (grade impact) or to the solver (environment limitation). Installing SCIP or increasing the time limit would clarify.

3. **GPL Levenshtein dependency**: Legal review should confirm whether the Levenshtein package's GPL-2.0 license creates obligations for government deployment. The package is replaceable with rapidfuzz (MIT) -- confirm this is acceptable.

4. **Post-solve SVD bottleneck**: The observation that `n.optimize()` hangs on the SVD computation at 10k scale is a critical scalability finding. Confirm that the `create_model()` + `model.solve()` workaround produces correct results without LMP assignment.

5. **A-8 TINY PARTIAL vs A-8 SMALL QUALIFIED PASS**: The stochastic test results differ in grading between tiers. TINY is PARTIAL (bug documented), SMALL is QUALIFIED PASS (workaround used). A human should align the grading standard.

6. **B-3 implementation inconsistency**: TINY uses `x=1e10` workaround while MEDIUM uses `active=False` flag. The `active` flag is a documented PyPSA attribute. Confirm which approach is canonical and whether the TINY test should be updated.

---

## Phase 2 Readiness Findings

### P2-1: PSS/E RAW Format Parsing

**Status:** Not supported natively. PyPSA has no `import_from_raw` or `import_from_psse` method. Indirect paths exist through pandapower or MATPOWER converters but have limitations. Phase 2 will require either a custom RAW parser or integration with an existing parser library (e.g., `andes`).

### P2-2: Piecewise-Linear Cost Curves

**Status:** Not in current release (v1.1.2). Active PR #1603 (opened 2026-03-04) adds PWL `marginal_cost` and `capital_cost` using linear tangent constraints. SOS2 fallback is on the TODO list. The existing `marginal_cost_quadratic` attribute provides convex cost curve support as an interim alternative. PWL support will likely land in v1.2.0.

### Additional Phase 2 Considerations

- **Distributed slack gap**: The absence of distributed slack from `n.optimize()` is the most significant Phase 2 blocker for ISO congestion pattern reproduction. The `transmission_losses` parameter partially addresses this (bus-varying LMPs with loss components) but does not replicate the ISO distributed-reference formulation.
- **SCOPF at scale**: Native SCOPF works at SMALL (100 contingencies) but fails at MEDIUM (500 contingencies) due to bridge-edge PTDF singularity. Pre-filtering bridge edges from contingency lists is a necessary production step that PyPSA does not automate.
- **Model construction overhead**: At 10k buses, model build time (400-500s) dwarfs solver time (10-20s). Phase 2 workflows with repeated solves (iterative SCOPF, contingency screening) will need the `create_model()` + `solve()` workflow to avoid rebuilding the model each time.

---

## Methodology Notes

- All tests executed inside the devcontainer (Ubuntu 24.04, Python 3.12, HiGHS 1.13.1 via highspy)
- PyPSA version: 1.1.2, linopy version: 0.6.4
- Network import via matpowercaseframes 2.0.1 + `import_from_pypower_ppc()`
- Reference networks: IEEE 39-bus (TINY), ACTIVSg 2000 (SMALL), ACTIVSg 10000 (MEDIUM)
- Only HiGHS solver available; GLPK, SCIP, CBC not installed in devcontainer
- Solver time limits: 300s for MIP problems, no limit for LP problems
- Memory measured via tracemalloc where available
- Grading applied conservatively: when evidence is ambiguous, the lower grade is recommended with spot-check flag
- All test scripts located under `evaluations/pypsa/tests/` organized by dimension
- Observation files in `evaluations/pypsa/results/observations/` capture cross-cutting patterns
- 10 observation files, 52 test result files, 4 research files read for this synthesis
