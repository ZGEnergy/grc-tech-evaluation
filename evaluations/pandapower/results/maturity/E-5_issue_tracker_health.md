---
test_id: E-5
tool: pandapower
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: b28f55d5
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
timestamp: "2026-03-24T00:00:00Z"
---

# E-5: Issue Tracker Health

## Result: INFORMATIONAL

## Finding

Healthy issue tracker with 100% acknowledgment on the 20-issue closed sample, median
time-to-close of 29 days (14 days excluding pre-2024 outliers), and substantive responses.
152 open issues. Primary weakness is batch-style triage with multi-week gaps for initial
response on some recent issues.

## Evidence

### Method

Sampled 20 recently closed issues and 10 open issues from GitHub (e2nIEE/pandapower).
Excluded pull requests. Data collected 2026-03-24 via `gh api`.

### Closed Issues Sample (20 issues)

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
| 2662 | 2025-07-11 | 2026-01-05 | 178 | 4 |
| 2630 | 2025-06-04 | 2026-03-09 | 278 | 1 |
| 2552 | 2025-03-11 | 2026-03-09 | 363 | 5 |
| 1773 | 2022-12-08 | 2026-03-23 | 1,201 | 3 |
| 1400 | 2021-11-18 | 2026-03-23 | 1,586 | 1 |
| 926 | 2020-09-14 | 2025-12-08 | 1,911 | 4 |

### Closed Issue Statistics

| Metric | Value |
|--------|-------|
| Median time-to-close | 29 days |
| P25 | 7 days |
| P75 | 278 days |
| Min | 3 days |
| Max | 1,911 days |
| Acknowledged ratio | 20/20 (100%) |
| Median (excl. pre-2024 outliers) | 14 days |

Three ancient outliers (#926, #1400, #1773) were closed in batch cleanups during December
2025 and March 2026 releases, inflating the P75 and max.

### Open Issues Sample (10 most recent)

| # | Created | Days Open | Comments | Title |
|---|---------|----------|----------|-------|
| 2933 | 2026-03-24 | 0 | 0 | Improve Python-Based OPF Speed |
| 2932 | 2026-03-24 | 0 | 0 | converter broken |
| 2921 | 2026-03-17 | 7 | 1 | Exporting switches to PowerModels.jl |
| 2916 | 2026-03-13 | 11 | 2 | simbench affect on actions |
| 2910 | 2026-03-10 | 14 | 2 | converter issues due to pd.NA |
| 2908 | 2026-03-09 | 15 | 0 | Sincal converter update |
| 2886 | 2026-02-18 | 34 | 1 | create_transformers value init bug |

- **Total open issues (repo-wide):** 152
- **Recent issues (< 14 days):** Several with 0 comments, indicating triage delay
- **Feature requests** remain open under discussion
- **Documentation issues** receive lower priority

### Response Quality

- Issues receive substantive responses from core developers, not bot templates
- Labels (bug, enhancement, maintenance) actively applied
- Batch closures occur during release cycles (e.g., multiple issues closed 2025-12-08
  and 2026-03-09, coinciding with releases)
- Some recent issues (1-2 weeks old) have zero comments, consistent with batch-style
  triage by an academic team

## Implications

Healthy issue tracker consistent with an actively maintained academic project. The 100%
acknowledgment rate and 14-day median (excluding ancient outliers) are strong. The batch
triage pattern and multi-week initial response gaps on some issues are expected for a
team operating on academic schedules rather than commercial SLAs. The 152 open issues is
moderate for a 9-year project of this scope.
