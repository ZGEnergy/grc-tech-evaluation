---
test_id: E-5
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: QUALIFIED PASS

## Finding

The issue tracker shows active maintenance with a median time-to-close of 81 days. Issues receive responses, but many are closed in batches rather than individually addressed, and several long-standing issues remain open for years without resolution. The response quality is generally good when maintainers engage.

## Evidence

### Sample: Last 20 closed issues (excluding PRs/bot issues)

| Issue | Created    | Closed     | Days Open | Topic                                    |
|-------|------------|------------|-----------|------------------------------------------|
| #988  | 2025-11-11 | 2026-02-01 | 81        | Bus type change behavior                 |
| #991  | 2025-12-03 | 2026-02-01 | 60        | Wrong branch type in case118.m           |
| #935  | 2024-11-28 | 2026-02-01 | 429       | AC powerflow breaks with switches        |
| #987  | 2025-11-05 | 2026-02-01 | 88        | PF ignoring qmax/qmin                    |
| #977  | 2025-07-22 | 2026-02-01 | 193       | calc_branch_flow_nfa support             |
| #984  | 2025-09-18 | 2025-09-20 | 1         | solve_mn_opf_strg error                  |
| #953  | 2025-03-19 | 2025-10-04 | 199       | European network format support          |
| #978  | 2025-07-23 | 2025-07-26 | 3         | Shunt sign confusion                     |
| #974  | 2025-05-26 | 2025-07-26 | 61        | SDP bounds on large cases                |

**Median time-to-close:** 81 days
**Mean time-to-close:** 123.9 days

**Notable pattern:** Issues #988, #991, #935, #987, #977 were all closed on 2026-02-01, suggesting batch triage rather than individual resolution. This is common in maintainer-limited projects.

### Sample: Last 10 open issues

| Issue | Created    | Comments | Age (days) | Topic                              |
|-------|------------|----------|------------|------------------------------------|
| #934  | 2024-11-01 | 12       | 491        | PSSE import gen_status fix         |
| #989  | 2025-11-11 | 4        | 116        | Generators in PQ buses             |
| #975  | 2025-06-04 | 12       | 276        | DCPPowerModel DirectMode           |
| #979  | 2025-07-27 | 1        | 223        | Shunt docs correction              |
| #923  | 2024-07-08 | 2        | 607        | LODF utility request               |
| #969  | 2025-05-01 | 2        | 310        | Remove epigraph formulation        |
| #82   | 2017-02-08 | 10       | 3314       | Feasibility checking               |
| #730  | 2020-07-02 | 4        | 2074       | SDP formulation update             |
| #770  | 2021-03-03 | 1        | 1830       | Parallel power flow                |
| #697  | 2020-04-13 | 2        | 2154       | Power flow improvements            |

**Acknowledged ratio (open issues):** 8/10 have maintainer responses (odow or ccoffrin).
Issues #82, #730, #770, #697 have been open for 2-9 years without resolution.

**Total open issues:** 83

Source: <https://github.com/lanl-ansi/PowerModels.jl/issues>

## Implications

The issue tracker is functional but shows characteristics of a resource-constrained project. Recent issues get attention (especially from odow), but the long tail of ancient open issues and batch-closure pattern indicate limited bandwidth for community support. The 81-day median is acceptable for a research tool but would be concerning for production-critical software.
