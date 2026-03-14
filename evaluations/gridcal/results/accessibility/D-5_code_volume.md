---
test_id: D-5
tool: gridcal
dimension: accessibility
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "2226c4c4"
timestamp: "2026-03-13T18:00:00Z"
---

# D-5: Code Volume

Line counts for each Suite A test script in `evaluations/gridcal/tests/expressiveness/`.
Two metrics reported: total lines and non-blank/non-comment (NBNC) lines.

## Per-Test Line Counts

| Test | File | Total Lines | NBNC Lines |
|------|------|-------------|------------|
| A-1 (DCPF) | test_a1_dcpf.py | 137 | 95 |
| A-2 (ACPF) | test_a2_acpf.py | 198 | 144 |
| A-3 (DCOPF) | test_a3_dcopf.py | 200 | 154 |
| A-4 (AC feasibility) | test_a4_ac_feasibility.py | 225 | 176 |
| A-5 (SCUC) | test_a5_scuc.py | 278 | 203 |
| A-6 (SCED) | test_a6_sced.py | 291 | 226 |
| A-9 (SCOPF) | test_a9_scopf.py | 242 | 185 |
| A-10 (Lossy DCOPF) | test_a10_lossy_dcopf_lmp.py | 265 | 190 |
| A-11 (Distributed slack) | test_a11_distributed_slack_opf.py | 219 | 155 |
| A-12 (Multi-period storage) | test_a12_multiperiod_dcopf_storage.py | 434 | 338 |

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total scripts | 10 |
| Total lines (all scripts) | 2,489 |
| Total NBNC lines | 1,866 |
| Mean NBNC lines per test | 187 |
| Median NBNC lines per test | 183 |
| Min NBNC lines | 95 (A-1, DCPF) |
| Max NBNC lines | 338 (A-12, multi-period storage) |

## Analysis

- **Simple analyses (A-1, A-2)** require 95-144 NBNC lines. These include network
  loading, solver invocation, and result extraction with assertions. The core solve
  pattern is concise (load file, set options, call solver, read results).

- **Standard OPF (A-3)** requires 154 NBNC lines, comparable to PF tests. The API
  pattern is similar: load, configure options, solve, extract.

- **Compound workflows (A-4, A-5, A-6, A-9)** require 176-226 NBNC lines. These
  involve multi-stage operations (DCOPF then ACPF for A-4, UC then ED for A-5/A-6,
  contingency enumeration for A-9). The elevated line count reflects workflow
  orchestration rather than API verbosity.

- **Advanced features (A-10, A-11, A-12)** require 155-338 NBNC lines. A-12 is the
  clear outlier at 338 NBNC lines due to the complexity of multi-period setup (time
  profiles, battery configuration, 24-hour load profile injection, temporal result
  extraction).

- **Profile setup boilerplate** is a recurring contributor to code volume in temporal
  tests (A-5, A-6, A-12). GridCal requires manual unix-timestamp conversion for time
  profiles and explicit profile array construction for each generator/load parameter.
  This adds approximately 20-40 lines per temporal test compared to tools that accept
  datetime objects and DataFrame-based profile assignment.

## Cross-Tool Context

These line counts include test scaffolding (imports, assertions, result printing) in
addition to the GridCal-specific API calls. The NBNC metric provides a better comparison
basis across tools, as it excludes formatting and comments. The median of 183 NBNC lines
per test indicates moderate API verbosity — not excessively boilerplate-heavy, but not
as concise as tools with higher-level convenience APIs (e.g., PyPSA's single-call
`n.optimize()`).
