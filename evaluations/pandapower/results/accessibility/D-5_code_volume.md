---
test_id: D-5
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

Lines of code required for each Suite A test in pandapower. Tests that PASS tend to be
concise (53-142 code lines). Tests that FAIL are verbose because they document absent
capabilities and show diagnostic exploration of the API surface.

## Evidence

**LOC per test (pandapower v3.4.0):**

| Test | Status | Total Lines | Code Lines | Notes |
|------|--------|-------------|------------|-------|
| A-1 (DCPF) | PASS | 88 | 53 | Minimal: load, solve, extract |
| A-2 (ACPF) | PASS | 123 | 77 | Includes convergence fallback protocol |
| A-3 (DC OPF) | QUALIFIED PASS | 135 | 81 | Cost setup + LMP extraction |
| A-4 (AC feasibility) | PASS | 170 | 107 | DC OPF + ACPF + violation checks |
| A-5 (SCUC) | FAIL | 131 | 65 | Capability assessment only (no SCUC) |
| A-6 (SCED) | FAIL | 115 | 59 | Dependency failure doc (no SCUC for A-5) |
| A-7 (Contingency) | PASS | 217 | 142 | Graph distance + combinatorial sweep |
| A-8 (Stochastic OPF) | FAIL | 194 | 123 | Sequential loop demo (not native stochastic) |
| A-9 (SCOPF) | FAIL | 235 | 120 | PTDF/LODF computation + API exploration |
| A-10 (Lossy DC OPF) | FAIL | 176 | 93 | Lossless vs AC comparison |
| A-11 (Dist. slack OPF) | FAIL | 180 | 107 | Parameter inspection + PF demo |

**Column definitions:**
- **Total Lines:** `wc -l` of the test script (includes docstrings, comments, blank lines).
- **Code Lines:** Non-blank, non-comment, non-docstring lines.

**Summary statistics (passing tests only: A-1, A-2, A-3, A-4, A-7):**

| Metric | Value |
|--------|-------|
| Mean total lines | 147 |
| Mean code lines | 92 |
| Min code lines | 53 (A-1 DCPF) |
| Max code lines | 142 (A-7 contingency) |

**Observations on code volume:**

1. **Core power flow (A-1, A-2):** Very concise. The pandapower API is terse for basic PF:
   `from_mpc()`, `rundcpp()`/`runpp()`, then read `res_bus`/`res_line` DataFrames. The
   boilerplate is dominated by result extraction, not model setup.

2. **OPF (A-3):** Moderate. Cost curve setup adds ~10 lines. LMP extraction is straightforward
   (`net.res_bus["lam_p"]`). The solver lock-in to PYPOWER interior point adds documentation
   but not code.

3. **Contingency sweep (A-7):** Highest LOC among passing tests (142 code lines). Graph
   distance computation and combinatorial enumeration require explicit coding. pandapower
   provides the graph bridge (`create_nxgraph`) but not a high-level contingency API that
   handles pruning and enumeration.

4. **Failed tests are verbose by design:** The FAIL scripts (A-5, A-6, A-8, A-9, A-10, A-11)
   contain significant documentation and capability assessment code. The code volume for these
   reflects diagnostic effort, not implementation complexity.

**Minimal "happy path" LOC for key operations:**

| Operation | Minimal LOC |
|-----------|-------------|
| Load MATPOWER case | 2 (import + `from_mpc()`) |
| Run DCPF | 1 (`pp.rundcpp(net)`) |
| Run ACPF | 1 (`pp.runpp(net)`) |
| Run DC OPF | 1 (`pp.rundcopp(net)`) |
| Check convergence | 1 (`net["converged"]` or `net["OPF_converged"]`) |
| Extract bus results | 1 (`net.res_bus`) |
| Extract line results | 1 (`net.res_line`) |
| Extract LMPs | 1 (`net.res_bus["lam_p"]`) |
| Get topology graph | 2 (import + `create_nxgraph(net)`) |

**Test script paths:**

All scripts at `evaluations/pandapower/tests/expressiveness/test_a*.py`.

## Implications

pandapower has low code volume for its core capabilities (power flow, basic OPF). The API is
concise and pandas-native, minimizing boilerplate. Higher LOC in A-7 (contingency) reflects
the absence of a high-level contingency analysis API with built-in graph-distance pruning,
requiring the user to code enumeration logic manually. Cross-tool LOC comparison (to be
assembled across all tools) will provide relative context.
