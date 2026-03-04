# PyPSA -- Phase 1 Evaluation Synthesis

## Executive Summary

PyPSA 1.1.2 is a mature, well-architected Python library for power system modeling that excels in problem expressiveness, extensibility, and ecosystem maturity. All three gate tests passed (IEEE 39-bus, ACTIVSg 2k, ACTIVSg 10k ingested with correct component counts). The tool provides native support for DCPF, ACPF, DC OPF, SCUC, contingency analysis, and stochastic optimization, with clean pandas-DataFrame-based output and a well-designed solver abstraction via linopy. Key weaknesses are the MATPOWER import path (silently drops gencost data, pandapower importer crashes), two regression bugs in v1.1.2 power flow code, and open-source MILP solver scalability limits for large SCUC problems. The supply chain is clean (MIT license, Sigstore-attested releases, fully air-gappable) with one low-severity GPL dependency (Levenshtein) that is trivially replaceable.

## Grade Recommendations

| Criterion | Recommended Grade | Confidence | Key Evidence |
|-----------|------------------|------------|--------------|
| Problem Expressiveness | A- | High | 8/8 tests pass (2 qualified); native UC, stochastic, and contingency support; one fragile workaround (A-8 scenario bug) |
| Extensibility | A- | High | 6/6 tests pass; clean extra_functionality callback, native NetworkX graph, pandas output; two regression bugs in contingency path |
| Scalability | B | Medium | DCPF and DC OPF scale to 10k bus; ACPF non-convergent at 10k; SCUC fails at 2k with HiGHS; C-5 is protocol issue |
| Workforce Accessibility | B+ | High | Clean API once loaded; examples work; docs cover ~50% of tests; MATPOWER import friction is significant barrier |
| Maturity & Sustainability | A | High | 31 releases in 24mo; 476 commits, 42 committers; DFG/Breakthrough Energy funding; IEA/ACER/TSO adoption; 84% test coverage |
| Supply Chain (Gate) | A- | High | MIT license; Sigstore attestation; fully air-gappable; one GPL dep (Levenshtein) is isolatable and replaceable |

## Per-Criterion Detail

### Criterion 1: Problem Expressiveness

Recommended Grade: A-

#### Strengths
- Native DCPF via `net.lpf()` with single-call API, no solver needed (A-1)
- Native ACPF via `net.pf()` with Newton-Raphson, converges on flat start for TINY (A-2)
- DC OPF via `net.optimize()` with automatic LMP extraction via `buses_t.marginal_price` (A-3)
- Clean two-stage DC OPF to AC PF workflow on same Network object, no re-import needed (A-4)
- 7 of 8 SCUC constraint types built-in as generator attributes; reserve via documented `extra_functionality` callback (A-5)
- UC/ED separation achievable with public API, commitment matrix as pandas DataFrame (A-6)
- N-M contingency sweep with zero workarounds: native NetworkX graph, in-place branch toggling, connectivity checking (A-7)
- Native stochastic optimization via `set_scenarios()` with probability-weighted objective (A-8)

#### Weaknesses
- MATPOWER gencost data silently dropped on import, requiring manual cost assignment for all OPF tests (A-3, A-4, A-5, A-6, A-8)
- `find_bus_controls()` bug when combining scenarios with pypower-imported networks requires fragile monkey-patch (A-8)
- `get_scenario()` fails with HiGHS pickle error, preventing clean per-scenario extraction (A-8)
- No built-in reserve requirement constraint; must use `extra_functionality` callback (A-5)

#### Workarounds Required
- **Stable (A-3, A-4, A-5, A-6, A-8):** Manual `marginal_cost` assignment from MATPOWER gencost data. Uses documented public API. Present in all OPF tests but is an import-path issue, not an optimization limitation.
- **Fragile (A-8):** Monkey-patching `SubNetwork.find_bus_controls` to no-op for stochastic DC OPF on pypower-imported networks. Safe for DC OPF only; would break AC PF scenarios.

