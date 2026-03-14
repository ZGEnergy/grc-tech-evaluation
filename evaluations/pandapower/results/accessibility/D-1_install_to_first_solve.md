---
test_id: D-1
tool: pandapower
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "08a21cea"
---

# D-1: Install to First Solve

## Environment

- Container: devcontainer (Ubuntu 24.04, Python 3.12)
- Package manager: uv
- pandapower version: 3.4.0

## Install Process

### Step 1: `uv sync` in `evaluations/pandapower/`

```
Resolved 41 packages in 0.55ms
Audited 39 packages in 0.37ms
```

Wall-clock time: **<1 second** (packages already cached from prior setup).

On a cold install, `uv sync` resolves and installs 39 packages (pandapower + numpy, scipy,
pandas, matplotlib, and other dependencies). From a warm cache, this is near-instantaneous.

### Step 2: `uv run python verify_install.py`

```
pandapower version: 3.4.0
Buses: 39
Lines: 35
Converged: True
```

Wall-clock time: **1.4 seconds** (includes Python startup, pandapower import, network load,
and AC power flow solve).

### Step 3: First solve (import to result)

Timed the complete sequence: import pandapower, load case9, run AC power flow.

```
Time to first solve (import + load + solve): 1.823s
Converged: True
```

## Friction Points

1. **No friction on install.** `uv sync` with the provided `pyproject.toml` works cleanly.
   No system dependencies, no compiler toolchain, no Julia runtime needed for basic
   functionality.

2. **Import time is moderate.** pandapower imports numpy, scipy, pandas, and matplotlib
   eagerly. The ~1.5s import time is noticeable but acceptable for interactive use.

3. **Warning on MATPOWER case loading.** Loading case39 produces a warning:
   "There are 11 branches which are considered as trafos - due to ratio unequal 0 or 1 -
   but connect same voltage levels." This is informational but could confuse new users who
   do not understand the distinction between lines and transformers in pandapower's data
   model.

4. **No Julia dependency needed for basic operations.** The PandaModels.jl bridge
   (for advanced OPF formulations) is optional. Core AC/DC power flow and basic OPF work
   with the pure-Python PYPOWER backend.

## Summary

| Metric | Value |
|--------|-------|
| Install command | `uv sync` |
| Install wall-clock (warm cache) | <1s |
| Dependency count | 39 packages |
| First solve wall-clock | 1.8s |
| System dependencies | None |
| Blocking issues | None |
