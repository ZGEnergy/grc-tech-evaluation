---
test_id: D-2
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# D-2: Documentation Audit — Suite A Completability from Official Docs

## Methodology

For each Suite A test (A-1 through A-11), assessed whether implementation is
completable using only the official MATPOWER documentation: User's Manual (PDF),
Sphinx-based reference manual, MOST User's Manual, and function help text
(`help <function>`). Noted where the evaluator had to read source code, search
GitHub issues, or guess at undocumented behavior.

## Per-Test Assessment

### A-1: DC Power Flow (104 LOC)

| Aspect | Source |
|--------|--------|
| `rundcpf()` API | Manual Ch. 4; `help rundcpf` |
| mpc struct (bus/branch/gen columns) | Manual Appendix B (case format) |
| Result extraction (bus angles, branch flows) | Manual Ch. 4, Table 4-1 |

**Verdict: Fully completable from docs.** Core PF functions are the best-documented
part of MATPOWER. Column indices are documented in `caseformat` and `idx_bus`/
`idx_brch`/`idx_gen` define files.

### A-2: AC Power Flow (150 LOC)

| Aspect | Source |
|--------|--------|
| `runpf()` API | Manual Ch. 4; `help runpf` |
| Voltage magnitudes & angles | Manual Ch. 4 |
| Reactive power output | Manual Ch. 4 |

**Verdict: Fully completable from docs.** Same quality as A-1.

### A-3: DC OPF (143 LOC)

| Aspect | Source |
|--------|--------|
| `rundcopf()` API | Manual Ch. 6; `help rundcopf` |
| LMP extraction (`bus(:, LAM_P)`) | Manual Ch. 6 + `idx_bus` defines |
| Shadow prices on constraints | Manual Ch. 6 |

**Verdict: Fully completable from docs.** OPF output fields well-documented.

### A-4: AC Feasibility / Contingency (201 LOC)

| Aspect | Source |
|--------|--------|
| `runpf()` convergence checking | Manual Ch. 4 (success flag) |
| Branch removal for contingency | Documented pattern: set branch status column to 0 |
| Voltage/flow limit checking | Column indices in `idx_bus`, `idx_brch` |

**Verdict: Fully completable from docs.** Contingency analysis via mpc mutation
is a standard documented pattern.

### A-5: SCUC via MOST (377 LOC)

| Aspect | Source |
|--------|--------|
| MOST basic API | MOST User's Manual (separate PDF) |
| `xGenData` structure (commitment fields) | MOST manual Table 2-2 |
| PWL cost conversion for GLPK | **Not documented** — had to read source of `poly2pwl` |
| GLPK limitation (no MIQP) | **Not documented** — discovered via solver errors |
| UC fields (`CommitKey`, `MinUp`, `MinDown`) | MOST manual, but scattered across sections |

**Verdict: Partially completable.** The MOST manual documents the data structures,
but the critical GLPK/MIQP limitation and required PWL conversion are not mentioned.
Required reading `qps_glpk.m` source and trial-and-error debugging.

### A-6: SCED (387 LOC)

| Aspect | Source |
|--------|--------|
| MOST multi-period dispatch | MOST User's Manual |
| Ramp rate constraints | MOST manual (RampWear fields in xGenData) |
| Load profile setup | MOST manual Table 2-4 |
| Transition probability matrix | MOST manual Section 2.3 |

**Verdict: Mostly completable.** MOST manual covers the API but is dense and
hard to navigate. The example scripts (`most_ex1_ed.m` through `most_ex7_suc.m`)
were more useful than the manual prose.

### A-7: N-1 Contingency Sweep (288 LOC)

| Aspect | Source |
|--------|--------|
| `makePTDF()`, `makeLODF()` | Manual Ch. 9 (sensitivity analysis) |
| Loop-based contingency screening | Standard MATLAB pattern, not MATPOWER-specific |
| Post-contingency flow calculation | `help makeLODF` documents the formula |

**Verdict: Fully completable from docs.** Sensitivity functions are well-documented
with clear mathematical descriptions.

