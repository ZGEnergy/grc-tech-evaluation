---
test_id: E-6
tool: powermodels
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "b8b60049"
---

# E-6: ci_test_coverage

## Finding

PowerModels.jl has a comprehensive CI setup with tests running on Julia 1.10 (LTS) and Julia 1 (current) across Ubuntu, macOS, and Windows on every push and PR, plus a weekly scheduled run. Code coverage is 93.93% as measured by Codecov on the current master commit. CI is green on the current release.

## Evidence

**CI exists:** Yes — GitHub Actions, defined in `.github/workflows/ci.yml`

### CI trigger events:
- Push to `master` or `release-*` branches
- Any open/sync/reopen of a pull request
- Weekly scheduled run (every Wednesday at midnight UTC)

#### Test matrix:
- Julia versions: `1.10` (LTS), `1` (current stable)
- OS: `ubuntu-latest`, `macOS-latest`, `windows-latest`
- Architecture: `x64`
- 6 jobs per CI run (2 versions × 3 OS)

**Coverage upload:** `julia-actions/julia-processcoverage@v1` + `codecov/codecov-action@v5` — coverage uploaded on every run with `CODECOV_TOKEN` secret.

#### Badge verification (live Codecov API, not README badge):
Coverage queried directly from `https://codecov.io/api/v2/github/lanl-ansi/repos/PowerModels.jl/commits?branch=master&limit=1`:

```

commitid: bcacabf5  (2025-12-01 — "Bump actions/checkout from 5 to 6")
coverage: 93.93%
files: 43
lines: 9655
hits: 9069
misses: 586
ci_passed: true

```

Coverage has been stable at 93.71–94.19% across all commits in the last 18 months.

#### CI status on current release (v0.21.5 / commit bcacabf5):
Latest GitHub Actions run: `CI completed success 2026-03-11` — green.

Additional workflow files:
- `CompatHelper.yml` — automatic dependency compatibility PRs (runs daily)
- `TagBot.yml` — automated GitHub releases from JuliaRegistries tags
- `documentation.yml` and `documentation-deploy.yml` — docs build and deployment

**Test suite exists:** Yes — `test/` directory; test runner is `test/runtests.jl`; 43 source files measured for coverage.

**Approx coverage:** 93.93% (verified from Codecov API, current master)

**CI green on current release:** Yes

## Implications

A 93.93% coverage rate is excellent for a research-grade scientific library. The multi-OS, multi-version matrix provides confidence that the package works across deployment environments. The weekly scheduled run catches breakage from upstream dependency changes without requiring a code push. CompatHelper automates dependency upper-bound maintenance. This is a strong maturity signal — the test infrastructure is production-grade.
