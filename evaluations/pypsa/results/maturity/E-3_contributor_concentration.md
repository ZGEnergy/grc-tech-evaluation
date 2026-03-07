---
test_id: E-3
tool: pypsa
dimension: maturity
slug: contributor_concentration
network: N/A
protocol_version: v4
status: informational
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# E-3: Contributor Concentration

## Top Contributors (Lifetime)

| Rank | Author | Lifetime Commits | Affiliation |
|------|--------|-----------------|-------------|
| 1 | fneum (Fabian Neumann) | 713 | TU Berlin / OET |
| 2 | FabianHofmann (Fabian Hofmann) | 474 | TU Berlin / OET |
| 3 | nworbmot (Tom Brown) | 470 | TU Berlin (creator) |
| 4 | lkstrp (Lukas Strippe) | 291 | TU Berlin / OET |
| 5 | coroa (Jonas Hoersch) | 227 | Former TU Berlin |
| 6 | p-glaum | 86 | |
| 7 | pz-max | 61 | |
| 8 | lisazeyen | 44 | |
| 9 | martacki | 40 | |
| 10 | (others) | ... | |

Total lifetime contributors: 104

## Concentration Analysis

| Metric | Value |
|--------|-------|
| Top 1 contributor % (lifetime) | 29.3% (fneum) |
| Top 3 contributors % (lifetime) | 68.1% (fneum + FabianHofmann + nworbmot) |
| Top 5 contributors % (lifetime) | 89.3% |
| Contributors with >50 commits | 7 |

## Bus Factor Assessment

Bus factor: 3-4

The project has three maintainers with PyPI publishing rights (fneum, lkstrp, nworbmot). In the last 12 months, the primary active contributor is lkstrp (52.9% of recent commits), with fneum (9.8%) and FabianHofmann (6.7%) as significant secondary contributors. This represents a generational transition from the original creator (nworbmot/Tom Brown) to newer maintainers.

**Risk factors:**
- High concentration: Top 3 lifetime contributors account for 68% of all commits
- Institutional concentration: All top contributors are affiliated with TU Berlin and/or Open Energy Transition (OET)
- Recent concentration: lkstrp alone contributed 53% of commits in the last 12 months

**Mitigating factors:**
- Three independent PyPI maintainers
- OET provides institutional backing beyond any single individual
- 32 unique contributors in the last 12 months shows community breadth
- Stanford (PyPSA-USA) and PyPSA meets Earth provide independent institutional anchors
- MIT license ensures forkability regardless of maintainer availability