#### Evidence Summary

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 DCPF | TINY | Pass | None | 0.107s | 127 |
| A-2 ACPF | TINY | Pass | None | 0.139s | 199 |
| A-3 DC OPF | TINY | Qualified Pass | Stable (gencost) | 0.437s | 208 |
| A-4 DC OPF+ACPF | TINY | Pass | Stable (gencost) | 0.458s | 222 |
| A-5 SCUC | TINY | Pass | Stable (gencost) | 0.804s | 287 |
| A-6 SCED | TINY | Pass | Stable (gencost) | 1.366s | 295 |
| A-7 N-M Contingency | TINY | Pass | None | 25.8s | 326 |
| A-8 Stochastic OPF | TINY | Qualified Pass | Fragile (monkey-patch) | 0.666s | 275 |

#### Grade Rationale
All 8 expressiveness tests pass, with 6 clean passes and 2 qualified passes. The gencost import gap is a stable, well-understood workaround that affects data loading rather than the optimization API itself. The A-8 fragile workaround is concerning but is specific to the pypower import + scenario interaction, not a fundamental limitation of the stochastic API. The breadth of native support (DCPF, ACPF, OPF, SCUC, contingency, stochastic) with clean APIs warrants an A-, with the minus reflecting the fragile workaround in A-8 and the recurring gencost friction.

### Criterion 2: Extensibility

Recommended Grade: A-

#### Strengths
- `extra_functionality` callback provides documented, first-class custom constraint injection into the linopy model (B-1)
- `net.graph()` returns a native NetworkX MultiGraph with full edge provenance -- zero conversion friction (B-2)
- `net.copy()` provides deep clone for contingency loops without file re-parsing (B-3)
- Time-series interface (`_t` DataFrames) accepts programmatic scenario data directly (B-4)
- All results are native pandas DataFrames -- zero conversion needed for export (B-5)
- Clean 4-layer architecture with mixin-based separation of concerns and internal documentation (B-6)

#### Weaknesses
- `lpf_contingency()` (BODF-based O(1)-per-contingency method) broken in v1.1.2 due to DataFrame/Series regression (B-3, B-6)
- `lpf()` crashes with KeyError on island-causing branch outages when sub-network lacks a branch type (B-3)
- No intermediate result caching in `lpf()` -- each call recomputes topology and B/H matrices (B-6)
- `SubNetwork.lpf()` method mixes injection aggregation, matrix solve, flow computation, and slack adjustment (~120 LOC) (B-6)

#### Workarounds Required
- **Stable (B-3):** Catch `KeyError` for 2 of 46 island-causing contingencies in N-1 loop. Well-understood edge case.

#### Evidence Summary

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1 Flow Gate | TINY | Pass | None | 0.775s | 254 |
| B-2 BFS Graph | TINY | Pass | None | 0.05s | 35 |
| B-3 N-1 DCPF Loop | TINY | Qualified Pass | Stable (KeyError catch) | 3.34s | 65 |
| B-4 50-Scenario DCPF | TINY | Pass | None | 18.02s | 230 |
| B-5 DataFrame Export | TINY | Pass | None | 0.110s | 143 |
| B-6 Code Architecture | N/A | Pass | None | N/A | N/A |

#### Grade Rationale
PyPSA's extensibility story is strong: the `extra_functionality` callback, native NetworkX integration, and pandas-native output model make it straightforward to build custom analysis on top of the tool. The two regression bugs in v1.1.2 (broken `lpf_contingency()`, KeyError on island outages) are concerning but are API-level issues with clear workarounds, not architectural deficiencies. The A- reflects the overall excellent extensibility surface with a deduction for the two regression bugs that affect the built-in contingency analysis path.

### Criterion 3: Scalability

Recommended Grade: B

