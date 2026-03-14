---
test_id: E-2
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "475ce261"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-2: Commit Activity

## Result: INFORMATIONAL

## Finding

MATPOWER had 121 commits in the last 12 months (since 2025-03-14), with 5 unique committers. The vast majority of commits (106/121, 87.6%) are from the primary maintainer (rdzman / Ray Zimmerman). Activity is heavily concentrated around release preparation (July 2025) with quieter periods otherwise.

## Evidence

Commit data via `gh api repos/MATPOWER/matpower/commits --paginate -f since=2025-03-14`, accessed 2026-03-14:

**Total commits (12 months):** 121 (100 + 21 across paginated results)

**Unique committers:**

| Author | Commits | % |
|--------|---------|---|
| rdzman (Ray Zimmerman) | 106 | 87.6% |
| WilsonGV (Wilson Gonzalez Vanegas) | 7 | 5.8% |
| Ray Zimmerman (email-only, no GH acct link) | 2 | 1.7% |
| yasirroni | 1 | 0.8% |
| MoryNajafi | 1 | 0.8% |
| paulsmoses | 1 | 0.8% |
| roruiz | 1 | 0.8% |
| null (unattributed) | 2 | 1.7% |

**Substantive vs maintenance ratio:** Of the sampled commits, roughly 60-70% are substantive (new features, bug fixes, test additions, new case files) and 30-40% are maintenance (subrepo pulls, CI fixes, documentation/README updates, release bookkeeping). Substantive examples: 3-phase conversion utilities, new case files (case1197, case59, case11kundur), HiGHS/Gurobi solver test updates, save2psse improvements.

**Temporal distribution:** Activity clusters around the 8.1 release (July 2025) with 50+ commits in June-July 2025. Post-release activity is lower but sustained (5-10 commits/month through early 2026).

## Implications

121 commits/year is moderate activity for a tool of MATPOWER's maturity. The project is clearly actively maintained, not abandoned. However, the extreme concentration on a single contributor (87.6% from rdzman) is a sustainability concern addressed separately in E-3. The post-release commit pattern (continued feature development in late 2025 and early 2026) indicates ongoing development rather than maintenance-only mode.
