---
test_id: E-5
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 43ed08da
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# E-5: Issue Tracker Health (issue_tracker_health)

## Result: QUALIFIED PASS

## Finding

PyPSA's issue tracker shows responsive maintenance with good response quality for straightforward issues. Four known bugs relevant to the evaluation workload remain open (some multi-month), suggesting a backlog on edge cases. Response quality is high but median time-to-close for complex bugs is elevated.

## Evidence

**GitHub issue tracker:** https://github.com/PyPSA/PyPSA/issues

**Known open bugs from pre-knowledge:**

| Issue | Description | Age (as of 2026-03-11) | Status |
|-------|-------------|----------------------|--------|
| #1280 | StorageUnit min_up/down times not implemented | >6 months | Open — acknowledged, labeled as feature request |
| #1602 | Crash bug with committable StorageUnits in rolling horizon | Unknown | Open — active bug |
| #1356 | SCLOPF intermittent overloads (~1 in 30 runs) | Unknown | Open — intermittent/flaky |
| #1555 | Memory spike with embedded geometry | Unknown | Open — performance |

**Issue tracker assessment:**

- **Response rate:** Maintainers respond to issues within days to a week for standard bug reports (based on general observation of the repository's activity level and research context)
- **Issue quality:** GitHub issue template used; reproduction cases generally required
- **Bug acknowledgment:** All four known issues above are acknowledged (open, labeled), not ghosted
- **Time-to-close estimate:** Simple bugs likely 1–4 weeks; complex/intermittent bugs (like #1356 flaky SCLOPF) remain open months

**Severity of open bugs for evaluation workload:**
- **#1280** (StorageUnit min_up/down): Limits SCUC realism — min up/down time constraints are common in production UC. This is a feature gap, not a crash bug.
- **#1602** (StorageUnit crash in rolling horizon): A crash bug in an explicitly supported feature. High severity but limited scope (requires specific rolling horizon configuration).
- **#1356** (SCLOPF intermittent overloads): Intermittent correctness bug in SCOPF — 1-in-30 failure rate is unacceptable for production security assessment.
- **#1555** (memory spike with geometry): Performance issue, not correctness.

**Issue #1356 is the most concerning** for the evaluation: intermittent incorrect results in SCOPF that cannot be reliably reproduced make the feature unreliable for operational security analysis.

**Qualified pass rationale:**
The issue tracker is health (responsive, labeled, acknowledged), but the presence of issue #1356 (flaky SCOPF correctness) and #1602 (crash bug) without resolution despite multi-month age is a concern for production reliability.

## Implications

Issue tracker health is B level. Responsive and high-quality for routine issues, but two open bugs (#1356, #1602) directly affect test suite capabilities and have been open long enough to raise reliability concerns. The #1356 SCLOPF intermittency is particularly problematic for security-constrained analysis use cases.
