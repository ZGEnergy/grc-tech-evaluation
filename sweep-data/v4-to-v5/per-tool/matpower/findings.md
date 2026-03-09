# MATPOWER -- Sweep Findings (v4)

## Summary

The MATPOWER v4 evaluation is thorough and well-documented, with 57 tests covering all protocol dimensions. The evaluation quality is high for core PF/OPF tests, with executed code and captured output. Three categories of concern emerged: (1) three scalability tests (C-4, C-6, C-8) report solver capacity failures but actually failed at MOST's loadmd() data ingestion stage, making the failure attribution speculative; (2) the C-10 distributed slack timing is anomalous (66 min for a problem simpler than the 10s single-slack equivalent); (3) several TINY-tier tests lose discriminative value because case39 produces uniform LMPs with no congestion. Two probes are recommended for timing verification and one for claim verification.

## Finding Details

### matpower-F01: C-10 distributed slack scale timing is anomalous (66 min vs expected ~30s)

**Category:** extraordinary_claim | **Severity:** high
**Tests:** C-10

The C-10 result reports that the distributed-slack DC OPF on MEDIUM via manual opt_model construction took 3,969 seconds (~66 minutes), with the MIPS solve alone consuming 3,878 seconds. This is deeply inconsistent with other evidence in the evaluation:

- C-3 solves the single-slack DC OPF on the same network in 9.7s via MIPS.
- The manual opt_model formulation in C-10 has only 1,937 Pg variables and 10,244 flow constraints, which is a *smaller* problem than the full B-theta formulation used by rundcopf (which includes bus angle variables).
- The synthesis estimated "~90-120s" for this test, suggesting the evaluator also expected much faster performance.

The most likely explanation is that the PTDF-based flow constraint matrix (12,706 branches x 1,937 generators) is stored as a dense matrix, causing MIPS to use dense linear algebra instead of sparse factorization. The standard rundcopf uses the sparse B-theta formulation. This 400x slowdown is a formulation artifact, not a meaningful scalability finding.

The synthesis marks C-10 as a "qualified_pass" but the timing undermines the result's credibility. A probe should verify whether the opt_model constraint matrix is sparse and whether MIPS performs comparably on a correctly-formulated problem.

**Cross-tool relevance:** none
**Proposed action:** add_verification -- re-run with sparse constraint matrix or verify matrix sparsity

---

### matpower-F02: C-5 contingency sweep wall-clock dominated by Octave data structure overhead

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** C-5

C-5 reports a total wall-clock of 2,476 seconds (~41 minutes) for the N-M contingency sweep on MEDIUM. However, the breakdown reveals:

- BFS + adjacency construction: ~2,400s (97% of total)
- PTDF + LODF precomputation: 29s
- Actual N-1 through N-4 screening (28,035 cases): 50.4s

The 2,400s adjacency construction time is caused by Octave's `containers.Map` being extremely slow for 10,000-bus networks. This is an Octave interpreter limitation, not a MATPOWER or algorithmic performance issue. The actual contingency screening performance (50s for 28K cases, 1.8ms per case) is strong.

The synthesis marks this as a "qualified_pass" due to the LODF bottleneck, but the qualification conflates Octave overhead with tool capability. The LODF precomputation (6.9s as part of the 29s PTDF+LODF step) is actually fast. A fairer assessment would separate the algorithm's performance from the interpreter's overhead.

**Cross-tool relevance:** none
**Proposed action:** adjust_scoring -- report screening time separately from adjacency construction

---

### matpower-F03: IEEE 39-bus case39 has no effective RATE_A limits, producing uniform LMPs

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-3, A-9, B-8

Multiple tests on TINY produce trivially uniform results because case39's branch thermal limits never bind:

- **A-3 (DC OPF):** All 39 buses show LMP = 13.5169 $/MWh. Shadow prices MU_SF and MU_ST are all zero. The test verifies that MATPOWER can solve a DC OPF, but the uniform LMPs mean it does not verify that locational pricing, congestion shadow prices, or LMP differentiation work correctly.

- **A-9 (SCOPF):** "Base-case dispatch is identical between SCOPF and unconstrained DC OPF." The SCOPF cost differs by only 0.03% and no contingency constraint binds. The test confirms MOST's SCOPF formulation runs, but does not verify that preventive security constraints actually constrain dispatch.