#### Strengths
- DCPF scales cleanly to 10k bus (6.69s, 2.4 GB memory) (C-1)
- DC OPF converges on 10k bus with both HiGHS and GLPK, identical objectives (C-3)
- Solver swap is a single parameter change, no reformulation needed (C-7)
- 50-scenario stochastic DCPF on 2k bus completes in 45s with consistent per-scenario timing (C-6)
- Three solvers (HiGHS, GLPK, SCIP) produce numerically identical results on 10k-bus DC OPF (C-7)

#### Weaknesses
- ACPF does not converge on 10k bus -- singular Jacobian after 72 iterations; no warm-start or damping options exposed (C-2)
- SCUC fails on 2k bus with HiGHS -- 39k binary variables, root LP relaxation exceeds 600s timeout (C-4)
- DC OPF model construction time dominates solve time (~200s build vs ~2.4s HiGHS solve on 10k bus) (C-3, C-7)
- Peak memory reaches 7.5 GB for 10k-bus DC OPF (C-3)

#### Workarounds Required
- None for scalability tests specifically (C-5 failure is a protocol issue, not a PyPSA issue)

#### Evidence Summary

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| C-1 DCPF | MEDIUM | Pass | None | 6.69s | -- |
| C-2 ACPF | MEDIUM | Qualified Pass | None | 9.74s | -- |
| C-3 DC OPF (HiGHS+GLPK) | MEDIUM | Pass | None | 428.1s | -- |
| C-4 SCUC 24hr | SMALL | Fail | None | 641.4s | -- |
| C-5 N-M Contingency | MEDIUM | Fail (protocol) | N/A | N/A | -- |
| C-6 50-Scenario DCPF | SMALL | Pass | None | 45.4s | -- |
| C-7 Solver Swap | MEDIUM | Pass | None | 812.7s | -- |

#### Grade Rationale
PyPSA handles LP-based problems (DCPF, DC OPF) at 10k-bus scale without difficulty, and the solver abstraction layer works cleanly across three open-source solvers. However, two meaningful gaps prevent a higher grade: (1) the Newton-Raphson ACPF solver lacks convergence aids for large networks, and (2) the open-source HiGHS solver cannot handle 2k-bus 24-hour SCUC within a 10-minute time limit. The C-4 failure is a solver ecosystem constraint (commercial solvers would likely succeed) rather than a PyPSA architectural issue, but it is a practical limitation for the target use case. C-5 is not penalized as it is a protocol parameter issue. The B grade reflects strong LP scalability with meaningful MILP and NLP gaps.

### Criterion 4: Workforce Accessibility

Recommended Grade: B+

#### Strengths
- Core API is minimal and clean: `net.lpf()`, `net.pf()`, `net.optimize()` (D-1)
- All 6 built-in examples run without modification on current release (D-3)
- Version-tagged example downloads ensure examples match installed version (D-3, F-9)
- Infeasible OPF produces clear "infeasible" status; missing costs produces actionable ValueError (D-4)
- Comprehensive example gallery with 30+ notebook examples (D-2)
- Core solve logic is 20-55 lines per test, competitive with other tools (D-5)

#### Weaknesses
- No native MATPOWER `.m` file reader; requires third-party intermediary (`matpowercaseframes`) (D-1)
- `import_from_pandapower_net()` crashes on case39 (multi-generator bus shape mismatch bug) (D-1)
- Pypower importer silently drops gencost data, leading to zero-cost OPF with no error (D-1, D-4)
- Invalid bus type accepted silently -- no enum validation on `control` attribute (D-4)
- ~50% of Suite A tests require source reading or issue searching beyond official docs (D-2)
- No explicit "DC OPF from MATPOWER data" tutorial; import limitations undocumented (D-2)

#### Workarounds Required
- None specific to accessibility tests, but MATPOWER import friction is the primary barrier

#### Evidence Summary

