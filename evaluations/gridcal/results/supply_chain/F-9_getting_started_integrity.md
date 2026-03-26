---
test_id: F-9
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "81981b48"
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T18:00:00Z"
---

# F-9: Getting-Started Integrity

## Result: PASS

## Finding

The evaluation's getting-started artifact (`verify_install.py`) works correctly and demonstrates DCPF on the IEEE 39-bus case. The `pyproject.toml` does not pin the veragridengine version, but a `uv.lock` file exists that freezes the complete dependency tree, ensuring reproducible installs. The upstream project's examples directory contains 49 scripts but version pins are absent.

## Evidence

**Evaluation getting-started artifact:**
- File: `evaluations/gridcal/verify_install.py`
- Functionality: Loads case39.m, runs DC power flow (`SolverType.Linear`), verifies convergence
- Output: Reports version, bus count, branch count, convergence status
- Status: **Works correctly** with veragridengine 5.6.28

**Version pinning in `pyproject.toml`:**
```toml
dependencies = [
    "veragridengine",
]
```
- No version constraint on veragridengine (no `>=`, `==`, or `~=`)
- Risk: breaking changes in future versions could cause failures

**Lock file:**
- `uv.lock` file exists (304 KB, dated 2026-03-09)
- This freezes all 62 dependency versions for reproducible installs via `uv sync`
- The lock file mitigates the unpinned `pyproject.toml` constraint

**Upstream getting-started resources:**
- GitHub `examples/` directory: 49 Python scripts covering various analysis types (power flow, OPF, contingency analysis, CPF, etc.)
- Examples do not specify version requirements or pin dependencies
- README provides basic install: `pip install VeraGridEngine` (no version pin)
- ReadTheDocs documentation covers up to v5.0.2; current version is 5.6.x (significant documentation lag)
- GitHub issues #416 and #347 reported broken getting-started/tutorial links (both closed 2026-01-07)

**Reproducibility assessment:**
- With `uv sync`: reproducible (lock file pins all versions)
- With `pip install`: not reproducible (no version pins, will get latest)
- Installed version (5.6.28) is 10 patch releases behind PyPI latest (5.6.38)

## Implications

The getting-started artifact functions correctly. The presence of a `uv.lock` file provides reproducible dependency resolution, which is the primary integrity requirement. The unpinned `pyproject.toml` is a minor concern mitigated by the lock file. The upstream project's documentation lag (ReadTheDocs at v5.0.2 vs current v5.6.x) and history of broken links indicate ongoing documentation maintenance challenges, but this does not affect the evaluation's own artifact integrity.
