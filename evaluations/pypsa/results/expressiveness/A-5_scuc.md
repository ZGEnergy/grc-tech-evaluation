---
test_id: A-5
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 1640c770
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 6.770
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 467
solver: HiGHS
timestamp: 2026-03-24T12:00:00Z
---

# A-5: Solve 24-hour unit commitment as MILP on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via `import_from_pypower_ppc()`, then applied
Modified Tiny augmentation:

1. **Differentiated generator costs** from `gen_temporal_params.csv`:
   hydro $5, nuclear $10, coal $25, gas CC $40 per MWh.

2. **UC parameters** from `gen_temporal_params.csv`: startup costs (cold
   start), ramp rates (MW/hr converted to per-unit), min up/down times
   (hours, cast to int for PyPSA's rolling window constraints).

3. **24-hour load profile** from `load_24h.csv`: distributed proportionally
   across 21 load buses. System load ranges 4,237--6,254 MW.

4. **All generators set `committable=True`** with `p_min_pu=0.3` (30%
   minimum stable generation when committed).

Solved via `n.optimize()` with HiGHS MILP settings per `solver-config.md`
(mip_rel_gap=0.01, time_limit=300, threads=1). PyPSA activates binary
commitment variables automatically when `committable=True`.

### Built-in vs user-assembled constraint types

| Constraint | Type | PyPSA attribute |
|-----------|------|-----------------|
| Binary commitment | built-in | `n.generators.committable = True` |
| Min up time | built-in | `n.generators.min_up_time` |
| Min down time | built-in | `n.generators.min_down_time` |
| Startup cost | built-in | `n.generators.start_up_cost` |
| Shutdown cost | built-in | `n.generators.shut_down_cost` |
| Ramp limits | built-in | `n.generators.ramp_limit_up/down` |
| Min stable gen | built-in | `n.generators.p_min_pu` |
| Reserve requirement | user-assembled | via `extra_functionality` callback |
| Joint UC + dispatch | built-in | single `n.optimize()` call |

## Output

### Solver Performance

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Termination | Optimal |
| MIP gap | 0.818% (< 1% threshold) |
| Objective | $1,743,649.64 |
| MILP variables | 720 binary (commitment + start/shut) |
| Solve time | 1.89s |

### Generator Cycling

3 generators cycle during the 24-hour horizon, exceeding the >= 2 requirement:

| Generator | Technology | Transitions | Pattern |
|-----------|-----------|-------------|---------|
| G3 | coal_large | 1 | Off at hour 23 |
| G6 | gas_CC | 1 | Off at hours 20-23 |
| G9 | gas_CC | 3 | Off hours 3-8, back on hour 9, off hours 22-23 |

The gas CC generators (G6, G9 at $40/MWh) are decommitted during
low-load hours, which is the economically expected behavior with
differentiated costs. Nuclear generators remain on for all 24 hours
due to high startup costs ($64,000) and long min_down_time (48 hours).

### Commitment Schedule (binary)

```
Hour  G0 G1 G2 G3 G4 G5 G6 G7 G8 G9
 0     1  1  1  1  1  1  1  1  1  1
 1     1  1  1  1  1  1  1  1  1  1
 2     1  1  1  1  1  1  1  1  1  1
 3     1  1  1  1  1  1  1  1  1  0
 4     1  1  1  1  1  1  1  1  1  0
 5     1  1  1  1  1  1  1  1  1  0
 6     1  1  1  1  1  1  1  1  1  0
 7     1  1  1  1  1  1  1  1  1  0
 8     1  1  1  1  1  1  1  1  1  0
 9     1  1  1  1  1  1  1  1  1  1
...
20     1  1  1  1  1  1  0  1  1  1
21     1  1  1  1  1  1  0  1  1  1
22     1  1  1  1  1  1  0  1  1  0
23     1  1  1  0  1  1  0  1  1  0
```

### Binding Verification (v11 mandatory)

Re-ran with `min_up_time=min_down_time=0` for all generators to verify
that the min up/down constraints are actually binding.

| Metric | Constrained | Relaxed |
|--------|------------|---------|
| Objective | $1,743,649.64 | $1,693,316.97 |
| Cost reduction | -- | -2.89% |
| Changed generators | -- | G3, G4, G6, G9 |

4 generators changed their commitment schedule when min up/down constraints
were removed, confirming the constraints are binding. The relaxed solution
is $50,333 cheaper (2.89% reduction), demonstrating the economic impact of
the temporal coupling constraints. G4 (coal) additionally cycles in the
relaxed case, freed from its 24-hour min_up_time constraint.

### MIP Gap Extraction

HiGHS reports the MIP gap directly in its output: `Gap: 0.818% (tolerance: 1%)`.
This is extractable from solver output. PyPSA does not surface MIP gap in
`n.objective` attributes, but the solver's verbose output provides it.

## Workarounds

None required. PyPSA's UC formulation is fully built-in via `committable=True`
with native support for min up/down times, startup costs, ramp limits, and
joint UC+dispatch optimization. The `n.generators_t.status` DataFrame provides
the commitment schedule as a time-indexed binary matrix.

## Timing

- **Wall-clock:** 6.770s (first solve + binding verification re-solve)
- **First solve only:** 1.89s
- **Binding verification solve:** 3.80s
- **Timing source:** measured
- **Peak memory:** not measured (not a scalability test)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a5_scuc_tiny.py`
