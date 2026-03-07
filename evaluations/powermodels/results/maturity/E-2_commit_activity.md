---
test_id: E-2
tool: powermodels
dimension: maturity
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# E-2: Commit Activity

## Result: QUALIFIED PASS

## Finding

PowerModels.jl had 24 commits in the last 12 months from 3 unique human committers. Substantive commits represent 75% of total activity. While the commit volume is low, the project is mature and in maintenance mode, and the commits are high-quality (bug fixes, performance improvements, dependency updates).

## Evidence

**Period:** 2025-03-06 to 2026-03-06

**Total commits:** 24
**Unique human committers:** 3 (odow, LKuhrmann, mtanneau)
**Bot commits:** 4 (dependabot bumps)

**Commit breakdown:**
- Bug fixes: 6 (switch resolution, bus merging, dict syntax, JSON parsing, element type, test relaxation)
- Performance/DX improvements: 3 (PrecompileTools, Memento silence, refactor tests)
- Code cleanup/refactoring: 5 (deprecations, package imports, empty docstrings, spelling fixes)
- Documentation: 2 (admittance matrix docs, doc build fix)
- Version prep: 2 (v0.21.4, v0.21.5)
- Dependency bumps (bot): 4 (actions/checkout, codecov, upload-pages-artifact)
- External contributor PRs: 2 (LKuhrmann #956, #941)

**Substantive ratio:** 18/24 = 75% (excluding bot bumps and version prep)

**Key committers in period:**
- odow (Oscar Dowson, JuMP maintainer): 17 commits -- now the de facto active maintainer
- LKuhrmann: 2 commits (external contributor)
- mtanneau: 1 commit (external contributor)
- dependabot[bot]: 4 commits

Source: <https://github.com/lanl-ansi/PowerModels.jl/commits/master>

## Implications

The commit volume is low (24/year) and the contributor base is narrow (effectively a single active maintainer, odow). This is characteristic of a mature research tool in maintenance mode rather than active development. The qualification reflects the low bus factor risk -- if odow becomes unavailable, commit activity would likely cease. However, the quality of changes is high and the project is stable.
