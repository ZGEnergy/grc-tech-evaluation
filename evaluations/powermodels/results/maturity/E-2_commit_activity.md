---
test_id: E-2
tool: powermodels
dimension: maturity
status: qualified_pass
timestamp: 2026-03-05
---

# E-2: Commit Activity

## Finding

PowerModels.jl shows moderate but declining commit activity. In the last 24 months (Mar 2024 - Mar 2026), there were approximately 37 commits from 6 unique committers. Notably, the primary maintainer (ccoffrin) has shifted to a secondary role with odow (Oscar Dowson, JuMP maintainer) making the most commits recently.

## Evidence

Commits in last ~24 months (since 2024-03-05), by author:

| Author | Commits | Role |

|--------|---------|------|

| odow | 19 | JuMP ecosystem maintainer |

| ccoffrin | 6 | Original creator (LANL) |

| dependabot[bot] | 6 | Automated dependency updates |

| LKuhrmann | 2 | External contributor |

| Robbybp | 2 | External contributor |

| mtanneau | 2 | External contributor |

Total: ~37 commits from 6 human committers.

Commits in last 12 months (since 2025-03-05): 24 commits.

Last push to master: 2025-12-01 (about 3 months before evaluation date).

Source: GitHub API `repos/lanl-ansi/PowerModels.jl/commits`

## Implications

The commit volume is modest but consistent. The shift from ccoffrin to odow as the primary committer indicates the project is receiving cross-pollination from the broader JuMP ecosystem, which is positive for longevity. However, the low absolute volume (24 commits/year) and significant fraction of automated dependency updates (dependabot) suggests the project is in a maintenance phase rather than active feature development. This is expected for a mature research tool.
