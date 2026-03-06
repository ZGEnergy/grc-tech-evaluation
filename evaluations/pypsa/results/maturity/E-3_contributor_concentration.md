---
test_id: E-3
tool: pypsa
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-3: Contributor Concentration and Bus Factor

## Finding

PyPSA has 99+ contributors, but the top 3 account for approximately 55% of all commits. The bus factor is effectively 3, with a tight core team at TU Berlin.

## Evidence

Top 10 contributors by commit count (via `gh api repos/PyPSA/PyPSA/contributors`):

| Contributor | Commits | Share |
|-------------|---------|-------|
| fneum | 713 | 23.6% |
| FabianHofmann | 474 | 15.7% |
| nworbmot (Tom Brown) | 470 | 15.6% |
| lkstrp | 291 | 9.7% |
| pre-commit-ci[bot] | 237 | 7.9% |
| coroa | 227 | 7.5% |
| p-glaum | 86 | 2.9% |
| pz-max | 61 | 2.0% |
| lisazeyen | 44 | 1.5% |
| martacki | 40 | 1.3% |

Total contributors: 99+
Total commits tracked: ~3015

Top 3 human contributors (fneum, FabianHofmann, nworbmot): 1657 commits = 54.9%

All three core developers are affiliated with TU Berlin's Department of Digital Transformation in Energy Systems (formerly FIAS). Tom Brown (nworbmot) is the original creator and group leader.

The project also has Open Energy Transition (OET) as a commercial entity providing development support and training, which adds organizational resilience.

## Implications

While the top-3 concentration of ~55% is moderate, the institutional concentration at TU Berlin is a concern for bus factor. However, mitigating factors include: (1) 99+ total contributors showing broad community engagement, (2) OET as a commercial support entity, and (3) the presence of a "second tier" of significant contributors (lkstrp, coroa) who could step up. Qualified pass -- concentration is notable but not disqualifying.