### A-8: Stochastic Timeseries (316 LOC)

| Aspect | Source |
|--------|--------|
| MOST stochastic setup | MOST manual Section 2.3 |
| Scenario probability weighting | MOST manual (transmat field) |
| Wind profile data structure | MOST manual + examples |
| `contab` (contingency table) format | MOST manual Table 2-5, but **format is confusing** |
| Expected dispatch extraction | **Required reading MOST source** — `md.results.ExpectedDispatch` not in manual |

**Verdict: Partially completable.** Basic setup from manual + examples, but
extracting results required reading `most.m` source code to discover the
`results.ExpectedDispatch` field and its indexing.

### A-9: SCOPF (339 LOC)

| Aspect | Source |
|--------|--------|
| MOST contingency-constrained OPF | MOST manual Section 3 |
| Security constraints via `contab` | MOST manual, but **sparse documentation** |
| Contingency definition format | MOST manual Table 2-5 |

**Verdict: Mostly completable.** The contingency table format is documented but
terse. Required cross-referencing examples and manual.

### A-10: Lossy DC OPF / LMP Decomposition (293 LOC)

| Aspect | Source |
|--------|--------|
| `rundcopf()` is lossless | **Not explicitly documented** — absence of loss model undocumented |
| Loss approximation method | **Not documented** — manual approach required |
| LMP decomposition (energy/congestion/loss) | **Not documented** — manual computation from PTDF |
| `makePTDF()` for sensitivity | Manual Ch. 9 |

**Verdict: Not completable from docs alone.** The fundamental gap — that `rundcopf()`
does not support losses — is nowhere stated in the documentation. The evaluator
had to discover this by reading source code and GitHub issues, then implement a
manual workaround using PTDF-based loss approximation.

### A-11: Distributed Slack OPF (324 LOC)

| Aspect | Source |
|--------|--------|
| Distributed slack in OPF | **Documented as absent** via GitHub issues #136, #63, #233 |
| `makePTDF()` distributed slack weights | `help makePTDF` documents the `slack` parameter |
| Manual opt_model construction | **Required reading `opf.m` and `mp.opt_model` source** |
| Shadow price conventions | **Undocumented** |

**Verdict: Not completable from docs alone.** GitHub issues confirm the feature
is absent. The workaround (manual `opt_model` construction) required deep source
code reading. No documentation covers this use case.

## Summary Table

| Test | LOC | Doc Completable | Sources Beyond Docs |
|------|-----|-----------------|---------------------|
| A-1 | 104 | Yes | None |
| A-2 | 150 | Yes | None |
| A-3 | 143 | Yes | None |
| A-4 | 201 | Yes | None |
| A-5 | 377 | Partial | Source code (`qps_glpk.m`, `poly2pwl.m`), trial-and-error |
| A-6 | 387 | Mostly | MOST examples more useful than manual |
| A-7 | 288 | Yes | None |
| A-8 | 316 | Partial | MOST source code for result extraction |
| A-9 | 339 | Mostly | Cross-referencing examples with manual |
| A-10 | 293 | No | Source code, GitHub issues, manual implementation |
| A-11 | 324 | No | GitHub issues, `opf.m` source, `mp.opt_model` internals |

## Key Findings

1. **Core MATPOWER (PF, OPF, sensitivity) is excellently documented.** Tests A-1
   through A-4 and A-7 are fully completable from official docs.

2. **MOST documentation is comprehensive but difficult to navigate.** The MOST
   User's Manual covers the data structures but result extraction is poorly
   documented. Examples are the primary learning resource.

3. **Absence of features is not documented.** The lossy DC OPF gap (A-10) and
   distributed slack limitation (A-11) are not mentioned in the manual. Users
   discover these only through GitHub issues or source reading.

4. **Solver compatibility matrix is missing.** The GLPK/MIQP limitation that
   affects A-5 is not documented anywhere.

5. **6 of 11 tests completable from docs alone; 3 partially; 2 not at all.**