| Test | Network | Status | Key Finding |
|------|---------|--------|-------------|
| D-1 Install-to-Solve | TINY | Qualified Pass | 15-20 min due to import path debugging |
| D-2 Documentation Audit | N/A | Qualified Pass | 4/8 tests completable from docs alone |
| D-3 Example Verification | N/A | Pass | 6/6 examples pass unmodified |
| D-4 Error Quality | TINY | Qualified Pass | 2/3 errors produce clear diagnostics; 1 fails silently |
| D-5 LOC Comparison | N/A | Informational | 86-142 SLOC per test; core logic 20-55 lines |

#### Grade Rationale
PyPSA's core API is well-designed and accessible once the user gets past the data ingestion barrier. The MATPOWER import friction is the dominant accessibility issue -- it adds 15-20 minutes to the first-solve experience and affects documentation coverage for OPF workflows. The silent acceptance of invalid bus types (D-4c) is a data model validation gap. The B+ reflects an overall good API with significant but bounded import-path friction that does not affect users who build networks programmatically (PyPSA's primary workflow).

### Criterion 5: Maturity & Sustainability

Recommended Grade: A

#### Strengths
- 31 releases in 24 months with semantic versioning; v1.0 milestone reached Oct 2025 (E-1)
- 476 commits from 42 unique committers in 12 months (E-2)
- Diversified funding: DFG, Breakthrough Energy, BMWK, Helmholtz; commercial support via OET (E-4)
- Median issue close time 24 days; bugs resolved in hours/days (E-5)
- Cross-platform CI matrix (Linux/macOS/Windows), 84% code coverage, mypy strict mode, CodeQL security scanning (E-6)
- Operational adoption by IEA, ACER, JRC, Austrian Power Grid, TransnetBW, Shell, Saudi Aramco (E-7)
- National models for EU, US, UK, Germany, Poland, and global developing nations (E-7)

#### Weaknesses
- Top 3 contributors account for 46.9% of lifetime commits; bus factor ~3-4 (E-3)
- All top contributors affiliated with TU Berlin -- institutional concentration risk (E-3)
- Two regression bugs shipped in v1.1.2 (B-3 observation) suggest edge-case testing gaps despite 84% coverage

#### Workarounds Required
- None for maturity tests

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 Release Cadence | Pass | 31 releases in 24 months; last release 9 days ago |
| E-2 Commit Activity | Pass | 476 commits, 42 committers in 12 months |
| E-3 Contributor Concentration | Qualified Pass | Top 3 = 46.9%; mitigated by institutional backing |
| E-4 Funding Model | Pass | Multi-source: DFG, Breakthrough Energy, BMWK, OET |
| E-5 Issue Tracker Health | Pass | Median close 24 days; substantive responses |
| E-6 CI/CD & Coverage | Pass | 84% coverage, cross-platform CI, mypy strict, CodeQL |
| E-7 Operational Adoption | Pass | IEA, ACER, 6+ TSOs, Shell, country-level models |

#### Grade Rationale
PyPSA is among the most mature open-source power system modeling tools by every measured dimension: release cadence, contributor breadth, funding diversity, issue tracker health, CI infrastructure, and operational adoption. The contributor concentration (46.9% top 3) is a moderate risk, but it is mitigated by institutional embedding at TU Berlin, multi-source funding, and a growing contributor base. The operational adoption by energy regulators (ACER), the IEA, and multiple TSOs provides strong evidence of production-grade reliability.

### Criterion 6: Supply Chain (Gate)

Recommended Grade: A-

Gate: PASS

#### Strengths
- MIT license on core package; CC-BY-4.0 on documentation (F-1)
- 87 total dependencies, all OSI-approved; `uv.lock` with SHA-256 hashes (F-2)
- Pure Python core with zero compiled extensions; all compiled code in well-known scientific packages (F-4)
- Full DCPF execution path traceable through pure Python to `scipy.sparse.linalg.spsolve` (F-5)
- Sigstore attestation on PyPI releases; dual distribution via PyPI + conda-forge (F-6)
- Core functionality fully air-gappable; runtime network access only for optional example downloads (F-7)
- HiGHS (MIT) bundled as default solver; DCPF requires only scipy (F-8)
- Example networks version-pinned to installed release tag (F-9)

