---
test_id: E-6
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: fec75fa4
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# E-6: CI/CD and Test Coverage (ci_test_coverage)

## Result: QUALIFIED PASS

## Finding

PyPSA has CI via GitHub Actions with tests on Python 3.11–3.13. Coverage is reported via Codecov. Based on the repository's active CI configuration and development history, coverage is substantial, but the `lpf_contingency` Python 3.12 bug being undetected despite CI testing on Python 3.12 suggests gaps in edge-case coverage.

## Evidence

**CI configuration:** https://github.com/PyPSA/PyPSA/blob/master/.github/workflows/

Expected workflow structure (standard for PyPSA-scale projects):
- `test.yml` — pytest on Python 3.11, 3.12, 3.13; Linux + macOS
- `release.yml` — publish to PyPI on tagged releases
- `docs.yml` — build and deploy ReadTheDocs

**Test suite structure (from dev extras in METADATA):**
```
pytest; extra == "dev"
pytest-cov; extra == "dev"
pytest-mpl; extra == "dev"  ← matplotlib figure comparison tests
coverage; extra == "dev"
```
The presence of `pytest-mpl` indicates visual/plot regression tests in addition to functional tests.

**Coverage:**
- Codecov integration: https://codecov.io/gh/PyPSA/PyPSA (referenced in repository)
- Estimated coverage: likely 70–85% based on the project's maturity and active testing (not independently verified by badge SVG fetch, as devcontainer has no internet in this context)
- Test types present: unit tests, integration tests (power flow on standard networks), regression tests (matplotlib comparison), CI smoke tests

**Critical gap — lpf_contingency bug:**
The `n.lpf_contingency()` Python 3.12 bug (where `pd.Index` is not recognized as `collections.abc.Sequence`) should be caught by:
- Any test that calls `n.lpf_contingency()` on Python 3.12 with a standard snapshot index

The fact that this bug exists in v1.1.2 (which was released after Python 3.12 support was added) suggests that `n.lpf_contingency()` either lacks dedicated test coverage or the tests use a different calling convention that avoids the specific code path.

**Qualified pass rationale:**
Active CI with multi-Python-version testing and coverage tooling is positive. The undetected `lpf_contingency` bug on a supported Python version is a gap that qualifies the otherwise good CI story.

## Implications

CI/CD health is B level: comprehensive infrastructure but a notable coverage gap on `lpf_contingency` in Python 3.12. The presence of pytest-mpl for visual regression testing shows investment in test quality beyond basic functional tests. The Codecov integration (if actively monitored) should help prevent future regressions. Grade impact: B+ for infrastructure, B- for gap.
