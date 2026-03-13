---
test_id: A-1
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 32fb2553
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.116
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 114
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-1: DC Power Flow (dcpf)

## Result: PASS

## Approach

Loaded IEEE 39-bus case39.m via `matpowercaseframes.CaseFrames` → PYPOWER ppc dict (with `.values` numpy arrays) → `pypsa.Network.import_from_pypower_ppc()`. Ran DC (linear) power flow via `n.lpf()`. Extracted outputs as pandas DataFrames from `n.buses_t.v_ang`, `n.buses_t.p`, and `n.lines_t.p0`.

The ppc dict must be constructed manually with `.values` arrays — `CaseFrames.to_dict()` returns DataFrames which `import_from_pypower_ppc` cannot handle.

## Output

All three required outputs confirmed as pandas DataFrames:

**Voltage Angles (degrees, first 5 buses):**

| Bus | Angle (deg) |
|-----|-------------|
| 1 | -12.304 |
| 2 | -8.104 |
| 3 | -10.989 |
| 4 | -11.650 |
| 5 | -10.346 |

**Line Flows p0 (MW, first 5 lines):**

| Line | Flow (MW) |
|------|-----------|
| L0 | -178.354 |
| L1 | 80.754 |
| L2 | 333.430 |
| L3 | -261.784 |
| L4 | 54.115 |

**Nodal Injections p (MW, first 5 buses):**

| Bus | Injection (MW) |
|-----|----------------|
| 1 | -97.6 |
| 2 | 0.0 |
| 3 | -322.0 |
| 4 | -500.0 |
| 5 | 0.0 |

**Summary statistics:**
- Buses: 39, Lines: 35, Generators: 10
- Non-zero voltage angles: 38 of 39 buses (slack bus = 0 by definition)
- Non-zero line flows: 35 of 35 lines
- Max voltage angle: ±13.46 degrees
- Max line flow: 608.78 MW
- Slack bus: Bus 31

## Workarounds

- **What:** Used `matpowercaseframes.CaseFrames` to parse `.m` file, then manually constructed PYPOWER ppc dict with `cf.bus.values`, `cf.gen.values`, `cf.branch.values` (numpy arrays), then called `n.import_from_pypower_ppc(ppc)`.
- **Why:** PyPSA has no native MATPOWER .m reader. `CaseFrames.to_dict()` returns pandas DataFrames, but `import_from_pypower_ppc` requires numpy array format.
- **Durability:** stable — `matpowercaseframes` is a documented companion package; `import_from_pypower_ppc` is a public API method used in official examples.
- **Grade impact:** B-level. The parsing pipeline is standard; only the intermediate step of constructing the ppc dict is non-obvious.

## Timing

- **Wall-clock:** 1.116 s (includes network load, lpf solve, and result extraction)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solve time (lpf only):** 0.065 s
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a1_dcpf_tiny.py`

Key API sequence:
```python
from matpowercaseframes import CaseFrames
cf = CaseFrames(network_file)
ppc = {"version": "2", "baseMVA": cf.baseMVA, "bus": cf.bus.values,
       "gen": cf.gen.values, "branch": cf.branch.values}
n = pypsa.Network()
n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
n.lpf()
v_ang = n.buses_t.v_ang      # DataFrame
p_inject = n.buses_t.p       # DataFrame
p0 = n.lines_t.p0            # DataFrame
```