#### Weaknesses
- One direct GPL-2.0-or-later dependency (`Levenshtein` package) used for UX string matching (F-3)
- Google Cloud transitive dependencies (via dask/fsspec) add unnecessary package surface area (F-2)
- `carbon_management()` example fetches from external non-version-pinned URL (F-9)

#### Workarounds Required
- None required for gate pass. GPL dependency is low-severity and replaceable (swap `Levenshtein` for MIT-licensed `RapidFuzz`, which is already a transitive dep).

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 Core License | Pass | MIT -- maximally permissive |
| F-2 Dependency Tree | Informational | 87 packages, max depth 5, uv.lock with hashes |
| F-3 License Audit | Qualified Pass | 1 GPL dep (Levenshtein); all others permissive |
| F-4 Compiled Extensions | Pass | Pure Python core; compiled deps are standard scientific stack |
| F-5 Code Inspectability | Pass | Full DCPF trace is pure Python, no opaque steps |
| F-6 Distribution Integrity | Pass | Sigstore attestation, semver, dual PyPI + conda-forge |
| F-7 Air-Gap Install | Qualified Pass | Core air-gappable; examples module makes optional network requests |
| F-8 Solver Dependency | Pass | HiGHS bundled (MIT); DCPF needs only scipy |
| F-9 Example Integrity | Pass | Version-pinned URLs since v0.35.0 |

#### Grade Rationale
The supply chain is clean and well-managed. The MIT license eliminates copyleft concerns for the core package. The single GPL dependency (Levenshtein) is used only for UX string matching and is trivially replaceable with an MIT-licensed alternative already in the dependency tree. Sigstore attestation, hash-pinned lockfiles, and air-gap-compatible installation provide strong supply chain integrity. The A- reflects the overall excellent supply chain posture with a minor deduction for the GPL dependency that requires awareness (even though it is low-risk and replaceable).

## Cross-Cutting Observations

### API Friction Patterns

The dominant API friction pattern across the evaluation is the **MATPOWER import gap**. PyPSA's pypower importer silently drops gencost data, producing zero-cost generators that lead to meaningless OPF results without any error message. This affected tests A-3, A-4, A-5, A-6, and A-8. The workaround (manually setting `marginal_cost` from `matpowercaseframes` gencost data) is stable and uses documented public API, but it adds ~15 lines of boilerplate to every OPF test and is a significant barrier for new users starting from MATPOWER case files.

A secondary friction point is the `import_from_pandapower_net()` crash on networks with multiple generators sharing a bus (case39 bus 31). This blocks the most obvious import path for MATPOWER data.

Beyond the import path, PyPSA's API is consistently clean: single-call solves (`lpf()`, `pf()`, `optimize()`), DataFrame-based results, and documented extension points (`extra_functionality`, `net.graph()`).

### Documentation Gaps

Documentation covers the core API well but has significant gaps around MATPOWER data ingestion:
- No documentation of `import_from_pypower_ppc()` silently dropping gencost
- No tutorial for "DC OPF from MATPOWER data" workflow
- The `import_from_pandapower_net()` crash is not documented or warned about
- Import/export documentation lists methods but does not document data loss on import

