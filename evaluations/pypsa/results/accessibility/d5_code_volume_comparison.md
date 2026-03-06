---
test_id: D-5
tool: pypsa
dimension: accessibility
status: informational
timestamp: 2026-03-05
---

# D-5: Code volume comparison -- LOC for each Suite A test

## Finding

PyPSA test implementations range from 110 LOC (DCPF) to 276 LOC (contingency sweep).
The contingency sweep (A-7) is a clear outlier at 2.5x the median, reflecting the
absence of a built-in N-M sweep API. Core power flow and optimization tests are compact.

## Evidence

| Test | Description | LOC | Notes |
|------|-------------|-----|-------|
| A-1 | DCPF | 110 | Minimal: load + `n.lpf()` + extract results |
| A-2 | ACPF | 151 | Adds convergence checking and DC warm-start fallback |
| A-3 | DC OPF | 147 | +5 LOC for manual gencost assignment workaround |
| A-5 | SCUC | 164 | 24h snapshots, UC parameters, commitment extraction |
| A-7 | Contingency sweep | 276 | No built-in N-M sweep; manual graph construction, branch deactivation loop, islanding detection |
| A-8 | Stochastic timeseries | 182 | set_scenarios() API + error handling for import-path bug |
| A-9 | SCOPF | 215 | Multiple fallback attempts for infeasibility |
| A-10 | Lossy DC OPF | 177 | Lossless baseline + lossy solve + LMP decomposition |
| A-11 | Distributed slack OPF | 176 | Inspection of API + multiple solver comparisons |

**Statistics:**
- Median: 176 LOC
- Mean: 177 LOC
- Min: 110 LOC (A-1, DCPF)
- Max: 276 LOC (A-7, contingency sweep)
- Total: 1,598 LOC across 9 tests

**Note:** These LOC counts include test harness boilerplate (imports, load_network helper,
result dict construction, JSON output). The `load_network` helper alone is ~12 LOC and
is repeated in each file. Pure "domain logic" LOC would be lower, but the boilerplate
is a real cost of using PyPSA with MATPOWER case files.

**Outlier analysis:**
- A-7 (276 LOC) is 57% above median. This reflects the complete absence of a built-in
  contingency sweep function. The user must build: NetworkX graph construction, graph-distance
  filtering, combinatorial enumeration, branch deactivation/restoration, and islanding
  detection -- all from scratch.
- A-9 (215 LOC) is elevated due to multiple fallback attempts needed when case39 is
  N-1 infeasible for the full contingency set.

## Implications

For tasks with built-in API support (A-1, A-2, A-3, A-5, A-10), PyPSA is concise.
The code volume spikes when users must assemble workflows from primitives (A-7) or
handle undocumented failure modes (A-8, A-9, A-11). The MATPOWER import boilerplate
adds a fixed overhead to every test.
