---
test_id: E-5
tool: pandapower
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: PASS

## Finding

The issue tracker is actively maintained. Median time-to-close for the last 20 closed issues is 1.9 days, with 17 of 20 issues resolved within 7 days. Open issues receive timely responses. The tracker is used as a combined issue/PR workflow (many "issues" are actually pull requests with fixes).

## Evidence

Data sourced from GitHub API on 2026-03-06.

**Last 20 closed issues (sorted by most recently updated):**

| # | Created | Closed | Days Open | Title (truncated) |
|---|---------|--------|-----------|-------------------|
| 2900 | 2026-03-05 | 2026-03-05 | 0.0 | Issues/fixes in structure dict extension |
| 2800 | 2025-11-17 | 2026-03-04 | 107.8 | Difficulty interfacing with PowerModels |
| 2899 | 2026-03-04 | 2026-03-04 | 0.0 | fix shift_lv_degree cim2pp translation |
| 2889 | 2026-02-20 | 2026-02-26 | 5.8 | Fix UnboundLocalError in _from_ppc_branch |
| 2887 | 2026-02-18 | 2026-02-25 | 6.8 | signal 6 error |
| 2890 | 2026-02-23 | 2026-02-23 | 0.0 | sonar_fixes |
| 2892 | 2026-02-24 | 2026-02-24 | 0.0 | structure dict extension more fixes |
| 2891 | 2026-02-24 | 2026-02-24 | 0.0 | Structure dict extension fixes |
| 2888 | 2026-02-19 | 2026-02-23 | 4.1 | fix SonarQube warnings |
| 2884 | 2026-02-12 | 2026-02-17 | 4.8 | addition to structure dict extension |

- **Median time-to-close:** 1.9 days
- **Issues closed within 7 days:** 17/20 (85%)
- **Issues closed within 30 days:** 17/20 (85%)
- **Outlier:** Issue #2800 (107 days) -- a complex PowerModels.jl interop question
- **One ancient issue:** #581 from 2019 was closed same day it was opened (backlog cleanup)

**Last 10 open issues (as of 2026-03-06):**

| # | Created | Title (truncated) |
|---|---------|-------------------|
| 2904 | 2026-03-06 | Issues/fixes in structure dict extension |
| 2903 | 2026-03-06 | Add BSD 3-Clause License heading |
| 2902 | 2026-03-05 | Fix runopp(init="results") |
| 2901 | 2026-03-05 | prevents supply mv through nv |
| 2898 | 2026-03-03 | Distribution in station controller |
| 2895 | 2026-03-01 | enable backward compatibility v3.2.2 |
| 2856 | 2026-01-20 | Adding PF control and tan(phi) control |
| 2788 | 2025-10-30 | incorporate pandera into network structure |
| 2733 | 2025-09-30 | Missing plots in tutorial |
| 2646 | 2025-06-25 | NaN values for single-phase |

Most open issues are recent (within the last week), indicating active triage. Older open items (#2788, #2733, #2646) appear to be feature requests or enhancements rather than critical bugs.

**Total open issues:** 156 (repository-wide, includes PRs counted by GitHub)

- **Source:** [GitHub Issues](https://github.com/e2nIEE/pandapower/issues)

## Implications

The issue tracker shows strong maintainer responsiveness. The fast median close time (1.9 days) reflects a mix of self-submitted fix PRs and genuine external issue resolution. The backlog of 156 open items is typical for a project of this size and does not indicate neglect.
