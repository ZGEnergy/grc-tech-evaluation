---
test_id: E-6
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

# E-6: CI/Test Coverage

## Result: PASS

## Finding

pandapower has a comprehensive CI pipeline using GitHub Actions with a matrix strategy across 5 Python versions (3.10--3.14). The test suite is organized into 15+ subdirectories covering all major subsystems. Coverage is collected on Python 3.10 and uploaded to Codecov.

## Evidence

**CI Configuration:** `.github/workflows/github_test_action.yml`

Key CI characteristics:
- **Trigger:** Every push and pull request (excluding CHANGELOG changes)
- **Matrix:** Python 3.10, 3.11, 3.12, 3.13, 3.14
- **Test splitting:** pytest-split with 2 groups for parallelism
- **Timeout:** 20 minutes per job
- **Coverage:** pytest-cov on Python 3.10 with XML report uploaded to Codecov
- **Concurrency control:** Cancels in-progress runs on the same PR (avoids wasted compute)
- **Package management:** uv-based (modern tooling)

**Additional CI workflows:**
- `test_release.yml` -- release testing pipeline
- `upload_release.yml` -- automated release publishing

**Test suite structure** (`pandapower/test/`):

| Directory | Scope |
|-----------|-------|
| api | High-level API tests |
| loadflow | Power flow solver tests |
| opf | Optimal power flow tests (run separately) |
| shortcircuit | Short-circuit calculation tests |
| estimation | State estimation tests |
| contingency | Contingency analysis tests |
| control | Controller tests |
| converter | Format conversion tests |
| grid_equivalents | Network reduction tests |
| networks | Built-in network tests |
| plotting | Visualization tests |
| protection | Protection coordination tests |
| timeseries | Time-series simulation tests |
| toolbox | Utility function tests |

Notable: OPF tests are explicitly excluded from the main CI run (`--ignore=pandapower/test/opf`), likely because they require external solvers not available in the CI environment.

- **Source:** [GitHub Actions workflows](https://github.com/e2nIEE/pandapower/tree/develop/.github/workflows)

## Implications

The CI setup is mature and well-configured. Testing across 5 Python versions (including 3.14) demonstrates forward-looking compatibility. The pytest-split parallelism and concurrency controls indicate attention to CI efficiency. The exclusion of OPF tests from CI is a minor gap -- these tests may not run automatically on every commit, though they likely run via `test_release.yml` before publishing.
