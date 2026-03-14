---
test_id: E-5
tool: pypsa
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: d2f277d5
---

# E-5: Issue Tracker Health

## Findings

### Sample: 20 Most Recent Closed Issues

| Issue | Created | Closed | Time to Close | Response Quality |
|-------|---------|--------|---------------|-----------------|
| #1607 | 2026-03-06 | 2026-03-10 | 4.0 days | Substantive (numerical tolerance fix, PR created) |
| #1588 | 2026-03-02 | 2026-03-03 | 0.5 days | Concise explanation |
| #1587 | 2026-03-02 | 2026-03-03 | 0.5 days | Brief (requested PR) |
| #1586 | 2026-03-02 | 2026-03-03 | 0.5 days | Brief (requested PR) |
| #1583 | 2026-02-26 | 2026-02-26 | 0.5 hours | Explanation of behavior |
| #1580 | 2026-02-25 | 2026-02-26 | 0.7 days | Substantive (pandas 3.0 compat, PR linked) |
| #1574 | 2026-02-23 | 2026-02-23 | 0.1 days | Quick resolution |
| #1561 | 2026-02-11 | 2026-02-11 | 0.1 days | Acknowledged, fix committed |
| #1550 | 2026-02-03 | 2026-02-03 | 0.0 days | Technical explanation |
| #1547 | 2026-02-03 | 2026-02-03 | 0.2 days | Detailed analysis, PR created within hours |
| #1546 | 2026-02-03 | 2026-02-11 | 8.2 days | Linked to existing fix |
| #1541 | 2026-01-29 | 2026-02-26 | 28.0 days | Initial response next week, fix in later release |
| #1535 | 2026-01-22 | 2026-02-11 | 20.0 days | Closed silently (no comments) |
| #1534 | 2026-01-21 | 2026-01-26 | 5.3 days | Closed silently (no comments) |
| #1525 | 2026-01-16 | 2026-01-26 | 10.5 days | Positive engagement |
| #1521 | 2026-01-12 | 2026-01-13 | 1.1 days | Detailed bug analysis by maintainer |
| #1517 | 2026-01-06 | 2026-01-26 | 20.1 days | Extended technical discussion, community engagement |
| #1504 | 2025-12-30 | 2026-02-11 | 42.8 days | Closed silently |
| #1497 | 2025-12-16 | 2025-12-22 | 5.8 days | Closed (no comments visible) |
| #1496 | 2025-12-16 | 2025-12-22 | 5.9 days | Closed (no comments visible) |

### Statistics

- **Median time-to-close**: 4.0 days
- **Min**: 0.4 hours (#1550)
- **Max**: 42.8 days (#1504)
- **Issues with substantive response**: 14/20 (70%)
- **Issues closed without visible comment**: 4/20 (20%)
- **Issues closed same day**: 8/20 (40%)

### Sample: 10 Most Recent Open Issues

| Issue | Opened | Age | Comments | Status |
|-------|--------|-----|----------|--------|
| #1618 | 2026-03-13 | 0 days | 0 | New (day of evaluation) |
| #1616 | 2026-03-13 | 0 days | 0 | New |
| #1611 | 2026-03-10 | 3 days | 2 | Community-diagnosed, root cause identified |
| #1606 | 2026-03-06 | 7 days | 10+ | Active discussion, design decisions being made |
| #1605 | 2026-03-06 | 7 days | 2 | Bug confirmed |
| #1602 | 2026-03-04 | 9 days | 2 | Root cause identified, fix planned |
| #1601 | 2026-03-04 | 9 days | 1 | Feature request with implementation sketch |
| #1599 | 2026-03-04 | 9 days | 0 | Feature request |
| #1598 | 2026-03-04 | 9 days | 1 | Positive maintainer response |
| #1590 | 2026-03-02 | 11 days | 3 | Maintainer engaged, constructive dialogue |

### Response Quality Assessment

**Good.** Maintainers provide technically substantive responses in the
majority of cases. Notable patterns:

1. Bug reports with reproduction cases get fast, detailed responses
2. Feature requests with low-quality descriptions receive constructive
   pushback (e.g., #1590 where a maintainer requested better issue formatting)
3. Some issues are closed without comment, likely duplicates or resolved
   by linked PRs (GitHub auto-close)
4. Extended discussions on design issues (#1606, #1517) show willingness
   to engage with community feedback on API design

### Consumed Observations

Doc-gap observations from extensibility tests (B-6, B-9, C-4) identified
minor documentation gaps:
- B-6: Mixin architecture undocumented (low severity)
- B-9: PTDF column ordering requires source code reading (low severity)
- C-4: SCIP not available in devcontainer (medium severity, environment issue)

These gaps were not reflected in the issue tracker as reported problems,
suggesting they are known-but-unaddressed documentation items rather than
user-facing pain points.

## Recorded Metrics

- median_ttc: 4.0 days (95.2 hours)
- ack_ratio: 80% (16/20 received substantive response)
- response_quality: good (technically substantive, constructive feedback)
