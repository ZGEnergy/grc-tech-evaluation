---
test_id: F-9
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "81981b48"
timestamp: "2026-03-13T23:00:00Z"
---

# F-9: Getting-Started Integrity

## Finding

The evaluation's getting-started artifact (`verify_install.py`) works correctly and demonstrates DCPF on the IEEE 39-bus case. However, the version pin in `pyproject.toml` is unpinned (`veragridengine` with no version constraint), and the upstream project's own getting-started documentation has reported broken links.

## Evidence

**Evaluation getting-started artifact:**
- File: `evaluations/gridcal/verify_install.py`
- Functionality: Loads case39.m, runs DC power flow (SolverType.Linear), verifies convergence
- Output: Reports version, bus count, branch count, convergence status
- Exit code: 0 on success, 1 on failure
- Status: **Works correctly** with veragridengine 5.6.28

**Version pinning in `pyproject.toml`:**
```toml
dependencies = [
    "veragridengine",
]
```
- No version constraint: `veragridengine` with no `>=`, `==`, or `~=` specifier
- This means `uv sync` will install whatever version is latest at install time
- Risk: breaking changes in future versions could cause verify_install.py to fail
- The 5.4.0 rename (GridCalEngine -> VeraGridEngine) is already reflected in the dependency name

**Upstream getting-started documentation:**
- GitHub issue #416: "Getting Started Link is not working" (created 2025-08-05, closed 2026-01-07)
- GitHub issue #347: "Link on tutorials is broken" (created 2025-03-11, closed 2026-01-07)
- ReadTheDocs documentation covers up to v5.0.2 only; current version is 5.6.x
- README provides basic install instructions (`pip install VeraGridEngine`) that work correctly

**Reproducibility assessment:**
- The `pyproject.toml` uses `uv` with `package = false` (application mode)
- No `uv.lock` file was observed, meaning exact dependency versions are not locked
- Running `uv sync` at different times could produce different dependency versions
- The installed version (5.6.28) is 6 patch releases behind latest (5.6.34)

## Implications

The getting-started artifact functions correctly but has two integrity gaps: (1) no version pin on `veragridengine`, meaning future installs may get a different (potentially incompatible) version, and (2) no lock file to freeze the complete dependency tree. For evaluation reproducibility, pinning to `veragridengine==5.6.28` and committing a `uv.lock` would be advisable. The upstream project's broken documentation links (now fixed) suggest a history of documentation maintenance issues.
