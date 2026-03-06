---
test_id: D-1
tool: pypsa
dimension: accessibility
status: qualified_pass
timestamp: 2026-03-05
---

# D-1: Install-to-first-solve timing

## Finding

PyPSA requires approximately 1.25 seconds from first import to a successful DCPF solve
on IEEE 39-bus. However, the install process has meaningful friction: `uv sync` pulls
87 packages, no native MATPOWER `.m` file reader exists, and the pypower import path
drops gencost data silently.

## Evidence

**Installation:** `uv sync` resolves 87 packages (pypsa, pandapower, matpowercaseframes,
highspy, plus transitive dependencies). The dependency footprint is large for a
power-flow library.

**Import path friction:**
1. PyPSA cannot read `.m` files natively. Requires `matpowercaseframes` to parse
   the file into a pypower `ppc` dict, then `n.import_from_pypower_ppc(ppc)`.
2. The `import_from_pandapower_net()` path crashes on case39 due to a shape mismatch
   bug when multiple generators share a bus (bus 31 in case39).
3. `import_from_pypower_ppc()` emits warnings and silently drops: areas, gencosts,
   and component status fields. The user must manually reconstruct cost data.

**Timing (import-to-solve, warm cache):**
- Wall clock: 1.251s (includes Python import, file parse, network construction, LPF solve)
- This is after `uv sync` has already completed.

**First-time install (`uv sync` from scratch):** takes additional time to download
and install 87 packages. Not measured independently since the devcontainer
pre-provisions the environment, but `uv sync` is fast (typically < 30s).

**Steps to first solve:**

```python
from matpowercaseframes import CaseFrames
import pypsa

cf = CaseFrames("case39.m")
ppc = {"version": "2", "baseMVA": cf.baseMVA,
       "bus": cf.bus.values, "gen": cf.gen.values,
       "branch": cf.branch.values}
n = pypsa.Network()
n.import_from_pypower_ppc(ppc)
n.lpf()  # DC power flow
```

**Friction summary:**
- No native `.m` reader (must use matpowercaseframes as intermediary)
- gencost silently dropped (must manually parse and assign)
- Broken pandapower import path ships in release
- 87-package dependency footprint

## Implications

The core API (`n.lpf()`) is clean once data is loaded, meriting a pass. The qualification
reflects real friction in the import path: users working with standard IEEE/MATPOWER
test cases must learn the matpowercaseframes workaround, discover that gencost is
silently dropped, and avoid the broken pandapower path. The 87-package dependency count
is a supply-chain concern but does not block functionality.
