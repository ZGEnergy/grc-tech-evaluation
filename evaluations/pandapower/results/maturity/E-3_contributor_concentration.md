---
test_id: E-3
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "7c6517db"
---

# E-3: Contributor Concentration — pandapower

## Sub-criterion
5b (Sustainability Risk)

## Method
Two analyses:
1. **Commit concentration:** Lifetime contributor statistics from GitHub contributor API
   (183 total contributors).
2. **Reviewer concentration:** Sampled last 50 merged PRs, fetched reviews via GitHub API,
   excluded bots, computed reviewer distribution.

## Part 1: Commit Concentration (Lifetime)

| Contributor | Commits | % of Total |
|-------------|---------|-----------|
| rbolgaryn | 1,808 | 24.0% |
| lthurner | 1,532 | 20.3% |
| vogt31337 | 518 | 6.9% |
| KS-HTK | 403 | 5.3% |
| wangzhenassd | 357 | 4.7% |
| pawellytaev | 239 | 3.2% |
| dlohmeier | 193 | 2.6% |
| hilbrich | 187 | 2.5% |
| shankhoghosh | 184 | 2.4% |
| ZhengLiu1119 | 179 | 2.4% |

- **Total contributors (lifetime):** 183
- **Total commits (top 50 contributors):** 7,537
- **Top 1 contributor (rbolgaryn):** 24.0%
- **Top 3 contributors:** 51.2% (rbolgaryn + lthurner + vogt31337)
- **Bus factor:** 3 (top 3 contributors needed to reach 50% of commits)

## Part 2: Reviewer Concentration (Last 50 Merged PRs)

Of 50 sampled merged PRs, 48 had at least one human review (96%).

| Reviewer | PRs Reviewed | % of Reviewed PRs |
|----------|-------------|-------------------|
| vogt31337 | 19 | 39.6% |
| heckstrahler | 18 | 37.5% |
| KS-HTK | 11 | 22.9% |
| mrifraunhofer | 4 | 8.3% |
| furqan463 | 3 | 6.2% |
| marcopau | 1 | 2.1% |
| MMatthiessen | 1 | 2.1% |
| hilbrich | 1 | 2.1% |
| pawellytaev | 1 | 2.1% |

- **Top reviewer (vogt31337):** 39.6% of reviewed PRs
- **Top 3 reviewers (vogt31337 + heckstrahler + KS-HTK):** 100% of reviewed PRs
- **Total unique reviewers:** 9

### Reviewer Concentration Flag

The top reviewer (vogt31337) is at 39.6%, which is below the 60% threshold. **No single-reviewer
concentration flag is raised.**

However, the top 3 reviewers cover 100% of reviewed PRs. This means all code review is performed
by three individuals. While none individually dominates above 60%, the review function is
concentrated in a small group. If all three were unavailable simultaneously, no reviews would
occur.

## Cross-Reference with Consumed Observations

- **B-2 observation (arch-quality):** Notes exemplary NetworkX graph bridge design — suggests
  the core architecture is well-factored, which mitigates some bus-factor risk through code
  readability.
- **B-6 observation (arch-quality):** Notes clean 6-layer architecture but OPF duals are
  discarded — indicates some areas where institutional knowledge is embedded in undocumented
  internal conventions.
- **B-1 observation (doc-gaps):** The undocumented userfcn mechanism is an example of knowledge
  concentrated in the original developers (rbolgaryn, lthurner) that would be hard for new
  contributors to discover.

## Analysis

- **Commit bus factor of 3** is moderate for an academic project. The two dominant contributors
  (rbolgaryn, lthurner) together account for 44.3% of lifetime commits — both are affiliated
  with the originating institutions (University of Kassel / Fraunhofer IEE).
- **Reviewer pool is narrow but not critically so.** Three active reviewers with the top
  reviewer below 60% is acceptable, though the absence of any reviewer outside this trio is
  a concentration risk.
- **Recent committer diversity is better than lifetime numbers suggest.** The trailing 12-month
  data (E-2) shows 30 unique committers with the top committer at 30.1%, indicating the
  contributor base is broadening over time.

## Assessment

Moderate concentration risk. Bus factor of 3, reviewer pool of 3 active individuals, no single
reviewer above 60%. The project has 183 lifetime contributors and 30 active in the last year,
indicating a broad but loosely engaged contributor base with a concentrated core team.
