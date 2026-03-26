---
test_id: E-6
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
protocol_version: "v11"
skill_version: "v2"
test_hash: "b75da9be"
---

# E-6: CI/CD and Test Coverage

## Result: INFORMATIONAL

## Finding

pandapower maintains a comprehensive GitHub Actions CI pipeline with ~28 jobs per push,
multi-version Python testing (3.10-3.14), and independently verified Codecov coverage
of 72% on both master and develop branches. All core test jobs pass consistently; the
workflow-level "failure" status is caused by non-core jobs (downstream compatibility,
deprecation warnings), not by pandapower's own test suite.

## Evidence

### CI Configuration

Source: `.github/workflows/github_test_action.yml` on the `develop` branch
(https://github.com/e2nIEE/pandapower/blob/develop/.github/workflows/github_test_action.yml)

| Job | Purpose | Matrix |
|-----|---------|--------|
| **build** | Core test suite (pytest-split into 2 groups) | Python 3.10-3.14 (5 versions x 2 groups = 10 jobs) |
| **numpy1-support** | Backward compat with numpy 1.x | Python 3.14 x 2 groups |
| **opf** | OPF tests with Julia/PandaModels backend | Python 3.14, Julia 1.10 |
| **upload-coverage** | Merges coverage XML, uploads to Codecov + Codacy | -- |
| **warnings** | pytest `-W error` (treat warnings as errors) | Python 3.14 x 2 groups |
| **relying** | Downstream package tests (pandapipes, simbench) | Python 3.10-3.14 |
| **linting** | flake8 syntax and style checks | Python 3.10 |
| **postgresql** | SQL I/O tests against live PostgreSQL 16 | Python 3.14 |
| **tutorial_tests** | Notebook execution via `nbmake` | -- |
| **tutorial_warnings_tests** | Notebook execution with `-W error` | -- |
| **docs_check** | Sphinx docs build with `-W` (warnings-as-errors) | -- |
| **typing** | mypy static type checking | Python 3.14 |

The workflow uses `pytest-split` for test parallelization and `concurrency` groups to
cancel superseded runs on the same PR.

### Latest develop Branch CI (2026-03-24)

Verified via `gh api repos/e2nIEE/pandapower/actions/runs/23498302967/jobs`:

- **All 10 core `build` jobs: PASS** (Python 3.10-3.14, both split groups)
- **numpy1-support: PASS** (both groups)
- **opf: PASS**
- **typing (mypy): PASS**
- **tutorial_tests: PASS**
- **tutorial_warnings_tests: PASS**
- **linting: PASS**
- **postgresql: PASS**
- **Sphinx docs check: PASS**
- **upload-coverage: PASS**
- **warnings (3.14, 1): FAIL** (deprecation warnings in dependencies)
- **warnings (3.14, 2): CANCELLED**
- **relying (3.12): FAIL** (downstream pandapipes/simbench compatibility)
- **relying (other versions): CANCELLED**

The workflow-level conclusion is "failure" because GitHub Actions reports failure if any
job fails. The failures are exclusively in non-core jobs (`warnings` and `relying`), not
in pandapower's own test suite.

### Test Coverage

Codecov badge SVGs fetched directly (2026-03-24):
- `https://codecov.io/github/e2nIEE/pandapower/coverage.svg?branch=master` -- **72%**
- `https://codecov.io/github/e2nIEE/pandapower/coverage.svg?branch=develop` -- **72%**

Badge SVG confirmed by parsing the XML: `>72%<` appears in the text elements.

Coverage is measured on the Python 3.10 build jobs using `pytest-cov`, with XML reports
uploaded to both Codecov and Codacy. The coverage figure excludes OPF tests (run in a
separate job with Julia dependencies) and may therefore undercount actual coverage.

### Test Suite Structure

Tests reside in `pandapower/test/` with subdirectories: `api/`, `loadflow/`, `opf/`,
`shortcircuit/`, `estimation/`, `contingency/`, `control/`, `converter/`,
`grid_equivalents/`, `networks/`, `plotting/`, `protection/`, `timeseries/`,
`toolbox/`, `topology/`.

### CI Hygiene Observation

pandapower has zero all-green workflow runs in recent history because `relying` and
`warnings` jobs have been persistently failing. This is a CI hygiene issue -- these
jobs should arguably be `continue-on-error: true` or in a separate workflow -- but it
does not indicate that pandapower's own test suite is broken.

## Implications

pandapower demonstrates strong CI maturity:
- Multi-version Python testing across 5 Python versions
- Dedicated OPF testing with Julia integration
- PostgreSQL integration testing, tutorial notebook execution, mypy type checking
- Dual code quality platforms (Codecov + Codacy)
- 72% test coverage is moderate -- adequate for a research-origin tool but below
  industry best practice (80%+)

The persistent CI "failures" from non-core jobs are a minor hygiene concern but do not
affect the reliability of pandapower's own test suite.
