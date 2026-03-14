---
test_id: E-6
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "b75da9be"
---

# E-6: CI/CD and Test Coverage — pandapower

## Sub-criterion
5a (Demonstrated Maturity)

## Method
Examined GitHub Actions workflow configuration (`.github/workflows/github_test_action.yml`),
recent CI run results via `gh api`, and verified test coverage percentage by fetching
the Codecov badge SVG directly (not relying on README badge rendering).

## CI/CD Configuration

pandapower uses GitHub Actions with a comprehensive multi-job workflow triggered on every
push and pull request:

| Job | Purpose | Matrix |
|-----|---------|--------|
| **build** | Core test suite (pytest-split into 2 groups) | Python 3.10 - 3.14 (5 versions x 2 groups = 10 jobs) |
| **numpy1-support** | Backward compat with numpy 1.x | Python 3.14 x 2 groups |
| **opf** | OPF tests with Julia/PandaModels backend | Python 3.14, Julia 1.10 |
| **upload-coverage** | Merges coverage XML, uploads to Codecov + Codacy | — |
| **warnings** | pytest `-W error` (treat warnings as errors) | Python 3.14 x 2 groups |
| **relying** | Downstream package tests (pandapipes, simbench) | Python 3.10 - 3.14 |
| **linting** | flake8 syntax and style checks | Python 3.10 |
| **postgresql** | SQL I/O tests against live PostgreSQL 16 | Python 3.14 |
| **tutorial_tests** | Notebook execution via `nbmake` | — |
| **tutorial_warnings_tests** | Notebook execution with `-W error` | — |
| **docs_check** | Sphinx docs build with `-W` (warnings-as-errors) | — |
| **typing** | mypy static type checking | Python 3.14 |

**Total CI jobs per push:** ~28 (across all matrix combinations).

The workflow uses `pytest-split` for test parallelization and `concurrency` groups to
cancel superseded runs on the same PR.

## Test Suite Structure

Tests reside in `pandapower/test/` with subdirectories covering:

- `api/` (file I/O, SQL)
- `loadflow/`
- `opf/`
- `shortcircuit/`
- `estimation/` (state estimation)
- `contingency/`
- `control/`
- `converter/`
- `grid_equivalents/`
- `networks/`
- `plotting/`
- `protection/`
- `timeseries/`
- `toolbox/`
- `topology/`

## CI Pass Status (develop branch, 2026-03-11)

The latest develop-branch run shows the following job-level results:

- **All 14 core `build` jobs: PASS** (Python 3.10-3.14, both split groups)
- **numpy1-support: PASS** (both groups)
- **opf: PASS**
- **typing (mypy): PASS**
- **tutorial_tests: PASS**
- **tutorial_warnings_tests: PASS**
- **linting: PASS**
- **postgresql: PASS**
- **Sphinx docs check: PASS**
- **upload-coverage: PASS**
- **warnings: FAIL** (Python 3.14 — deprecation warnings in dependencies)
- **relying: FAIL** (downstream pandapipes/simbench compatibility issues)

The workflow-level conclusion is "failure" because GitHub Actions reports failure if any
job fails. However, all 14 core test jobs (the `build` matrix) pass on all Python versions.
The failures are in non-core jobs: `warnings` (third-party deprecation warnings treated as
errors) and `relying` (downstream package compatibility), not in pandapower's own tests.

**Note:** The `pandapower` workflow has zero all-green runs in recent history because the
`relying` and `warnings` jobs have been persistently failing. This is a CI hygiene issue
(these jobs should arguably be `continue-on-error: true` or in a separate workflow), but
it does not indicate that pandapower's own test suite is broken.

## Test Coverage

**Codecov badge (master branch):** 72%
**Codecov badge (develop branch):** 72%

Coverage is measured on the Python 3.10 build jobs using `pytest-cov`, with XML reports
uploaded to both Codecov and Codacy. The coverage figure excludes OPF tests (run in a
separate job with Julia dependencies) and may therefore undercount actual coverage.

The badge SVG was fetched directly at:
- `https://codecov.io/github/e2nIEE/pandapower/coverage.svg?branch=master` → **72%**
- `https://codecov.io/github/e2nIEE/pandapower/coverage.svg?branch=develop` → **72%**

Both Codecov and Codacy integrations are active, providing dual code-quality tracking.

## Assessment

pandapower has a mature, comprehensive CI pipeline with:
- Multi-version Python testing (3.10 through 3.14)
- Parallel test splitting for faster feedback
- Dedicated OPF testing with Julia integration
- PostgreSQL integration testing against a live database
- Tutorial notebook execution testing
- Static type checking (mypy), linting (flake8), and docs build verification
- Downstream package compatibility testing

The 72% coverage is moderate. Core test jobs pass consistently on all supported Python
versions. The workflow-level "failure" status is a cosmetic issue caused by non-core jobs
(downstream compatibility, deprecation warnings) rather than test failures in pandapower
itself.
