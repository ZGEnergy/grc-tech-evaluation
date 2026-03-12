---
test_id: A-5
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 314538b0
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.70
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 312
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# A-5: SCUC — 24-hour Unit Commitment

## Result: PASS

## Approach

Loaded case39.m via `matpowercaseframes.CaseFrames` → pypower ppc dict → `n.import_from_pypower_ppc()`. Assigned per-generator parameters from Modified Tiny `gen_temporal_params.csv`:

- **Marginal costs** by tech class: hydro $5, nuclear $10, coal $25, gas_CC $40/MWh
- **Startup costs** (cold start): from CSV — nuclear $64,000, coal $36,750, gas_CC $28,047 per start
- **Ramp limits**: converted from MW/hr to per-unit fraction of p_nom, capped at 1.0
- **Min up/down times**: integer hours from CSV (hydro 1h/1h, nuclear 24h/48h, coal 24h/48h, gas_CC 8h/4.5h rounded to 8h/5h)
- **p_min_pu = 0.3** for all generators (minimum stable generation when committed)
- Set `n.generators["committable"] = True` for all 10 generators
- 24-hour load profile from Modified Tiny `load_24h.csv`, summed across all buses and distributed proportionally to load components

Called `n.optimize(snapshots=n.snapshots, solver_name="highs", solver_options={time_limit:300, mip_rel_gap:0.01, presolve:"on", threads:1, output_flag:True})`.

**API friction noted:** `min_up_time` and `min_down_time` default to int64 dtype in PyPSA's generators DataFrame. Assigning float values (e.g., 4.5 hours) triggers a FutureWarning and then causes a `TypeError: pad_width must be of integral type` deep in PyPSA's rolling-window constraint builder for min up/down time constraints. Fix: cast values to `int` before assignment and enforce dtype with `.astype(int)`. Classified as stable workaround (documented public attribute, type requirement findable from error trace).

## Output

HiGHS 1.13.1 MILP problem:
- **Rows:** 6,107 | **Columns:** 2,064 (720 binary) | **Nonzeros:** 15,892
- **Termination:** Optimal
- **MIP gap:** 0.818% (within 1% tolerance)
- **Objective:** $1,743,649.64 (total 24-hour generation cost)
- **Solve time:** 1.62s (wall-clock)
- **B&B nodes:** 1

**Commitment schedule:**

| Generator | Tech | p_nom (MW) | MC ($/MWh) | Hours OFF |
|-----------|------|-----------|------------|-----------|
| G0 | Hydro | 1040 | 5 | 0 (all on) |
| G1 | Nuclear | 646 | 10 | 0 (all on) |
| G2 | Nuclear | 725 | 10 | 0 (all on) |
| G3 | Coal | 652 | 25 | 1 (H24) |
| G4 | Coal | 508 | 25 | 0 (all on) |
| G5 | Nuclear | 687 | 10 | 0 (all on) |
| G6 | Gas CC | 580 | 40 | 3 (H21–H23) |
| G7 | Nuclear | 564 | 10 | 0 (all on) |
| G8 | Nuclear | 865 | 10 | 0 (all on) |
| G9 | Gas CC | 1100 | 40 | 6 (H4–H9, H23–H24) |

**Cycling generators (≥1 commitment transition):**
- G3 (coal $25): 1 transition — decommits at H24 (low load overnight)
- G6 (gas CC $40): 1 transition — decommits at H21–H23 (post-peak hours)
- G9 (gas CC $40): 3 transitions — decommits H4–H9 (deep overnight), recommits H10, decommits again H23–H24

**3 generators cycle** → pass condition met (≥2 required).

**Formulation expressiveness confirmed:**

| Feature | Supported | Constraint name in solver output |
|---------|-----------|----------------------------------|
| Binary commitment variables | Yes | `Generator-com-status-*` |
| Min up time | Yes | `Generator-com-up-time`, `Generator-com-status-min_up_time_must_stay_up` |
| Min down time | Yes | `Generator-com-down-time` |
| Startup cost | Yes | `Generator-start_up-p-fixed-upper` |
| Ramp limits | Yes | `Generator-p-ramp_limit_up/down` |
| Joint UC+dispatch | Yes | Single MILP solved by HiGHS |
| Reserve (extra_functionality) | Expressible | Via custom constraint injection callback |

**Dispatch range:**

| Gen | Min dispatch (MW) | Max dispatch (MW) |
|-----|-------------------|-------------------|
| G0 (hydro) | 843.1 | 900.0 |
| G1 (nuclear) | 461.2 | 646.0 |
| G2 (nuclear) | 725.0 | 725.0 |
| G3 (coal) | 0.0 | 652.0 |
| G4 (coal) | 152.4 | 508.0 |
| G5 (nuclear) | 344.4 | 687.0 |
| G6 (gas CC) | 0.0 | 472.2 |
| G7 (nuclear) | 169.2 | 564.0 |
| G8 (nuclear) | 259.5 | 865.0 |
| G9 (gas CC) | 0.0 | 330.0 |

## Workarounds

- **What:** `min_up_time` and `min_down_time` must be explicitly cast to `int` dtype before assignment to `n.generators`
- **Why:** PyPSA's rolling-window constraint builder for min up/down time constraints uses these values as `pad_width` in `xarray.variable.rolling_window()`, which requires an integral type. The generators DataFrame initializes these columns as int64, but `.at[name, col] = float_value` silently stores the float without dtype enforcement in pandas until the FutureWarning becomes an error. PyPSA does not validate or coerce this internally.
- **Durability:** stable — using publicly documented generator attributes (`min_up_time`, `min_down_time`); the fix is a standard Python `int()` cast. The underlying requirement (integer hours) is mentioned in PyPSA issue discussions.
- **Grade impact:** Minor API friction. Does not affect expressiveness grade — the feature is fully functional once the type is correct.
- **Version tested:** PyPSA 1.1.2, xarray 2024.x, numpy 1.26+

## Timing

- **Wall-clock:** 2.70s total (1.62s solve, 1.08s model build + data load)
- **Timing source:** measured (`time.perf_counter()`)
- **Peak memory:** not measured
- **Solver iterations:** 3,213 LP iterations (B&B tree: 1 node)
- **Convergence residual:** N/A (MILP)
- **MIP gap at termination:** 0.818%
- **CPU cores used:** 1 (single-threaded per solver-config.md)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a5_scuc_tiny.py`

Key API pattern for SCUC:
```python
# Enable binary UC variables
n.generators["committable"] = True
n.generators["min_up_time"] = n.generators["min_up_time"].astype(int)   # must be int
n.generators["min_down_time"] = n.generators["min_down_time"].astype(int)

# Solve MILP (HiGHS automatically uses binary branching for committable generators)
n.optimize(snapshots=snapshots, solver_name="highs", solver_options={...})

# Read commitment schedule
status_df = n.generators_t.status  # DataFrame(snapshots × generators), values 0.0/1.0
```
