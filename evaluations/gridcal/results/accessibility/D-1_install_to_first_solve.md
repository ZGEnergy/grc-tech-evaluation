---
test_id: D-1
tool: gridcal
dimension: accessibility
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "d924734c"
timestamp: "2026-03-13T18:00:00Z"
---

# D-1: Install-to-First-Solve

## Setup Process

GridCal is distributed as the `veragridengine` PyPI package (rebranded from `GridCalEngine`
at v5.4.0). The engine-only package installs without a GUI dependency (Qt), making it
suitable for headless/scripted use.

### Steps Performed

1. **Project initialization:** `pyproject.toml` specifies `veragridengine` as the sole
   dependency with `requires-python = ">=3.12"`.
2. **Dependency installation:** `uv sync` resolved 65 packages in 0.59s. The dependency
   tree is moderate — 62 audited packages including numpy, scipy, PuLP, OR-Tools, chardet,
   and several I/O format libraries. No compilation step is required; all wheels are
   pre-built.
3. **Verification script:** `verify_install.py` loads IEEE 39-bus via `vge.open_file()`,
   runs DC power flow with `SolverType.Linear`, and checks convergence.
4. **First solve wall-clock time:** 1.7 seconds (including Python startup, module import,
   file I/O, and solve). The solve itself is sub-second.

### Friction Points

- **Rebrand confusion:** The PyPI package is `veragridengine`, the import is
  `VeraGridEngine`, and the documentation at readthedocs still references `GridCal`/
  `GridCalEngine` in many places. A user searching for "GridCal" on PyPI will find the
  old (deprecated) package. The README explains the rename but this adds a discovery step.
- **urllib3 warning:** `RequestsDependencyWarning: urllib3 (2.6.3) or chardet (6.0.0.post1)/
  charset_normalizer (3.4.4) doesn't match a supported version!` — emitted on every import.
  Cosmetic only; does not affect functionality.
- **No `optimal_power_flow` convenience function:** The top-level `vge` namespace exposes
  `power_flow()` but not a matching `optimal_power_flow()`. OPF requires `vge.linear_opf()`
  or `vge.simple_opf()` — names that are not symmetric with the PF API. Discovered via
  `dir(vge)` introspection, not documentation.

### Positive Notes

- `uv sync` installs cleanly with no build-from-source steps.
- The `vge.open_file()` API reads MATPOWER `.m` files natively with no additional
  configuration.
- First-solve latency (1.7s wall-clock including import) is competitive.
- The `verify_install.py` pattern is simple and effective — 26 lines including imports.

## Assessment

Install-to-first-solve is straightforward for a Python-literate user. The main friction
is the rebrand naming inconsistency (package vs import vs documentation) and the
asymmetric API naming for PF vs OPF. Neither is blocking.
