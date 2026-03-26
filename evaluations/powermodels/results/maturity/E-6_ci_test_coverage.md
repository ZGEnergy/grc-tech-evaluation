---
test_id: E-6
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: b8b60049
status: pass
workaround_class: null
timestamp: 2026-03-24T12:00:00Z
---

# E-6: ci_test_coverage

## Finding

PowerModels.jl has a comprehensive CI setup with tests running on Julia 1.10 (LTS) and Julia 1 (current stable) across Ubuntu, macOS, and Windows. CI runs on every push, PR, and on a weekly Wednesday schedule. Code coverage is 93.93% as verified via the Codecov API and badge SVG (rounds to 94%). CI is green on the current master commit and all recent weekly scheduled runs pass.

## Evidence

**CI exists:** Yes — GitHub Actions, defined in `.github/workflows/ci.yml`.

### CI trigger events
- Push to `master` or `release-*` branches
- Pull request open/sync/reopen
- Weekly scheduled run (every Wednesday at midnight UTC via cron `0 0 * * 3`)

### Test matrix
- Julia versions: `1.10` (LTS), `1` (current stable)
- OS: `ubuntu-latest`, `macOS-latest`, `windows-latest`
- Architecture: `x64`
- 6 jobs per CI run (2 versions x 3 OS)

### Coverage measurement
- `julia-actions/julia-processcoverage@v1` generates `lcov.info`
- `codecov/codecov-action@v5` uploads to Codecov with `CODECOV_TOKEN` secret

### Badge verification (Codecov API + SVG, not README badge rendering)

**Codecov API** (`https://codecov.io/api/v2/github/lanl-ansi/repos/PowerModels.jl/commits?branch=master&limit=1`):
```
commitid: bcacabf5d931ea7d8725363c3cc3d3eb91803d04
commit_date: 2025-12-01
message: "Bump actions/checkout from 5 to 6 (#990)"
coverage: 93.93%
lines: 9,655
hits: 9,069
misses: 586
ci_passed: true
```

**Badge SVG** (`https://codecov.io/gh/lanl-ansi/PowerModels.jl/branch/master/graph/badge.svg`):
Displays **94%** (rounded from 93.93%). Confirmed consistent with API data.

### CI status on current release

Latest release: v0.21.5 (published 2025-08-12). Current master commit: `bcacabf5` (2025-12-01).

**Latest CI workflow run on master:** 2026-03-18, event=schedule, conclusion=success.

**Recent weekly CI runs (all passing):**
- 2026-03-18 — success (schedule)
- 2026-03-11 — success (schedule)
- 2026-03-04 — success (schedule)
- 2026-02-25 — success (schedule)
- 2026-02-18 — success (schedule)

**CompatHelper** runs daily and passes (latest: 2026-03-24).

### Additional workflows
- `CompatHelper.yml` — daily dependency compatibility PRs (active)
- `TagBot.yml` — automated GitHub releases from JuliaRegistries tags (active)
- `Documentation` + `Deploy Documentation to Pages` — docs build and deployment (active)
- `Dependabot Updates` — automated dependency updates (active)

**Test suite exists:** Yes — `test/runtests.jl`; 43 source files measured for coverage.

**Approx coverage:** 93.93% (Codecov API verified, badge SVG confirmed)

**CI green on current release:** Yes — all recent scheduled and push-triggered runs pass.

## Implications

93.93% coverage is excellent for a research-grade scientific computing library. The multi-OS, multi-Julia-version matrix catches platform-specific regressions. The weekly scheduled CI run detects upstream breakage (Julia updates, dependency changes) without requiring code pushes. CompatHelper and Dependabot automate dependency maintenance. This is production-grade CI infrastructure.