- **B-8 (Reference bus config):** All LMP comparisons across slack configurations are trivially identical because LMPs are uniform. The test cannot verify that reference bus changes affect LMPs.

The evaluator recognized this issue in A-10, where 8 branch limits were explicitly tightened to force congestion (producing LMPs ranging from 9.87 to 32.19 $/MWh). This targeted tightening demonstrates awareness, but the untightened tests lose signal.

This is a cross-tool issue: all tools using case39 for TINY will face the same problem unless the protocol mandates tightened limits.

**Cross-tool relevance:** confirmed
**Proposed action:** redesign_test -- mandate branch limit tightening in case39 for OPF tests, or use a congested variant

---

### matpower-F04: Gate tests are trivially passed for native MATPOWER format

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

MATPOWER loads its own native .m format via `loadcase()`. Gate tests measure whether a tool can ingest the reference networks, but for MATPOWER this tests the tool reading its own data format. Load times (0.016s for TINY, 1.02s for MEDIUM) reflect file parsing speed, not any ingestion challenge. Every other evaluated tool must convert from .m format, making these gate tests an infrastructure friction test for other tools and a trivial pass for MATPOWER.

This is expected behavior and does not indicate an evaluation deficiency, but it means the gate test dimension provides no comparative information for MATPOWER.

**Cross-tool relevance:** confirmed
**Proposed action:** none -- this is inherent to the protocol's choice of .m as reference format

---

### matpower-F05: SCUC produces all-committed schedule, failing to exercise unit commitment cycling

**Category:** missing_verification | **Severity:** medium
**Tests:** A-5, A-6

A-5 augments case39 with UC parameters (PMIN=20% of PMAX, startup costs at 5x PMAX, ramp rates at 30% of PMAX) and runs 24-hour SCUC. The result: all 10 generators remain committed for all 24 hours. No generator is ever de-committed or re-committed.

This means:
- Binary UC variables are never exercised (all remain 1)
- Min up/down time constraints never bind
- Startup/shutdown costs are never incurred
- A-6's ED comparison shows zero dispatch difference (UC = ED when all committed)

The root cause is case39's capacity-to-load ratio: total PMAX is 7,367 MW, peak load is 6,254 MW, and PMIN totals 1,473 MW. With startup costs at 5x PMAX, the optimizer correctly determines that keeping all generators on is cheaper than cycling. The test verifies that MOST's MILP formulation *exists* and solves, but does not verify that UC cycling logic (the core feature being tested) works correctly.

A probe should verify SCUC cycling by using more aggressive parameters (higher PMIN, lower startup costs, or a wider load range) or by reducing generator count.

**Cross-tool relevance:** confirmed -- any tool using case39 with these parameters will show the same behavior
**Proposed action:** redesign_test -- adjust UC parameters to force at least some generators to cycle

---

### matpower-F06: Three scalability failures stem from MOST ext2int bug, not proven solver limits

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** C-4, C-6, C-8

Three scalability tests are recorded as "fail" in the synthesis:

- **C-4 (SCUC on SMALL):** "failed at the loadmd() stage with: 'buses must be numbered consecutively'"
- **C-6 (Stochastic on SMALL):** Same loadmd() error
- **C-8 (SCOPF on MEDIUM):** "did not complete within the 10-minute timeout" (different from C-4/C-6 but same MOST pathway)

For C-4 and C-6, the solver was never invoked. The failure is a MOST data ingestion bug (loadmd() does not handle non-consecutive bus numbering on networks that pass core MATPOWER functions fine). The synthesis correctly identifies this as a MOST limitation and extrapolates that the resulting problem sizes would "likely exceed" solver capacity, but this is conjecture. The distinction matters:

- A loadmd() bug is fixable with ext2int() preprocessing or a MOST patch
- A solver capacity limit is architectural and requires decomposition algorithms

C-8 may have actually hit a timeout during the solve (the result file is less clear), but C-4 and C-6 definitively failed before solving.

**Cross-tool relevance:** none
**Proposed action:** add_verification -- attempt C-4/C-6 with manually renumbered networks to separate the ext2int bug from solver capacity

---

### matpower-F07: Solver swap test only tested 2 of 4 specified solvers

**Category:** test_design_gap | **Severity:** low
**Tests:** C-7

The protocol specifies C-7 should repeat C-3 with "each available open-source solver" including HiGHS, GLPK, SCIP, and Ipopt. The evaluation tested only MIPS (pass, 9.28s) and GLPK (rejected QP). HiGHS was unavailable (requires MEX compilation not done in the test environment). SCIP and Ipopt were not mentioned.