For users who build networks programmatically (PyPSA's primary workflow), documentation is substantially more complete, with dedicated pages for unit commitment, stochastic optimization, contingency analysis, and sector coupling.

### Solver Ecosystem

PyPSA's solver integration via linopy is a strength for LP problems and a limitation for large MILP problems:

- **LP (DCPF, DC OPF):** HiGHS, GLPK, and SCIP all produce identical results with a single-parameter swap. Model construction dominates solve time at scale.
- **MILP (SCUC):** HiGHS cannot solve the 2k-bus, 24-hour SCUC within 600s. The root LP relaxation alone is expensive (134k rows after presolve). Production-scale SCUC would require commercial solvers (Gurobi, CPLEX) or decomposition techniques.
- **NLP (ACPF):** PyPSA's built-in Newton-Raphson solver lacks convergence aids (warm-starting from DCPF, step-size damping) that would help with large networks. The 10k-bus ACPF hit a singular Jacobian.
- **BODF contingency:** The O(1)-per-contingency method (`lpf_contingency()`) is broken in v1.1.2, forcing users to the O(N * solve_cost) loop approach.

### Regression Bugs

Three regression bugs were identified in PyPSA 1.1.2, all in `pypsa/network/power_flow.py`:

1. **`lpf_contingency()` AttributeError** (line 934): `pd.concat` produces DataFrame instead of Series with single snapshot, breaking `.to_frame()` call. Renders the BODF-based contingency method unusable.

2. **`lpf()` KeyError on island-causing outages** (line 1840): Flow DataFrame indexing fails when a sub-network lacks branches of a given passive component type after topology detection.

3. **`find_bus_controls()` KeyError with scenarios** (in `SubNetwork`): After `set_scenarios()`, bus lookup uses non-scenario index against a MultiIndex, failing on pypower-imported networks.

All three bugs appear to be regressions from the component store refactoring in PyPSA 1.x. None are architectural -- all are fixable with 1-2 line patches. They suggest edge-case testing gaps in the v1.1.x release cycle despite 84% overall code coverage.

## Items Requiring Human Spot-Check

- [ ] **GPL dependency (Levenshtein):** Confirm that internal-use-only deployment does not trigger GPL obligations per legal counsel. If redistribution is planned, swap for RapidFuzz (one-line patch).
- [ ] **C-4 SCUC solver limitation:** Verify whether ZGE's target SCUC problem size exceeds HiGHS capabilities. If so, confirm Gurobi/CPLEX license availability and test PyPSA + commercial solver path.
- [ ] **C-2 ACPF non-convergence:** Determine whether ACPF on large networks is a required use case. If so, evaluate PyPSA's NR solver limitations vs. alternatives (e.g., Ipopt via AC OPF path).
- [ ] **A-8 scenario bug:** Test whether the `find_bus_controls` bug affects networks built natively via `net.add()` (not pypower import). If not, the fragile workaround is irrelevant for production use.
- [ ] **Regression bug reporting:** Confirm whether issues have been filed upstream for the three v1.1.2 regression bugs. If not, file them to track resolution timeline.
- [ ] **Model construction overhead:** The 200s+ model build time for 10k-bus DC OPF (C-3, C-7) may be a concern for repeated solves. Investigate whether linopy offers incremental model modification to avoid full reconstruction.

## Methodology Notes

- Scale cap: MEDIUM (all gate tests passed)
- Tool version: PyPSA 1.1.2
- Solver stack: HiGHS (LP/MILP), GLPK (LP), SCIP (MILP), Ipopt (NLP)
- Tests skipped: None
- C-5 attempted but failed due to **protocol parameter issue** (x=5, m=4 produces combinatorially infeasible case counts on 10k-bus networks). This is not a PyPSA limitation -- all tools will face the same issue. The protocol parameters need tier-specific scaling. PyPSA is not penalized for this failure.
- C-4 failed because HiGHS could not solve the 2k-bus SCUC MILP within the 600s time limit. This IS a scalability finding (open-source solver limitation at scale) but is not PyPSA-specific -- it is a solver ecosystem constraint that would affect any tool using HiGHS for large MILP problems.
- Hardware: 128 GB RAM, 16 cores, Ubuntu 24.04 LTS, no GPU
- All tests executed in devcontainer environment
