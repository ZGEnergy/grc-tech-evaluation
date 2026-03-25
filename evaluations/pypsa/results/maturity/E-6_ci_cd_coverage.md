---
test_id: E-6
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: b8b60049
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

# E-6: CI/CD and Test Coverage

## Result: PASS

## Finding

PyPSA has comprehensive CI/CD infrastructure with 4 GitHub Actions workflows, a
multi-OS/multi-Python test matrix, daily scheduled runs, and independently verified
84.4% code coverage via Codecov. Tests pass on the current release and master branch.

## Evidence

**Sources:**
- GitHub API (`gh run list --repo PyPSA/PyPSA`), queried 2026-03-24
- GitHub workflow files (`.github/workflows/`), accessed 2026-03-24
- Codecov API (`https://codecov.io/api/v2/github/PyPSA/repos/PyPSA/`), queried 2026-03-24

### CI Configuration

CI exists: **Yes.** GitHub Actions with 4 workflow files:

| Workflow | File | Purpose |
|----------|------|---------|
| Tests | `test.yml` | Main test suite — matrix of OS x Python versions x API modes |
| Test models | `test-models.yml` | Tests against downstream model projects |
| CodeQL | `codeql.yml` | Security analysis (CodeQL) |
| Release | `release.yml` | Automated release pipeline |

### Test Matrix Details

The `test.yml` workflow runs:
- **OS matrix**: Ubuntu, macOS, Windows
- **Python versions**: Dynamically determined from `pyproject.toml` classifiers (currently 3.11, 3.12, 3.13, 3.14)
- **API modes**: default, new_api (macOS/Windows only test default)
- **Triggers**: push to master/release branches, all PRs, daily cron (`0 5 * * *`)
- **Concurrency**: Cancels in-progress runs on new commits to same branch

### Code Coverage (Independently Verified)

**Coverage: 84.38%** (via Codecov API, not badge rendering)

| Metric | Value |
|--------|-------|
| Files measured | 84 |
| Total lines | 11,899 |
| Lines hit | 10,041 |
| Lines missed | 1,254 |
| Partial lines | 604 |
| Branch coverage (branches measured) | 2,167 |
| **Overall coverage** | **84.38%** |

Last updated: 2026-03-24T19:17:42Z

The coverage badge in README.md links to `https://codecov.io/gh/PyPSA/PyPSA`. The
84.4% figure was independently verified via the Codecov REST API, not by trusting
badge rendering alone.

### Current CI Status (as of 2026-03-24)

| Workflow | Branch | Status |
|----------|--------|--------|
| Tests | master | passing (2026-03-24T05:56:19Z) |
| Test models | master | passing (2026-03-24T05:54:59Z) |
| CodeQL | master | passing |
| Code Quality (scheduled) | master | passing (2026-03-24T23:32:04Z) |

Most recent feature branch (`fix/network-collection-different-sns`) also shows
passing Tests, Test models, and CodeQL as of 2026-03-24T19:14:11Z.

### Additional Quality Infrastructure

- **pre-commit.ci**: Automated pre-commit hook enforcement on PRs
- **Ruff**: Python linting and formatting
- **REUSE compliance**: License header checking via REUSE standard
- **Downstream testing**: `test-models.yml` runs tests against PyPSA-Eur and other
  dependent projects to catch compatibility regressions

### Consumed Observations

Architecture quality from B-6 noted a clean 4-layer architecture with explicit
model-build/solve separation via linopy, enabling independent unit testing of
each computational stage.

## Implications

PyPSA has best-in-class CI/CD for an academic open-source project. The 84.4%
coverage is strong, the multi-OS/multi-Python matrix catches platform-specific
regressions, the daily scheduled runs catch dependency drift, and downstream
model testing catches ecosystem-wide compatibility issues. The Codecov integration
provides transparent, independently verifiable coverage tracking.

## Recorded Metrics

- ci_exists: yes (GitHub Actions, 4 workflows)
- test_suite_exists: yes (pytest, multi-OS, multi-Python)
- coverage: 84.38% (Codecov API, independently verified)
- tests_pass: yes (current release and master branch)
- daily_ci: yes (cron schedule)
- downstream_testing: yes (test-models.yml)
