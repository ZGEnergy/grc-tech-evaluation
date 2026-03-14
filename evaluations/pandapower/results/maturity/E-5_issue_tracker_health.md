---
test_id: E-5
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "b28f55d5"
---

# E-5: Issue Tracker Health — pandapower

## Sub-criterion
5a (Demonstrated Maturity)

## Method
Sampled 20 recently closed issues and 14 open issues from the GitHub issue tracker
(e2nIEE/pandapower). Excluded pull requests. Computed time-to-close, acknowledgment ratio,
and response quality metrics.

## Closed Issues Sample (20 issues)

| # | Created | Closed | Days to Close | Comments |
|---|---------|--------|--------------|----------|
| 2887 | 2026-02-18 | 2026-02-25 | 7 | 2 |
| 2870 | 2026-02-02 | 2026-02-06 | 4 | 2 |
| 2857 | 2026-01-23 | 2026-02-02 | 10 | 1 |
| 2850 | 2026-01-16 | 2026-01-20 | 4 | 1 |
| 2849 | 2026-01-14 | 2026-01-28 | 14 | 2 |
| 2845 | 2026-01-12 | 2026-01-28 | 16 | 1 |
| 2839 | 2025-12-23 | 2026-01-02 | 10 | 3 |
| 2832 | 2025-12-10 | 2025-12-16 | 6 | 1 |
| 2831 | 2025-12-09 | 2025-12-16 | 7 | 1 |
| 2829 | 2025-12-05 | 2026-03-09 | 94 | 2 |
| 2828 | 2025-12-05 | 2025-12-08 | 3 | 4 |
| 2812 | 2025-11-25 | 2026-01-06 | 42 | 2 |
| 2800 | 2025-11-17 | 2026-03-04 | 107 | 3 |
| 2796 | 2025-11-11 | 2026-01-20 | 70 | 1 |
| 2767 | 2025-10-21 | 2025-12-08 | 48 | 4 |
| 2697 | 2025-08-17 | 2025-12-08 | 113 | 4 |
| 2662 | 2025-07-11 | 2026-01-05 | 178 | 4 |
| 2630 | 2025-06-04 | 2026-03-09 | 278 | 1 |
| 2552 | 2025-03-11 | 2026-03-09 | 364 | 5 |
| 926 | 2020-09-14 | 2025-12-08 | 1,911 | 4 |

### Closed Issue Statistics

- **Median time-to-close:** 29 days
- **P25 time-to-close:** 6 days
- **P75 time-to-close:** 110 days
- **Minimum:** 3 days
- **Maximum:** 1,911 days (issue #926, opened in 2020, closed in batch cleanup Dec 2025)
- **Acknowledged ratio:** 20/20 (100%) — all issues received at least one comment

Excluding the outlier (issue #926, 5+ years old), the median drops to approximately 16 days.

## Open Issues Sample (14 issues)

| # | Created | Days Open | Comments | Title |
|---|---------|----------|----------|-------|
| 2916 | 2026-03-13 | 0 | 0 | simbench affect on actions |
| 2910 | 2026-03-10 | 3 | 0 | lightsim2grid issue with case14 |
| 2908 | 2026-03-09 | 4 | 0 | Sincal to pandapower converter update |
| 2886 | 2026-02-18 | 23 | 0 | create_transformers value init not working |
| 2868 | 2026-02-01 | 40 | 1 | Tutorial Tests on Python 3.13/3.14 |
| 2867 | 2026-02-01 | 40 | 14 | unreliable test_cigre_with_bad_data |
| 2861 | 2026-01-24 | 48 | 1 | Add support for Pandas 3.0 |
| 2847 | 2026-01-12 | 60 | 0 | Trafo docs equations wrong |
| 2750 | 2025-10-15 | 149 | 2 | tolerance_mva as PU question |
| 2733 | 2025-09-30 | 164 | 2 | Missing plots in tutorial |
| 2716 | 2025-09-18 | 176 | 12 | Bidirectional DC lines |
| 2715 | 2025-09-18 | 176 | 7 | Parallel contingency analysis |
| 2676 | 2025-07-19 | 237 | 1 | init_time_steps bug |
| 2646 | 2025-06-25 | 261 | 1 | NaN values single-phase short circuit |

### Open Issue Observations

- **Total open issues:** 157 (repo-wide)
- **Recent issues (< 30 days):** Several have 0 comments, indicating initial triage delay
- **Feature requests** (#2715, #2908) remain open and under discussion
- **Bug reports** receive responses but may remain open for extended periods while awaiting
  a fix in a future release
- **Documentation issues** (#2847, #2733) tend to receive less priority

## Response Quality

- Issues receive substantive responses rather than bot-generated templates
- Bug reports typically receive diagnosis comments from core developers
- Labels (bug, enhancement, maintenance, help wanted) are actively applied
- Batch closures occur during release cycles (e.g., multiple issues closed on 2025-12-08
  and 2026-03-09, coinciding with releases)

## Analysis

- **100% acknowledgment rate** on closed issues is strong.
- **Median time-to-close of 29 days** (16 days excluding the 2020 outlier) is reasonable
  for a research-driven project without dedicated support staff.
- **Open issue count of 157** is moderate for a project of this size and age (9 years).
- **Triage lag:** Some recent open issues (2-4 weeks old) have zero comments, suggesting
  the team triages in batches rather than continuously. This is consistent with an
  academic-affiliated team operating on research schedules rather than commercial SLAs.
- **Long-tail issues:** Some issues remain open for 6+ months, typically feature requests
  or edge-case bugs that are not on the critical path. This is normal for volunteer-maintained
  open-source projects.

## Assessment

Healthy issue tracker with 100% acknowledgment, reasonable median resolution time, and
substantive (not template-driven) responses. Primary weakness is batch-style triage with
multi-week gaps for initial response on some issues. Overall consistent with an actively
maintained academic open-source project.
