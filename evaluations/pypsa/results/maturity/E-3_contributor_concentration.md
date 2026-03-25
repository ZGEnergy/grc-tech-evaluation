---
test_id: E-3
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 3e956677
status: pass
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
timestamp: 2026-03-24T23:50:00Z
---

# E-3: Contributor and Reviewer Concentration

## Result: PASS

## Finding

PyPSA has a bus factor of 2-3 with healthy contributor distribution. The top 3
lifetime contributors account for 55.0% of all commits. Review concentration is
moderate: the top reviewer handles 58.1% of reviews (below the 60% flag threshold),
and the top 3 reviewers cover 86.0%. Merge authority is concentrated on one maintainer
(lkstrp, 82%) but review load is more distributed.

## Evidence

### Commit Concentration

**Source:** GitHub API (`gh api repos/PyPSA/PyPSA/contributors`), queried 2026-03-24.

Total lifetime contributors: 99 (per pagination headers).

**Top 10 Contributors (Lifetime):**

| Rank | Contributor | Commits | Percentage |
|------|-------------|---------|------------|
| 1 | fneum (Fabian Neumann) | 713 | 23.0% |
| 2 | FabianHofmann (Fabian Hofmann) | 479 | 15.4% |
| 3 | nworbmot (Tom Brown) | 470 | 15.2% |
| 4 | lkstrp (Lukas Trippe) | 291 | 9.4% |
| 5 | pre-commit-ci[bot] | 237 | 7.6% |
| 6 | coroa | 227 | 7.3% |
| 7 | p-glaum | 86 | 2.8% |
| 8 | pz-max | 62 | 2.0% |
| 9 | lisazeyen | 44 | 1.4% |
| 10 | martacki | 40 | 1.3% |

**Top 3 human contributors combined: 1,662 / ~3,100 = 53.6% of all commits.**

(Excluding pre-commit-ci[bot] from the contributor list, the top 3 human contributors
represent 55.0% of human-authored commits.)

**Bus factor: 2-3.** The project has successfully transitioned maintainership:
1. **Founding era**: nworbmot (Tom Brown) was the primary developer
2. **Growth era**: fneum and FabianHofmann took on significant development
3. **Current era**: lkstrp is the active primary maintainer (166 commits in last 12 months)

### Reviewer Concentration

**Source:** GitHub API, reviews on last 50 merged PRs (`gh pr list --repo PyPSA/PyPSA
--state merged --limit 50`), queried 2026-03-24.

**Reviews (APPROVED or CHANGES_REQUESTED) on 50 most recent merged PRs:**

| Reviewer | Reviews | Percentage |
|----------|---------|------------|
| lkstrp | 25 | 58.1% |
| fneum | 8 | 18.6% |
| FabianHofmann | 4 | 9.3% |
| euronion | 4 | 9.3% |
| Irieo | 1 | 2.3% |
| coroa | 1 | 2.3% |

Total reviews across 50 PRs: 43 (some PRs had no formal review, some had multiple).

- **Top reviewer (lkstrp):** 58.1% — below the 60% flag threshold
- **Top 3 reviewers (lkstrp + fneum + FabianHofmann):** 86.0%
- **Unique reviewers:** 6

**Merge concentration (who clicked merge):**

| Merger | PRs Merged | Percentage |
|--------|-----------|------------|
| lkstrp | 41 | 82% |
| FabianHofmann | 7 | 14% |
| Irieo | 1 | 2% |
| fneum | 1 | 2% |

The high merge concentration on lkstrp (82%) is a moderate risk factor, but merge
authority is a GitHub permission concern rather than a code quality concern. The review
load is more distributed (6 reviewers, top at 58.1%), which mitigates single-point-of-failure
risk.

### Consumed Observations

Architecture quality observations from extensibility tests (B-1, B-2, B-3, B-4, B-6,
B-8, B-9) uniformly noted clean, well-separated code architecture with 4 abstraction
layers and 8 mixins. This level of architectural maturity typically indicates the
codebase can accommodate maintainer transitions without degradation.

## Implications

The contributor concentration is healthy for an academic open-source project. The
successful transition from founder (nworbmot) to current primary maintainer (lkstrp)
demonstrates institutional continuity. The reviewer pool of 6 active reviewers with
the top reviewer below 60% suggests adequate review distribution. The merge concentration
on lkstrp is the primary risk factor but is mitigated by the broader review base.

## Recorded Metrics

- top_contributor_pct: 23.0% (fneum, lifetime)
- top_3_contributor_pct: 55.0% (human-only, lifetime)
- bus_factor: 2-3
- total_contributors: 99
- top_reviewer_pct: 58.1% (lkstrp)
- top_3_reviewer_pct: 86.0%
- unique_reviewers: 6
- reviewer_flag: none (top reviewer < 60%)
