---
test_id: D-5
tool: matpower
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# D-5: Code Volume Comparison — Suite A Test Scripts

## Methodology

Counted total lines of code (including comments, blank lines, and boilerplate) for
each Suite A test script in `evaluations/matpower/tests/expressiveness/`.

Line counts via `wc -l`.

## Results

| Test | Script | Lines | Category |
|------|--------|-------|----------|
| A-1 | `test_a1_dcpf_tiny.m` | 104 | Core PF |
| A-2 | `test_a2_acpf_tiny.m` | 150 | Core PF |
| A-3 | `test_a3_dcopf_tiny.m` | 143 | Core OPF |
| A-4 | `test_a4_ac_feasibility_tiny.m` | 201 | Contingency |
| A-5 | `test_a5_scuc_tiny.m` | 377 | MOST UC |
| A-6 | `test_a6_sced_tiny.m` | 387 | MOST Dispatch |
| A-7 | `test_a7_contingency_sweep_tiny.m` | 288 | Sensitivity |
| A-8 | `test_a8_stochastic_timeseries_tiny.m` | 316 | MOST Stochastic |
| A-9 | `test_a9_scopf_tiny.m` | 339 | MOST SCOPF |
| A-10 | `test_a10_lossy_dcopf_lmp_tiny.m` | 293 | Manual Workaround |
| A-11 | `test_a11_distributed_slack_opf_tiny.m` | 324 | Manual Workaround |
| | **Total** | **2922** | |

## Analysis by Complexity Tier

### Tier 1: Low Complexity (< 200 LOC)
- A-1 (104), A-3 (143), A-2 (150)
- **Average: 132 LOC**
- These use single-function entry points (`rundcpf`, `rundcopf`, `runpf`)

### Tier 2: Moderate Complexity (200-300 LOC)
- A-4 (201), A-7 (288), A-10 (293)
- **Average: 261 LOC**
- These require loops, manual computation, or PTDF/LODF sensitivity functions

### Tier 3: High Complexity (> 300 LOC)
- A-8 (316), A-11 (324), A-9 (339), A-5 (377), A-6 (387)
- **Average: 349 LOC**
- MOST-based tests require extensive data structure setup
- Workaround tests (A-10, A-11) require manual opt_model construction

## Key Observations

1. **3.7x spread** between simplest (A-1, 104 LOC) and most complex (A-6, 387 LOC).

2. **Core MATPOWER is concise.** The three simplest tests (A-1, A-2, A-3) average
   132 LOC, much of which is boilerplate (path setup, result printing, assertions).
   The actual MATPOWER API calls are typically 3-5 lines.

3. **MOST tests are verbose** due to data structure setup requirements. Each MOST
   test requires constructing `xgd` (extended generator data), `profiles` (load/wind),
   `contab` (contingency tables), and `transmat` (transition probability matrices).

4. **Workaround tests inflate LOC.** A-10 and A-11 implement functionality that
   MATPOWER lacks natively, requiring manual matrix construction and optimization
   model assembly.

5. **Significant boilerplate overhead.** Each script includes ~20 lines of path
   setup, ~15 lines of network loading, and ~30-50 lines of result formatting.
   Effective "analysis code" is roughly 60-70% of the total.
