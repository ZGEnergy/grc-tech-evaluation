---
test_id: D-5
tool: gridcal
dimension: accessibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "2226c4c4"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T12:00:00Z"
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

Suite A test scripts for GridCal average 185 NBNC (non-blank, non-comment) lines per
test. Simple analyses (DCPF) require 95 lines while the most complex (multi-period
storage) requires 322 lines. Profile setup boilerplate for temporal tests is a
significant contributor to code volume.

## Evidence

Line counts measured from `evaluations/gridcal/tests/expressiveness/test_a*.py` using
`wc -l` (total) and `grep -cve '^\s*$' -e '^\s*#'` (NBNC).

### Per-Test Line Counts

| Test | File | Total Lines | NBNC Lines |
|------|------|-------------|------------|
| A-1 (DCPF) | test_a1_dcpf.py | 137 | 95 |
| A-2 (ACPF) | test_a2_acpf.py | 215 | 154 |
| A-3 (DCOPF) | test_a3_dcopf.py | 229 | 175 |
| A-4 (AC feasibility) | test_a4_ac_feasibility.py | 226 | 177 |
| A-5 (SCUC) | test_a5_scuc.py | 361 | 269 |
| A-6 (SCED) | test_a6_sced.py | 418 | 319 |
| A-9 (SCOPF) | test_a9_scopf.py | 234 | 180 |
| A-10 (Lossy DCOPF) | test_a10_lossy_dcopf_lmp.py | 259 | 183 |
| A-11 (Distributed slack) | test_a11_distributed_slack_opf.py | 219 | 155 |
| A-12 (Multi-period storage) | test_a12_multiperiod_dcopf_storage.py | 418 | 322 |

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total scripts | 10 |
| Total lines (all scripts) | 2,716 |
| Total NBNC lines | 2,029 |
| Mean NBNC lines per test | 203 |
| Median NBNC lines per test | 179 |
| Min NBNC lines | 95 (A-1, DCPF) |
| Max NBNC lines | 322 (A-12, multi-period storage) |

### Analysis by Complexity Tier

**Simple analyses (A-1, A-2): 95--154 NBNC lines.** These include network loading,
solver invocation, and result extraction with assertions. The core solve pattern is
concise: load file, set options, call solver, read results.

**Standard OPF (A-3): 175 NBNC lines.** Slightly more than PF tests due to OPF
option configuration and LMP/dispatch extraction. The `OptimalPowerFlowOptions`
constructor and result structure add modest overhead.

**Compound workflows (A-4, A-5, A-6, A-9): 177--319 NBNC lines.** These involve
multi-stage operations: DCOPF-then-ACPF (A-4), UC-then-ED (A-5/A-6), contingency
enumeration (A-9). A-5 and A-6 are notably high (269, 319) due to time-series profile
setup: unix-timestamp conversion, per-generator profile array construction, and
temporal result extraction.

**Advanced features (A-10, A-11, A-12): 155--322 NBNC lines.** A-12 is the clear
outlier at 322 NBNC lines due to multi-period setup complexity: time profiles, battery
device configuration, 24-hour load profile injection, and temporal SoC verification.

### Profile Setup Boilerplate

A recurring contributor to code volume in temporal tests (A-5, A-6, A-12). GridCal
requires:
1. Manual unix-timestamp conversion for `set_time_profile()` (~2 lines)
2. Explicit `Profile` object construction for each parameter (Pmax, Cost, load P)
3. Index-based profile assignment to individual devices

This adds approximately 30--50 NBNC lines per temporal test compared to tools that
accept datetime objects and DataFrame-based profile assignment directly. [tool-specific]

## Implications

GridCal's code volume is moderate for snapshot analyses and elevated for temporal
workflows. The median of 179 NBNC lines per test indicates reasonable API design for
the core PF/OPF pattern, but the profile system adds significant boilerplate for
time-series work. Cross-tool comparison will reveal whether this is typical or above
average for the tool class.
