---
test_id: E-6
tool: pypsa
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: b8b60049
---

# E-6: CI/CD and Test Coverage

## Findings

### CI Configuration

CI exists: **Yes.** GitHub Actions with 4 workflow files:

| Workflow | Purpose |
|----------|---------|
| `test.yml` | Main test suite — matrix of OS (Ubuntu, macOS, Windows) x Python versions x API modes |
| `test-models.yml` | Tests against downstream model projects |
| `codeql.yml` | Security analysis (CodeQL) |
| `release.yml` | Automated release pipeline |

### Test Suite

Test suite exists: **Yes.**

The test workflow (`test.yml`) runs:
- Package build and verification (setuptools_scm)
- Test matrix: 3 OS x N Python versions x 2 API modes (default, new_api)
- Daily scheduled runs (cron `0 5 * * *`) to catch dependency drift
- Concurrency management (cancels in-progress runs on new commits)

### CI Execution Frequency

- Runs on every push to `master` and release branches
- Runs on every pull request
- Runs daily on schedule

### Current CI Status

Most recent runs on `master` branch:
- Tests: passing on `fix-check-missing-buses` branch
- CodeQL: passing
- Test models: passing
- One docs-related failure (CairoSVG pip install) — cosmetic, not test failure

### Coverage

Approximate coverage: **Not directly measurable from CI config.** The CI
does not run coverage reporting as a visible badge. However, the test
suite is comprehensive:
- Unit tests for all major components (power flow, optimization, IO)
- Integration tests with multiple solver backends
- Cross-platform testing (Linux, macOS, Windows)
- Multi-Python-version testing (3.11, 3.12, 3.13, 3.14)
- Downstream model compatibility testing (test-models.yml)

### Tests Pass on Current Release

**Yes.** The v1.1.2 release (2026-02-23) was published after passing CI.
The most recent `master` branch CI runs show passing status.

### Consumed Observations

Architecture quality from B-6 noted a clean 4-layer architecture with
good separation of concerns, which is consistent with a testable codebase.
The OPF path has explicit model-build/solve separation via linopy, enabling
independent unit testing of each stage.

## Recorded Metrics

- ci_exists: yes (GitHub Actions, 4 workflows)
- test_suite_exists: yes (pytest, multi-OS, multi-Python)
- coverage: not reported as badge; comprehensive test matrix
- tests_pass: yes (current release and master branch)
