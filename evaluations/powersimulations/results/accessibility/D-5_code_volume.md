---
test_id: D-5
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "bfe66395"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

Suite A test scripts for PowerSimulations.jl range from **156 to 646 lines**, with a
median of **332 lines**. The high line counts reflect three structural factors: (1) PSI's
simulation-oriented API requires time series boilerplate even for single-snapshot solves,
(2) several tests required manual JuMP model construction because PSI lacks built-in
formulations (SCOPF, storage, lossy DCOPF, distributed slack), and (3) Julia's verbose
data manipulation patterns (explicit type annotations, multi-line struct construction).

## Evidence

### LOC Table — Suite A Tests

| Test | Description | LOC | Status | Notes |
|------|-------------|-----|--------|-------|
| A-1 | DCPF | 165 | pass | PowerFlows.jl direct solve |
| A-2 | ACPF | 213 | qualified_pass | PowerFlows.jl NR solve |
| A-3 | DCOPF (differentiated costs, 70% derating) | 271 | pass | PSI DecisionModel + cost setup |
| A-4 | AC Feasibility | 326 | pass | DCOPF + ACPF combined workflow |
| A-5 | SCUC (24hr) | 374 | qualified_pass | UC formulation + init bypass |
| A-6 | SCED (fix commitment, ED) | 529 | qualified_pass | Two-stage UC+ED workflow |
| A-9 | SCOPF (N-1 contingencies) | 364 | qualified_pass | Manual contingency constraints |
| A-10 | Lossy DCOPF + LMP decomposition | 339 | fail | Investigation-only (no formulation) |
| A-11 | Distributed Slack OPF | 156 | fail | Investigation-only (no formulation) |
| A-12 | Multi-period DCOPF + Storage | 646 | qualified_pass | Manual BESS via JuMP |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total tests | 10 |
| Total LOC | 3,383 |
| Mean LOC | 338 |
| Median LOC | 332 |
| Min LOC | 156 (A-11, fail — investigation only) |
| Max LOC | 646 (A-12, multi-period + storage) |
| Min LOC (passing test) | 165 (A-1, DCPF) |
| Max LOC (passing test) | 646 (A-12, multi-period + storage) |

### LOC Drivers by Category

**Boilerplate overhead (present in every PSI test):**
- Time series creation and transformation: ~10-15 lines per test
- Template construction with device models: ~8-12 lines per test
- System loading + cost/parameter setup: ~20-40 lines per test
- Result extraction and formatting: ~15-30 lines per test

**Manual JuMP construction (tests lacking built-in formulations):**
- A-9 (SCOPF): ~80 lines for PTDF computation + contingency constraint injection
- A-12 (Storage): ~120 lines for BESS variables, constraints, and nodal injection
- A-6 (SCED): ~100 lines for commitment extraction + ED model construction

**Investigation/diagnostic code (for failed tests):**
- A-10 (Lossy DCOPF): 339 lines of formulation investigation producing no result
- A-11 (Distributed Slack): 156 lines confirming capability absence

### Comparison Notes

The LOC counts reflect the complete test script including:
- Package imports and utility functions
- System loading and modification
- Model construction and solving
- Result extraction and verification
- Formatted output with tables

Comments and blank lines are included in the total line count, consistent with the
`loc` field in each test's result frontmatter.

For context, the simplest possible PSI DCOPF (A-3 equivalent, no cost differentiation
or branch derating) would require approximately:
- 5 lines: package imports
- 1 line: system loading
- 10 lines: time series boilerplate
- 6 lines: template + device models
- 3 lines: build + solve
- 5 lines: result extraction
- **~30 lines minimum** for a bare DCOPF

This 30-line floor compares to ~5-10 lines for an equivalent PyPSA or pandapower DCOPF,
reflecting PSI's simulation-framework overhead for single-snapshot problems.

## Implications

The high code volume is driven by PSI's design as a multi-period simulation framework
rather than a standalone power flow/OPF solver. Single-snapshot problems pay a fixed
overhead of ~30 lines for time series setup and template construction. Tests requiring
capabilities absent from PSI (SCOPF, storage, lossy DCOPF) incur additional overhead
from manual JuMP model construction.

For the evaluation's accessibility criterion, the code volume suggests that PSI is
well-suited for production simulation workflows (where the boilerplate is amortized
across many scenarios) but imposes higher friction for ad-hoc analysis or prototyping
compared to lighter-weight tools.
