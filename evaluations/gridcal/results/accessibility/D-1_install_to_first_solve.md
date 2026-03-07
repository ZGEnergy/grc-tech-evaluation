---
test_id: D-1
tool: gridcal
dimension: accessibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# D-1: Install to First Solve

## Result: QUALIFIED PASS

## Install Process

### Step 1: Package identification (friction)

The project was recently renamed from GridCal to VeraGrid. A user searching for "GridCal" on PyPI will find the old `GridCalEngine` package (v5.4.1), which prints a deprecation notice on every import:

```
GridCal has changed name to VeraGrid.
The gridcal package cannot be updated anymore, instead install
the also free and open source 'veragrid' witch is just the new name
of the software.
```

The new package is `veragridengine` on PyPI. There is no redirect, no compatibility shim, and no obvious link from the old package page to the new one. The deprecation message contains a typo ("witch" instead of "which").

### Step 2: Installation

```bash
uv add veragridengine   # or: pip install veragridengine
```

Installation is a standard `pip install` with no compiled extensions to build. All dependencies are pure Python or have pre-built wheels. No system-level dependencies required.

### Step 3: Import and verify

```python
import VeraGridEngine as vge
```

Every import produces a `RequestsDependencyWarning` about urllib3/chardet version mismatch. This is a packaging hygiene issue, not a functional problem.

`VeraGridEngine.__version__` raises `AttributeError`. Version must be retrieved via `importlib.metadata.version("veragridengine")`.

### Step 4: First solve (DCPF on IEEE 39-bus)

```python
grid = vge.open_file("case39.m")
opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
results = vge.power_flow(grid, options=opts)
```

The DC power flow solver is named `SolverType.Linear`, not `SolverType.DC` or anything containing "DC". A new user would not find this without reading source code or documentation.

The MATPOWER `.m` file reader works cleanly in one call (`vge.open_file()`).

## Issues Encountered

| # | Issue | Severity |
|---|-------|----------|
| 1 | Package rename (GridCalEngine -> VeraGridEngine) with no migration path | Medium |
| 2 | Deprecation message typo ("witch") | Low |
| 3 | urllib3/chardet version warning on every import | Low |
| 4 | No `__version__` attribute | Low |
| 5 | DC power flow named `SolverType.Linear`, not searchable as "DC" | Low |

## Wall-Clock Estimate

From `uv add veragridengine` to successful DCPF solve: approximately 2-3 minutes (install ~60s, writing 4-line script ~30s, debugging SolverType naming ~60s).

## Why QUALIFIED PASS

Installation itself is frictionless (pure Python, pip install). First solve completes quickly. However, the rename friction and non-obvious solver naming reduce the experience. A user who finds the old GridCalEngine first will lose significant time before discovering veragridengine.
