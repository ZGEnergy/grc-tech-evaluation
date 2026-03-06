---
test_id: E-6
tool: pypsa
dimension: maturity
status: pass
timestamp: 2026-03-05
---

# E-6: CI Configuration and Test Coverage

## Finding

PyPSA has comprehensive CI with multi-OS, multi-Python-version test matrices, code coverage reporting via Codecov, type checking with mypy, and documentation testing.

## Evidence

**CI workflows** (from `.github/workflows/`):

1. **test.yml** - Main test suite:
   - Triggers: push to master, all PRs, daily cron (5am UTC)
   - Matrix: Python 3.11-3.14 x {Ubuntu, macOS, Windows} x {default API, new API}
   - Steps: build package, install, `pytest --cov=pypsa`, upload to Codecov
   - Matplotlib image comparison tests included
   - Concurrency control (cancels in-progress runs on same ref)

2. **test-models.yml** - Model integration tests (separate workflow)

3. **codeql.yml** - GitHub CodeQL security analysis

4. **release.yml** - Automated release pipeline

**Test infrastructure:**
- pytest with coverage (`--cov=pypsa`)
- Branch coverage enabled (`branch = true` in pyproject.toml)
- JUnit XML output for test result tracking
- Codecov integration with per-flag reporting (unit-tests vs doc-tests, per-OS, per-Python)
- Matplotlib baseline image comparison tests (`--mpl`)
- Doc tests via `test/test_docs.py --test-docs`

**Type checking:**
- mypy strict mode runs in CI (`uv run mypy .`)

**Coverage configuration** (from pyproject.toml):

```
[tool.coverage.run]
branch = true
source = ["pypsa"]
```

Coverage percentage is tracked on Codecov but the exact value could not be retrieved via the Codecov web interface at evaluation time. The CI configuration demonstrates a mature testing setup.

**Warnings-as-errors policy:** DeprecationWarning, FutureWarning, RuntimeWarning, and UserWarning are treated as errors in pytest configuration.

## Implications

Excellent CI setup. The multi-OS, multi-Python matrix with daily cron runs, type checking, doc testing, and coverage tracking demonstrates engineering maturity well above typical academic open-source projects. The warnings-as-errors policy shows proactive deprecation management.
