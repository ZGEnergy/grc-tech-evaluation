---
test_id: E-3
tool: pypsa
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 3e956677
---

# E-3: Contributor Concentration

## Findings

### Top 3 Contributors (Lifetime)

Total all-time commits across 99 contributors: ~3,020.

| Rank | Contributor | Commits | Percentage | Affiliation |
|------|-------------|---------|------------|-------------|
| 1 | fneum (Fabian Neumann) | 713 | 23.6% | TU Berlin / PyPSA-Eur |
| 2 | FabianHofmann (Fabian Hofmann) | 479 | 15.9% | PyPSA maintainer |
| 3 | nworbmot (Tom Brown) | 470 | 15.6% | TU Berlin, project founder |

**Top 3 combined: 55.1% of all commits.**

### Reviewer Concentration (50 Most Recent Merged PRs)

| Reviewer | PRs Reviewed | Percentage |
|----------|-------------|------------|
| lkstrp | 30 | 44.8% |
| fneum | 10 | 14.9% |
| FabianHofmann | 9 | 13.4% |
| euronion | 9 | 13.4% |
| Other (4) | 9 | 13.4% |

### Merge Concentration

Of the 50 most recent merged PRs:
- lkstrp merged 42 (84%)
- FabianHofmann merged 6 (12%)
- Irieo merged 1 (2%)
- fneum merged 1 (2%)

### Bus Factor Assessment

**Bus factor: 2-3.** The project has transitioned maintainership over time:

1. **Founding era**: nworbmot (Tom Brown) was the primary developer
2. **Growth era**: fneum and FabianHofmann took on significant development
3. **Current era**: lkstrp is the active primary maintainer, with fneum,
   FabianHofmann, and Irieo as active reviewers/contributors

The high merge concentration on lkstrp (84%) is a moderate risk factor.
However, the review load is more distributed (4 reviewers each handling
>13% of reviews), which mitigates the single-point-of-failure risk.

### Consumed Observations

Architecture quality observations from extensibility tests (B-1, B-2, B-3,
B-4, B-6, B-8, B-9) uniformly noted clean, well-separated code architecture
with 4 abstraction layers and 8 mixins. This level of architectural maturity
typically indicates that the codebase can accommodate maintainer transitions
without degradation.

## Recorded Metrics

- top_contributor_pct: 23.6% (fneum)
- bus_factor: 2-3 (moderate)
- total_contributors: 99
- reviewer_count_active: 4 (>13% each)
