---
test_id: D-1
tool: pandapower
dimension: accessibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.488
peak_memory_mb: null
loc: 5
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-1: Install to First Solve

## Result: PASS

## Finding

pandapower installs cleanly via `uv sync` with 10 core dependencies (38 total packages including
performance extras). A working DCPF solve requires 5 lines of user code (import, load, solve,
check, extract). First solve completes in under 0.5 seconds. No compiled extensions or external
solver binaries are needed for basic power flow.

## Evidence

**Install process (pyproject.toml):**

```toml
dependencies = [
    "pandapower[performance]",
    "matpowercaseframes",
]
```

- `uv sync` resolves and installs all 38 packages without errors.
- No build-from-source step required. All wheels are pre-built.
- Core dependencies: deepdiff, geojson, networkx, numpy, packaging, pandas, pandera, scipy,
  tqdm, typing_extensions.
- Performance extras add: lightsim2grid, numba, ortools.

**Minimal DCPF code (5 LOC):**

```python
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
net = from_mpc("data/networks/case39.m", f_hz=60)
pp.rundcpp(net)
print(net.res_bus["va_degree"])
```

**First solve timing:** 0.488s wall-clock on IEEE 39-bus (TINY) in the devcontainer. This
includes one-time JIT compilation by numba (performance extra). Subsequent solves are faster.

**Convergence check:** `net.converged` is `True`. Results are in `net.res_bus` (39 rows),
`net.res_line` (35 rows) as pandas DataFrames.

**Verify script:** `evaluations/pandapower/verify_install.py` (24 lines) confirms install
and runs DCPF successfully.

## Implications

pandapower has a low barrier to entry for basic power flow. Pure Python installation with no
external solver dependencies for PF/DCPF. The `pip install pandapower` (or `uv sync`) path
works without friction. The MATPOWER case file converter (`from_mpc`) provides immediate
access to standard test networks. This supports a strong accessibility grade for the
install-to-first-solve criterion.