The test demonstrates solver swap *mechanism* (single parameter change), which is the primary thing being evaluated. However, the limited solver coverage means cross-solver objective consistency (a C-3 requirement) was only verified for MIPS vs GLPK (with PWL conversion, in C-3). The evaluation environment's solver availability was a constraint, not an evaluator choice.

**Cross-tool relevance:** likely -- MATPOWER is unique in requiring MEX compilation for additional solvers, but other tools may also lack some protocol-specified solvers
**Proposed action:** add_verification -- document which protocol-specified solvers were available vs tested

---

### matpower-F08: Distributed slack LMP comparison lacks specific numerical values

**Category:** misleading_result | **Severity:** medium
**Tests:** A-11, B-8

A-11 is the central test for distributed slack OPF capability. The result confirms dispatch is identical (correct) but for LMPs states only "differs significantly" without providing the actual distributed-slack LMP values. The table shows:

```
| Bus 1  | 14.01 | differs significantly |
| Bus 31 | 12.40 | differs significantly |
| Bus 39 | 16.53 | differs significantly |
```

The result also notes: "The sign convention in the manual formulation differs from MATPOWER's standard output, but the structural finding is confirmed: slack distribution affects marginal pricing."

This phrasing suggests the evaluator may not have resolved the sign convention issue to produce correctly signed distributed-slack LMPs. The sign convention mismatch between opt_model.get_soln() and MATPOWER's standard output is called out as undocumented. If the LMPs have incorrect signs or are not properly translated, the "differs significantly" claim may be masking an incomplete verification.

**Cross-tool relevance:** none
**Proposed action:** add_verification -- provide actual numerical LMP values for distributed-slack case and verify sign consistency

---

### matpower-F09: A-10 qualified_pass for lossless tool may be generous vs rubric intent

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** A-10

The rubric sub-question 10 asks: "Can the tool solve a DC OPF with loss approximation?" MATPOWER's `rundcopf()` is strictly lossless with no loss option. The evaluator:

1. Performed an exact lossless energy + congestion decomposition (passes)
2. Computed post-hoc loss estimates from branch impedances and flows (informational)
3. Noted the loss values are "NOT part of the optimization and do NOT affect dispatch or pricing"

The qualified_pass with "stable workaround" framing accurately describes what was achieved, but the rubric's intent (loss-inclusive optimization affecting dispatch) was not met. The evaluator documented this clearly, and the rubric note says "any loss method accepted." The loss component is 0.78% of load on TINY -- potentially material on larger networks. The scoring is defensible but worth noting for cross-tool consistency.

**Cross-tool relevance:** confirmed -- the boundary between "loss-inclusive optimization" and "post-hoc loss estimation" applies to all tools
**Proposed action:** adjust_scoring -- clarify rubric on whether post-hoc loss estimation counts as "loss approximation"

---

### matpower-F10: LOC counts include boilerplate and are not normalized across tools

**Category:** test_design_gap | **Severity:** low
**Tests:** D-5

D-5 counts total lines via `wc -l` including comments, blank lines, path setup (~20 lines per script), network loading (~15 lines), and result formatting (~30-50 lines). The file acknowledges this: "Effective 'analysis code' is roughly 60-70% of the total."

Octave scripts inherently include more boilerplate than Python or Julia:
- `addpath()` calls for MATPOWER subdirectories
- `define_constants` for column index names
- `fprintf` for output formatting (no built-in DataFrame display)

This inflates LOC relative to tools with cleaner import/display patterns. D-5 is useful for within-MATPOWER analysis (core vs MOST complexity) but cross-tool LOC comparison requires consistent methodology.

**Cross-tool relevance:** confirmed
**Proposed action:** none -- this is a known limitation of LOC as a metric

---

### matpower-F11: Peak memory measurements are estimates or null for most scalability tests

**Category:** missing_verification | **Severity:** low
**Tests:** C-1, C-2, C-3, C-9, C-10

The protocol requires peak memory recording for all C-tests. Octave lacks built-in memory profiling tools comparable to Python's `tracemalloc` or Julia's `@allocated`. Results:

