---
test_id: D-3
tool: gridcal
dimension: accessibility
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "2b77857a"
timestamp: "2026-03-13T18:00:00Z"
---

# D-3: Example Verification

## Sources Examined

1. **GridCalTutorials repo** (github.com/SanPen/GridCalTutorials/src/) — 5 files:
   - `defining_a_grid_from_scratch.ipynb` (Jupyter notebook)
   - `defining_a_grid_from_scratch_with_profiles.py` (Python script)
   - `ml_example.py`
   - `rt_example_client.py`
   - `rt_example_server.py`

2. **VeraGrid README** — Installation instructions only; no runnable code examples beyond
   `pip install` and `veragrid` CLI launch.

3. **veragrid.readthedocs.io** — Theory and analysis descriptions. No runnable code
   snippets found in the available sections.

## Example-by-Example Results

### 1. `defining_a_grid_from_scratch.ipynb` — BROKEN

- **Imports:** `from GridCal.Engine import *` — uses deprecated `GridCal.Engine` namespace
- **Status:** Will not run with `veragridengine` package. `GridCal.Engine` does not exist
  in the current package.
- **Fix required:** Replace all `GridCal.Engine` imports with `VeraGridEngine` equivalents.
  Additionally, class names may have changed (e.g., `Branch` no longer exists as a
  unified class; lines and transformers are separate types).
- **Assessment:** Broken, requires non-trivial import and class name migration.

### 2. `defining_a_grid_from_scratch_with_profiles.py` — BROKEN

- **Imports:** `from GridCal.Engine import *`, plus explicit imports of `Branch`,
  `BranchTemplate`, `Bus`, `Generator`, `Load`, `BranchType`, `PowerFlowOptions`,
  `PowerFlowDriver`, `MultiCircuit`, `TimeSeries` from `GridCal.Engine` submodules.
- **Status:** Will not run. Same namespace issue as the notebook. Additionally uses
  `Branch` (deprecated unified class), `BranchTemplate`, and `TimeSeries` driver class
  by old name.
- **Fix required:** Complete import rewrite. Replace `Branch` with `Line`, update driver
  class names, update profile assignment API (`P_prof`, `Q_prof` assignment syntax may
  differ).
- **Assessment:** Broken, requires significant rewrite.

### 3. `ml_example.py` — NOT TESTED (domain-specific)

- Machine learning example, not a getting-started power flow tutorial.
- Likely uses deprecated imports as well.

### 4. `rt_example_client.py` / `rt_example_server.py` — NOT TESTED (infrastructure)

- Real-time server/client examples, not getting-started tutorials.
- Likely use deprecated imports.

## Summary

| Example | Status | Fix Effort |
|---------|--------|------------|
| Grid from scratch (notebook) | Broken | Moderate — import rewrite + class renames |
| Grid from scratch with profiles (script) | Broken | Moderate — import rewrite + class renames + driver renames |
| ML example | Not tested | Unknown |
| RT client/server | Not tested | Unknown |

- **Run unmodified:** 0 of 2 tested
- **Need fixes:** 2 of 2 tested
- **Completely broken (will not import):** 2 of 2 tested

## Root Cause

The GridCal-to-VeraGrid rebrand at v5.4.0 changed the package name and import namespace
from `GridCalEngine`/`GridCal.Engine` to `VeraGridEngine`, but the official tutorials
repository was never updated. The tutorials are frozen at pre-rebrand API conventions.
The repository has only 6 commits total and appears unmaintained.

## Positive Note

While the official tutorials are broken, the `verify_install.py` script in this
evaluation (26 lines) demonstrates that a working first-solve example is achievable
with minimal code using the current API. The core API pattern
(`vge.open_file()` / `vge.power_flow()`) is clean and intuitive once the correct
import namespace is known.
