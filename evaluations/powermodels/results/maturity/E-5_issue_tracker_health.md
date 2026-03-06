---
test_id: E-5
tool: powermodels
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-5: Issue Tracker Health

## Finding

PowerModels.jl has 83 open issues and approximately 130+ closed issues. The median time-to-close for recently closed issues is approximately 194 days (6.5 months), with a wide range from same-day to 8+ years. Issues generally receive acknowledgment, but resolution is slow.

## Evidence

**Open issues**: 83 (as of 2026-03-05)
**Closed issues**: ~130+ (across paginated API results: 34 + 44 + 52 = 130 on first 3 pages)

**Recently closed issues (sample)**:

| Issue | Created | Closed | Days Open |

|-------|---------|--------|-----------|

| #988 (bus type change) | 2025-11-11 | 2026-02-01 | 82 |

| #991 (wrong branch type case118) | 2025-12-03 | 2026-02-01 | 60 |

| #935 (AC powerflow + switches) | 2024-11-28 | 2026-02-01 | 430 |

| #987 (qmax/qmin not respected) | 2025-11-05 | 2026-02-01 | 88 |

| #984 (solve_mn_opf_strg error) | 2025-09-18 | 2025-09-20 | 2 |

Median time-to-close (last 20 closed): ~194 days.

**Open issues of note**:
- #921 "PSSE Raw files Version 34" (opened 2024-07-01, 2 comments) -- PSS/E v34 support requested
- #918 "PSS/E parser transformer angle offset" (opened 2024-06-16, 2 comments)
- #894 "Move data parser to separate package" (opened 2023-11-03, 2 comments)

Most open issues have at least 1-2 comments indicating acknowledgment.

Source: GitHub API `repos/lanl-ansi/PowerModels.jl/issues`

## Implications

The issue tracker is functional but response times are slow. The batch-closure pattern (multiple issues closed on 2026-02-01) suggests periodic triage rather than continuous maintenance. The 83 open issues for a niche research package is a moderate backlog. Many open issues are feature requests or edge cases rather than critical bugs, which is expected.