- C-1: "~4.2 MB" (estimated from matrix dimensions)
- C-2, C-3, C-7: null
- C-5: "2,500 MB" (estimated)
- C-9: "1,017 MB" (likely computed from PTDF matrix size: 12706 x 10000 x 8 bytes)
- C-10: "1,200 MB" (estimated)

These are order-of-magnitude estimates, not actual process memory measurements. This is an Octave ecosystem limitation affecting all Octave-based tools.

**Cross-tool relevance:** likely -- other tools may have better memory profiling
**Proposed action:** none -- acknowledge as Octave limitation

---

### matpower-F12: Interoperability test is trivially passed by all matrix-based tools

**Category:** low_signal | **Severity:** low
**Tests:** B-5

B-5 tests CSV export. MATPOWER results are plain numeric matrices, so export requires only fprintf with column headers (18 LOC). The pass condition is "fewer than 5 lines of code beyond the solve." While Octave requires slightly more code than a Python tool with native DataFrame.to_csv(), this test has minimal discriminative value. Any tool that stores results in structured form will trivially pass.

**Cross-tool relevance:** confirmed
**Proposed action:** none

---

### matpower-F13: Stochastic test used only 3 scenarios with narrow load variation due to solver limits

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-8

The A-8 stochastic optimization test used only 3 scenarios with +/-3% load variation. The result notes: "The built-in MIPS solver struggles with larger load variation (+/-10%) on the 39-bus network combined with stochastic wind. Reducing to +/-3% load variation resolved convergence."

With +/-3% uncertainty, the three scenarios produce LMPs within a narrow band (3.05-7.05 $/MWh range at peak hour). This may not sufficiently stress the cross-scenario coupling that distinguishes genuine stochastic optimization from three near-identical deterministic solves. The protocol does not specify minimum variation or scenario counts for TINY, so this technically passes. However, it weakens the evidence that MOST's stochastic formulation handles meaningful uncertainty.

The 20-scenario wrapping test (B-4) used the same +/-3% load variation but with +/-8% peaker capacity variation, providing somewhat wider uncertainty bands.

**Cross-tool relevance:** likely -- tools with weaker solvers may face similar constraints
**Proposed action:** none -- protocol could specify minimum variation for future versions

---

### matpower-F14: Ramp rate utilization is suspiciously uniform across all generators

**Category:** missing_verification | **Severity:** low
**Tests:** A-6

All 10 generators in A-6 show exactly 26.7% ramp utilization (max delta / ramp limit). This uniformity across generators with PMAX ranging from 508 to 1,100 MW is a consequence of: (1) no congestion (uniform LMPs), (2) polynomial costs with similar quadratic coefficients, and (3) equal per-unit ramp limits (30% of PMAX). When all generators face the same marginal cost curve shape and no flow constraints bind, they all ramp proportionally.

While not incorrect, this means the ED ramp constraints were never binding or even close to binding (26.7% utilization). The test verifies ramp constraints exist in the formulation but does not verify they would correctly constrain dispatch when binding.

**Cross-tool relevance:** confirmed
**Proposed action:** none -- could be strengthened by setting tighter ramp limits on a subset of generators

---

## Extraordinary Claims

### C-10: Distributed slack DC OPF on MEDIUM takes 66 minutes via opt_model/MIPS

**Concern:** The single-slack DC OPF on the same network solves in 9.7s via MIPS. The manual opt_model formulation has fewer decision variables (1,937 Pg variables vs the full bus-angle formulation). A 400x slowdown for a simpler problem strongly suggests either: (a) the PTDF-based constraint matrix is stored as dense, causing MIPS to use dense O(n^3) factorization instead of sparse, or (b) the quadratic cost matrix is incorrectly structured, or (c) an opt_model configuration issue. The synthesis estimated "~90-120s" based on component measurements, indicating the actual run surprised the evaluator as well.

**Evidence quality:** moderate -- the timing is from an actual run, but the explanation is speculative

A probe should: (1) check whether the flow constraint matrix `H_dist * Cg` is stored as sparse, (2) if dense, convert to sparse and re-time, (3) compare MIPS iteration count between C-10 and C-3.

---

### C-5: Contingency sweep on MEDIUM takes 41 minutes

**Concern:** The 2,476s total is 97% Octave containers.Map overhead for adjacency construction and only 50s for the actual LODF-based screening. The synthesis reports the total as the test result and assigns a "qualified_pass" based partly on this timing. The actual screening performance (28,035 cases in 50s) is strong and would merit a clean pass if separated from the interpreter overhead.

