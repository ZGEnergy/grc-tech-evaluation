---
test_id: D-2
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "ddbe1832"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

7 of 10 Suite A tests are completable from official MATPOWER documentation alone. The remaining 3 require source code reading or external search due to undocumented MOST APIs and the absence of native lossy DC OPF / distributed slack OPF features.

## Evidence

MATPOWER documentation corpus:
- **MATPOWER User's Manual** (PDF, 247 pages) -- covers case format, PF, OPF, custom constraints, user-defined costs, mpoption, all legacy API functions
- **MOST Manual** (PDF) -- covers multi-period scheduling, unit commitment, storage, wind profiles, stochastic scenarios
- **Developer Manual** (Sphinx, markdown) -- covers MP-Core object model, extension API
- **Technical Notes 1-5** (PDFs) -- OPF formulations, derivatives, element framework
- **README.md** -- basic install and quickstart
- **`help` command** -- inline function help available for all public functions

### Per-Test Documentation Assessment

| Test | Description | Completable from Docs? | Source | Notes |
|------|-------------|------------------------|--------|-------|
| A-1 | DCPF | **Yes** (docs alone) | User's Manual Ch 3-4 | `rundcpf(mpc)` is documented with full struct format |
| A-2 | ACPF | **Yes** (docs alone) | User's Manual Ch 3-4 | `runpf(mpc, mpopt)` with NR solver options documented |
| A-3 | DCOPF | **Yes** (docs alone) | User's Manual Ch 6 | `rundcopf(mpc, mpopt)`, gencost format, LMP extraction (LAM_P) all documented |
| A-4 | AC Feasibility | **Yes** (docs alone) | User's Manual Ch 3-4, 6 | Using DC OPF result struct as input to `runpf` is straightforward from docs |
| A-5 | SCUC | **Partial** (docs + source) | MOST Manual Ch 4-5 | MOST SCUC is documented, but the `loadxgendata` table format requires reading source to get column names. `idx_ct` constants documented but mapping load profiles to CT_TLOAD requires studying examples |
| A-6 | SCED | **Yes** (docs alone) | User's Manual Ch 6 | Per-period `rundcopf` with GEN_STATUS=0 for decommitted generators is straightforward |
| A-9 | SCOPF | **Partial** (docs + source) | User's Manual Appendix A.3 | Custom constraints (`mpc.A/l/u`) documented. LODF matrix via `makeLODF` documented. But combining these for SCOPF requires understanding undocumented internal matrix ordering (ext2int, Bf construction) |
| A-10 | Lossy DCOPF + LMP decomposition | **No** (external search needed) | No native support | MATPOWER DC OPF has no built-in loss model. Iterative loss injection approach not in docs. LMP decomposition requires understanding PTDF math not documented in MATPOWER |
| A-11 | Distributed Slack OPF | **Partial** (docs + source) | User's Manual, `help makePTDF` | `makePTDF` accepts a slack distribution vector (documented in `help makePTDF`), but the post-processing approach to compute distributed-slack LMPs is not documented as a workflow |
| A-12 | Multi-period DCOPF + Storage | **Partial** (docs + source) | MOST Manual Ch 5-6 | `addstorage()` API documented in MOST Manual but storage table column names (`sd_table`) require reading source. GLPK solver integration issues not documented |

### Summary Counts

| Category | Count | Tests |
|----------|-------|-------|
| Completable from docs alone | 5 | A-1, A-2, A-3, A-4, A-6 |
| Docs + source reading needed | 4 | A-5, A-9, A-11, A-12 |
| External search required | 1 | A-10 |

### Documentation Strengths

1. **User's Manual is comprehensive for legacy API.** The 247-page PDF covers all core functions, data structures, and options with worked examples.
2. **Column-index documentation is thorough.** `idx_bus.m`, `idx_gen.m`, `idx_brch.m`, `idx_cost.m` define all named constants with descriptions.
3. **`help` function works.** `help runpf`, `help makePTDF`, etc. provide inline documentation for all public functions.
4. **Rich default output.** MATPOWER prints a full system summary by default, making it easy to verify results without knowing the struct layout.

### Documentation Gaps

1. **MOST table format underdocumented.** The `xgd_table`, `sd_table`, and profile struct formats require reading example files and source code to construct. Column name strings must match exactly but are not listed in a single reference.
2. **Internal/external indexing not explained accessibly.** `ext2int()` and `int2ext()` are critical for custom constraint injection but the transformation logic is explained only in the Developer Manual, not the User's Manual.
3. **No lossy DC OPF or LMP decomposition documentation.** A-10 requires building a custom iterative algorithm. This is a formulation gap, not a documentation gap -- but users seeking this capability will find no guidance.
4. **MP-Core (new framework) documentation immature.** The Developer Manual (Sphinx) covers the architecture but lacks worked examples comparable to the legacy manual.

### Consumed Observations

- [convergence-quality: NR residual not in results struct](../observations/convergence-quality-expressiveness-A-2_acpf.md) -- diagnostic data only available via verbose output parsing
- [arch-quality: Dual-framework architecture](../observations/arch-quality-extensibility-B-6_code_architecture.md) -- new users must choose between legacy and MP-Core APIs with different documentation maturity levels

## Implications

MATPOWER's documentation is strong for core power flow and OPF operations (the bread-and-butter use cases). The User's Manual is among the most comprehensive in the evaluation. However, advanced features (MOST scheduling, custom constraints, PTDF-based analysis) require source code reading and example study. The split between legacy and MP-Core documentation creates confusion for new users about which API to learn.
