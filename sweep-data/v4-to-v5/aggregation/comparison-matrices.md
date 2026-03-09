# Cross-Tool Comparison Matrices

## Contract  | v4-to-v5 Aggregation

---

## Test Outcome Matrix

Legend: P = pass, F = fail, QP = qualified_pass, I = informational, -- = not attempted/blocked

### Gate Tests

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER |
|---------|-------|------------|---------|-------------|----------|----------|
| G-1 (TINY) | P | P | P | P | P | P |
| G-2 (SMALL) | P | P | P | P | P | P |
| G-3 (MEDIUM) | P | P | P | P | P | P |

**Signal:** None. Unanimous pass. All tools handle MATPOWER .m format.

### Suite A: Problem Expressiveness

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| A-1 TINY | P | P | P | P | P | P | 1 | Low |
| A-1 MED | P* | P | P | P | P | P | 2 | Low |
| A-2 TINY | P | P | P | P | P | P | 1 | Low |
| A-2 MED | P** | P | P | F | F | P | 3 | High |
| A-3 TINY | P | QP | P | P | QP | P | 2 | Low |
| A-3 MED | F | QP | P | P | -- | P | 3 | High |
| A-4 TINY | P | P | P | P | QP | P | 2 | Low |
| A-4 MED | F | P | P | QP | -- | P | 3 | High |
| A-5 TINY | P | F | F | QP | QP | P | 3 | High |
| A-5 SMALL | F | F | F | F | -- | P | 2 | Medium |
| A-6 TINY | P | F | F | QP | QP | P | 3 | High |
| A-6 SMALL | F | F | F | F | -- | P | 2 | Medium |
| A-7 TINY | P | P | QP | QP | P | P | 2 | Low |
| A-7 MED | F | P | QP | F | -- | P | 3 | High |
| A-8 TINY | F | F | F | F | F | P | 2 | Medium |
| A-8 SMALL | F | F | F | F | -- | -- | 1 | Low |
| A-9 TINY | P | F | F | QP | QP | P | 3 | High |
| A-9 SMALL | P | F | F | QP | -- | P | 3 | High |
| A-10 TINY | P | F | QP | QP | F | QP | 4 | High |
| A-10 SMALL | P | F | QP | QP | F | QP | 4 | High |
| A-11 TINY | P | F | F | QP | QP | QP | 4 | High |
| A-11 SMALL | P | F | F | QP | -- | QP | 3 | High |

Notes:
- *P\** = A-1 MEDIUM PyPSA: all flows NaN due to singular matrix; pass is misleading (probe-001 related)
- *P\*\** = A-2 MEDIUM PyPSA: non-convergence warning; debunked by probe-001 (0 NR iterations, 83% flat start)

### Suite B: Extensibility

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| B-1 TINY | P | QP | F | P | P | P | 3 | High |
| B-1 MED | F | QP | F | P | -- | P | 3 | High |
| B-2 TINY | P | P | P | QP | QP | P | 2 | Low |
| B-2 MED | P | P | P | QP | -- | P | 2 | Low |
| B-3 TINY | P | P | P | P | P | P | 1 | Low |
| B-3 MED | F | P | P | P | -- | P | 2 | Medium |
| B-4 TINY | P | QP | QP | P | P | P | 2 | Low |
| B-4 SMALL | P | QP | QP | P | P | P | 2 | Low |
| B-5 TINY | P | P | P | P | P | P | 1 | Low |
| B-5 MED | P | P | P | P | -- | P | 1 | Low |
| B-6 | I | P | P | P | P | I | 2 | Low |
| B-7 TINY | P | P | P | P | QP | P | 2 | Low |
| B-7 MED | P | P | P | P | -- | P | 1 | Low |
| B-8 TINY | P | QP | P | P | P | QP | 2 | Low |
| B-8 SMALL | P | QP | P | P | -- | QP | 2 | Low |
| B-9 TINY | P | QP | P | P | P | P | 2 | Low |
| B-9 MED | F | QP | QP | P | -- | P | 3 | High |

### Suite C: Scalability

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| C-1 MED | P | P | P | P | P | P | 1 | Low |
| C-2 MED | P | P | P | F | F | P | 2 | Medium |
| C-3 MED | P | QP | P | P | QP* | P | 3 | Medium |
| C-4 SMALL | F | F | F | F | QP* | F | 2 | Medium |
| C-5 MED | QP | P | P | F | QP* | P | 3 | Medium |
| C-6 SMALL | P | QP | F | P | QP* | F | 3 | Medium |
| C-7 MED | P | F | P | QP | P | P | 2 | Medium |
| C-8 MED | F | F | F | F | F | F | 1 | Low |
| C-9 MED | QP | P | QP | P | P | P | 2 | Low |
| C-10 MED | P | F | F | QP | F | QP | 3 | Medium |

Notes:
- *QP\** = PowerSimulations C-3/C-4/C-5/C-6: estimated timings only, no actual measurement (probe-020 confirms)