**Evidence quality:** strong -- the breakdown is clearly reported in the result file

A probe should verify whether a simpler adjacency construction method (e.g., direct sparse matrix instead of containers.Map) reduces the overhead to a few seconds.

---

### C-4: SCUC on SMALL fails due to solver capacity limits

**Concern:** The test failed at `loadmd()` with a bus numbering error, not at the solver. The claim that the resulting MILP "would likely exceed GLPK's capacity" is an extrapolation based on problem size estimates (200K+ variables). While this extrapolation is reasonable, it is not verified. The ext2int bug in loadmd() is a known issue (GitHub #127) that could be fixed.

**Evidence quality:** weak -- the solver was never invoked; the capacity claim is extrapolated

A probe should: manually renumber the ACTIVSg 2000 buses to consecutive ordering, run loadmd(), and attempt the SCUC solve with a generous timeout to determine actual solver behavior.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | -- | Trivial for native format |
| G-2 | pass | -- | Trivial for native format |
| G-3 | pass | -- | 19.4% zero RATE_A branches noted |
| A-1 | pass | -- | -- |
| A-2 | pass | -- | -- |
| A-3 | pass | -- | Uniform LMPs, no congestion |
| A-4 | pass | -- | -- |
| A-5 | pass | stable (PWL for GLPK) | All gens committed, no UC cycling |
| A-6 | pass | stable (PWL for GLPK) | UC=ED, uniform ramp utilization |
| A-7 | pass | -- | -- |
| A-8 | pass | -- | Only 3 scenarios, +/-3% variation |
| A-9 | pass | -- | SCOPF dispatch identical to base OPF |
| A-10 | qualified_pass | stable (post-hoc loss) | No native lossy DC OPF |
| A-11 | qualified_pass | stable (manual opt_model) | LMP values not fully reported |
| B-1 | pass | -- | -- |
| B-2 | pass | stable (manual BFS) | -- |
| B-3 | pass | -- | -- |
| B-4 | pass | -- | -- |
| B-5 | pass | -- | Low discriminative value |
| B-6 | informational | -- | -- |
| B-7 | pass | -- | -- |
| B-8 | qualified_pass | stable (distributed slack) | LMP comparison trivial (uniform) |
| B-9 | pass | -- | -- |
| C-1 | pass | -- | Memory estimated, not measured |
| C-2 | pass | -- | Memory null |
| C-3 | pass | -- | -- |
| C-4 | fail | -- | loadmd() bug, not solver |
| C-5 | pass | stable (ext2int) | 97% time is Octave overhead |
| C-6 | fail | -- | loadmd() bug, not solver |
| C-7 | pass | -- | Only 2 of 4 solvers tested |
| C-8 | fail | -- | Timeout (likely solver, possibly loadmd) |
| C-9 | pass | stable (ext2int) | -- |
| C-10 | qualified_pass | stable (manual opt_model) | 66 min timing anomaly |
| D-1 | informational | -- | -- |
| D-2 | informational | -- | 6/11 from docs, 2 not completable |
| D-3 | informational | -- | 13/20 examples pass (65%) |
| D-4 | informational | -- | Mixed quality (2/10 to 9/10) |
| D-5 | informational | -- | LOC includes boilerplate |
| E-1 | informational | -- | 2 releases in 24 months |
| E-2 | informational | -- | 93% single developer |
| E-3 | informational | -- | Bus factor 1 (98.5%) |
| E-4 | informational | -- | Unfunded since mid-2024 |
| E-5 | informational | -- | Median close 108 days |
| E-6 | informational | -- | 462 test files, no coverage metric |
| E-7 | informational | -- | Zero production deployment |
| F-1 | pass | -- | BSD-3, case file carve-out |
| F-2 | pass | -- | Zero external deps |
| F-3 | pass | -- | All BSD-3 |
| F-4 | pass | -- | Zero compiled extensions |
| F-5 | pass | -- | Full path inspectable |
| F-6 | informational | -- | No checksums/signatures |
| F-7 | pass | -- | Fully air-gap compatible |
| F-8 | pass | -- | All on open-source solvers |
| F-9 | informational | -- | Docs bundled in release |
| P2-1 | informational | -- | Native PSS/E RAW support |
| P2-2 | informational | -- | Native PWL cost curves |
| P2-3 | informational | -- | Full pipeline demonstrated |
