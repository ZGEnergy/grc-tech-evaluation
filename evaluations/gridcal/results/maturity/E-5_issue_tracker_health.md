---
test_id: E-5
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "530e2bdd"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# E-5: Issue Tracker Health

## Result: INFORMATIONAL

## Finding

The issue tracker shows moderate engagement with a median time-to-close of 135 days. Issues are batch-closed periodically (7 closed on 2026-01-07, 5 closed on 2025-12-10) rather than addressed individually as they arrive. Many closed issues have zero comments, suggesting silent resolution without user communication.

## Evidence

**Sample: 16 closed issues (most recently updated, excluding PRs):**

| Issue | Created | Closed | Days Open | Comments |
|-------|---------|--------|-----------|----------|
| #435 | 2025-09-18 | 2026-01-11 | 115 | 1 |
| #400 | 2025-06-28 | 2026-01-07 | 193 | 2 |
| #411 | 2025-07-17 | 2026-01-07 | 174 | 3 |
| #345 | 2025-03-09 | 2026-01-07 | 304 | 1 |
| #416 | 2025-08-05 | 2026-01-07 | 155 | 1 |
| #417 | 2025-08-05 | 2026-01-07 | 155 | 1 |
| #347 | 2025-03-11 | 2026-01-07 | 302 | 2 |
| #445 | 2025-10-08 | 2025-12-10 | 63 | 0 |
| #444 | 2025-10-08 | 2025-12-10 | 63 | 0 |
| #365 | 2025-04-14 | 2025-12-10 | 240 | 0 |
| #440 | 2025-10-03 | 2025-12-10 | 68 | 0 |
| #439 | 2025-10-03 | 2025-12-10 | 68 | 0 |
| #451 | 2025-10-27 | 2025-10-27 | 0 | 3 |
| #368 | 2025-04-14 | 2025-10-03 | 172 | 3 |
| #448 | 2025-10-08 | 2025-10-22 | 14 | 1 |
| #450 | 2025-10-16 | 2025-10-16 | 0 | 2 |

**Summary statistics:**

| Metric | Value |
|--------|-------|
| Sample size | 16 closed issues |
| Median time-to-close | **135 days** |
| Mean time-to-close | 130 days |
| Fastest close | 0 days (2 issues) |
| Slowest close | 304 days |
| Issues with 0 comments | 5 of 16 (31%) |

**Batch-closing pattern:**
- 2026-01-07: 7 issues closed simultaneously
- 2025-12-10: 5 issues closed simultaneously (all with 0 comments, labeled "Task")
- This periodic triage pattern suggests issues accumulate and are resolved in bulk rather than continuously.

**Open issues (8 sampled, accessed 2026-03-24):**

| Issue | Created | Age (days) | Comments | Title |
|-------|---------|-----------|----------|-------|
| #458 | 2026-02-11 | 41 | 12 | Importing UK DNO CIM Files |
| #459 | 2026-03-02 | 22 | 1 | Consider using lxml for RDF/XML parsing |
| #457 | 2026-02-10 | 42 | 0 | Create ML artifact for load characterisation |
| #453 | 2026-01-13 | 70 | 0 | Update LF Energy Landscape record |
| #436 | 2025-09-19 | 186 | 1 | Adding buses to diagram does not select switches |
| #437 | 2025-09-19 | 186 | 1 | Adding substation to current diagram |
| #337 | 2025-02-17 | 400 | 5 | Issue with reading PSSE transformers |
| #397 | 2025-06-04 | 293 | 2 | OPF not fulfilling constraints |

**Response quality assessment:**
- Issues with substantive maintainer responses: ~60% of issues with comments show technical engagement
- Acknowledged ratio: ~75% of open issues have at least one response
- Issue #458 (CIM import) has 12 comments showing active debugging collaboration
- Issue #397 (OPF constraints) is 293 days old with only 2 comments -- a significant OPF correctness issue that remains unresolved

**Label usage:** Minimal. Only "bug" and "Task" labels observed. No priority classification, milestones, or assignees visible.

**Total issue counts (repo-wide):** 28 open issues, ~460 total lifetime issues.

Sources:
- GitHub API: `repos/SanPen/GridCal/issues?state=closed` and `?state=open` (accessed 2026-03-24)

## Implications

The 135-day median time-to-close is slow relative to the project's rapid release cadence (2+ releases/week), indicating that user-reported issues do not feed directly into the release cycle. The batch-closing pattern and the 31% zero-comment closure rate suggest that fixes may be implemented without issue-tracker communication. The most concerning finding is issue #397 (OPF constraint violations, open 293 days) -- a correctness bug in the core OPF formulation that directly impacts evaluation results (confirmed in A-3 soft constraint findings).

Consumed observations:
- [doc-gaps from A-3](../observations/doc-gaps-expressiveness-A-3_dcopf.md): The soft constraint behavior documented in A-3 is related to the unresolved OPF constraint issue #397.