### Suite D: Workforce Accessibility

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| D-1 | P | P | QP | QP | QP | I | 3 | Medium |
| D-2 | QP | QP | I | QP | I | I | 2 | Low |
| D-3 | P | P | QP | QP | I | I | 3 | Medium |
| D-4 | QP | QP | F | QP | QP | I | 3 | Medium |
| D-5 | I | I | I | I | I | I | 1 | Low |

### Suite E: Maturity & Sustainability

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| E-1 | I | P | P | P | I | I | 2 | Low |
| E-2 | I | P | P | QP | I | I | 2 | Low |
| E-3 | I | P | QP | F | I | I | 3 | Medium |
| E-4 | I | P | F | I | I | I | 2 | Low |
| E-5 | I | P | QP | QP | I | I | 2 | Low |
| E-6 | I | P | QP | P | I | I | 2 | Low |
| E-7 | I | P | QP | F | I | I | 3 | Medium |

### Suite F: Supply Chain

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| F-1 | P | P | QP | P | P | P | 2 | Low |
| F-2 | QP | P | P | I | I | P | 3 | Low |
| F-3 | QP | P | P | QP | I | P | 2 | Low |
| F-4 | P | P | P | P | P | P | 1 | Low |
| F-5 | P | P | P | P | P | P | 1 | Low |
| F-6 | P | P | P | P | P | I | 2 | Low |
| F-7 | P | P | F | P | P | P | 2 | Low |
| F-8 | P | P | QP | P | P | P | 2 | Low |
| F-9 | QP | QP | QP | P | I | I | 3 | Low |

### Phase 2 Readiness

| Test ID | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------|------------|---------|-------------|----------|----------|--------|--------|
| P2-1 | I | I | P | I | I | I | 2 | Low |
| P2-2 | I | I | F | I | I | I | 2 | Low |
| P2-3 | I | I | F | I | I | I | 2 | Low |

---

## Signal Summary

### High-Signal Tests (3+ distinct outcomes)

| Test | Dominant Factor | Notes |
|------|----------------|-------|
| A-2 MED | Tool capability | ACPF convergence at 10k: pandapower/gridcal/matpower pass; PM/PSI fail |
| A-3 MED | Infrastructure/data | PyPSA fails from zero s_nom; others pass with various approaches |
| A-4 MED | Tool capability + data | ACPF-based feasibility; some tools cannot solve ACPF at scale |
| A-5 TINY | Tool capability | SCUC architecture: built-in (pypsa/matpower) vs manual (PM/PSI) vs absent (pp/gc) |
| A-6 TINY | Tool capability | Same split as A-5 (SCED depends on UC) |
| A-7 MED | Combinatorial + tool | N-M explosion; only pp/gc/matpower complete at MEDIUM |
| A-9 TINY/SMALL | Tool capability | SCOPF: pypsa/matpower native; PM manual; pp/gc absent |
| A-10 | Tool capability | Lossy DCOPF: wide range from native (pypsa) to absent (pp/PSI) |
| A-11 | Tool capability | Distributed slack: wide range from native to absent |
| B-1 | Tool architecture | Custom constraints: JuMP-based (PM/PSI) and linopy (pypsa) vs absent (gc) |
| B-9 MED | Data + tool | PTDF accuracy at scale; phase-shifter correction issue (probe-010) |

### Low-Signal Tests (unanimous or near-unanimous)

| Test | Outcome | Reason |
|------|---------|--------|
| G-1/G-2/G-3 | All pass | MATPOWER format trivial for all tools |
| A-1 TINY | All pass | DCPF on 39-bus is trivial |
| A-2 TINY | All pass | ACPF on 39-bus is trivial |
| B-3 TINY | All pass | N-1 loop on 39-bus is trivial |
| B-5 TINY/MED | All pass | CSV export trivial for DataFrame-based tools |
| C-1 MED | All pass | DCPF scales well for all tools |
| C-8 MED | All fail | SCOPF at 500 contingencies on 10k-bus is infeasible for all |

---

## Probe Impact on Outcomes

| Probe | Tool | Test | Original | Corrected | Impact |
|-------|------|------|----------|-----------|--------|
| probe-001 | PyPSA | A-2 MED | pass | **should be fail** | 0 NR iterations, 83% flat start |
| probe-009 | pandapower | P2-3 | lambda 1e25 claim | **lambda claim debunked** | Both methods have identical convergence |
| probe-021 | PowerSim | A-4 | 100x unit mismatch | **labeling error** | Dispatch is MW, limits are pu; no actual mismatch |
| probe-025 | PowerSim | E-6 | 100% coverage | **78% coverage** | Badge misread |
| probe-010 | pandapower | B-9 | shunt attribution | **phase-shifter attribution** | Pbusinj/Pfinj correction eliminates all error |
| probe-006/007 | cross-tool | A-3/C-3 | uniform LMPs | **confirmed: no binding constraints** | Network insufficiency, not tool issue |
| probe-028 | MATPOWER | C-10 | 66 min timing | **confirmed: dense PTDF matrix** | MIPS on dense matrices is 400x slower |
| probe-029 | MATPOWER | C-5 | 97% Octave overhead | **confirmed** | LODF screening fast; containers.Map is bottleneck |
| probe-032 | MATPOWER | C-4 | solver capacity fail | **loadmd() ingestion fail** | Solver never invoked |
