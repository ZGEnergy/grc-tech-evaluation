---
test_id: E-3
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

# E-3: Contributor Concentration

## Result: PASS

## Finding

The top 3 contributors account for 50.0% of all commits. The top 2 (rbolgaryn and lthurner) dominate with 43.3% combined, but neither individually exceeds 25%. The project has 134 total contributors, with meaningful contributions from at least 10 people (100+ commits each). Bus factor is approximately 2--3.

## Evidence

Data sourced from GitHub API on 2026-03-06:

| Rank | Contributor | Commits | Share |
|------|------------|---------|-------|
| 1 | rbolgaryn | 1,808 | 23.4% |
| 2 | lthurner | 1,532 | 19.9% |
| 3 | vogt31337 | 518 | 6.7% |
| 4 | KS-HTK | 403 | 5.2% |
| 5 | wangzhenassd | 357 | 4.6% |
| 6 | pawellytaev | 239 | 3.1% |
| 7 | dlohmeier | 193 | 2.5% |
| 8 | hilbrich | 187 | 2.4% |
| 9 | shankhoghosh | 184 | 2.4% |
| 10 | ZhengLiu1119 | 179 | 2.3% |

- **Top 3 combined:** 3,858 / 7,717 = 50.0%
- **Total contributors:** 134
- **Contributors with 100+ commits:** 16
- **Source:** [GitHub Contributors](https://github.com/e2nIEE/pandapower/graphs/contributors)

Both top contributors (rbolgaryn and lthurner) are affiliated with University of Kassel / Fraunhofer IEE, indicating institutional rather than individual ownership. In the last 12 months, 21 unique committers were active, suggesting the knowledge base extends beyond the top 2.

## Implications

The bus factor of 2--3 is moderate. The top two contributors are institutionally backed (not hobbyist maintainers), which reduces single-point-of-failure risk. However, if both key contributors left the project simultaneously, continuity would depend on the next tier of contributors (vogt31337, KS-HTK, etc.) who each hold under 7% of total commits.
