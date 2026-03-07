---
test_id: D-5
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-5: Code Volume Comparison

## Objective

Measure lines of code (LOC) for each Suite A test script to quantify the effort
required to implement each power-system analysis in PyPSA.

## LOC by Test

These counts are for the canonical (full-network) test files in
`evaluations/pypsa/tests/expressiveness/`.

| Test | Description | LOC | Complexity |
|------|------------|-----|------------|
| A-1  | DC Power Flow | 158 | Low |
| A-2  | AC Power Flow | 252 | Medium |
| A-3  | DC OPF | 256 | Medium |
| A-4  | AC Feasibility Check | 275 | Medium |
| A-5  | SCUC | 382 | High |
| A-6  | SCED (two-stage) | 426 | High |
| A-7  | Contingency Sweep | 391 | High |
| A-8  | Stochastic Optimization | 485 | High |
| A-9  | Security-Constrained OPF | 282 | Medium |
| A-10 | Lossy DCOPF with LMP | 359 | High |
| A-11 | Distributed Slack OPF | 309 | Medium |
| **Total** | | **3,575** | |

## Observations

1. **Lowest LOC**: A-1 (DCPF) at 158 lines. This is the simplest analysis --
   `n.lpf()` does most of the work.

2. **Highest LOC**: A-8 (Stochastic) at 485 lines. Reflects the complexity of
   setting up multi-scenario data and validating scenario-dependent results.

3. **SCOPF is compact**: A-9 at 282 lines is notably short for a
   security-constrained problem, reflecting that
   `n.optimize.optimize_security_constrained()` encapsulates the complexity.

4. **SCED adds ~44 lines over SCUC**: A-6 (426) vs A-5 (382). The delta comes
   from the manual commitment-fixing workaround (encoding UC status into
   `p_min_pu`/`p_max_pu`).

5. **Test LOC includes**: imports, network construction from MATPOWER data,
   PyPSA model setup, solve invocation, result extraction, and pytest
   assertions. Pure "PyPSA API" lines (excluding test scaffolding and data
   loading) would be substantially lower.

6. **Small-network variants** exist for A-5, A-6, A-9, A-10, A-11 with reduced
   LOC (242-352 lines), used for faster CI runs.

## Notes

LOC counts include all content: comments, docstrings, blank lines, imports, test
assertions, and data-loading boilerplate. They are not a pure measure of "API
calls needed" but rather of total implementation effort including validation.

Cross-tool LOC comparison requires the same measurement methodology applied to
all six tools under evaluation.
