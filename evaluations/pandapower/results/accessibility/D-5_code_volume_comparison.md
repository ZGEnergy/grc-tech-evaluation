---
test_id: D-5
tool: pandapower
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T18:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "012a0a18"
---

# D-5: Code Volume Comparison

## Method

Counted lines of code (LOC) for each Suite A test script in
`evaluations/pandapower/tests/expressiveness/`. Two metrics reported:
- **Total lines:** All lines including blanks and comments
- **Code lines:** Non-blank, non-comment lines only

## Results

| Test | File | Total Lines | Code Lines |
|------|------|-------------|------------|
| A-1 (DCPF) | test_a1_dcpf.py | 138 | 94 |
| A-2 (ACPF) | test_a2_acpf.py | 190 | 143 |
| A-3 (DCOPF) | test_a3_dcopf.py | 309 | 220 |
| A-4 (AC Feasibility) | test_a4_ac_feasibility_check.py | 289 | 204 |
| A-5 (SCUC) | test_a5_scuc.py | 80 | 66 |
| A-6 (SCED) | test_a6_sced.py | 73 | 60 |
| A-9 (SCOPF) | test_a9_scopf.py | 257 | 192 |
| A-10 (Lossy DCOPF) | test_a10_lossy_dcopf_lmp_decomposition.py | 246 | 177 |
| A-11 (Dist. Slack OPF) | test_a11_distributed_slack_opf.py | 338 | 260 |
| A-12 (Multi-period Storage) | test_a12_multiperiod_dcopf_storage.py | 290 | 221 |

**Total across all Suite A tests:** 2,210 total lines / 1,637 code lines

## Analysis

### Tests with Low Code Volume (< 100 code lines)

- **A-5 (80 total / 66 code):** SCUC is not supported by pandapower. The script is
  short because it documents the limitation and exits early.
- **A-6 (73 total / 60 code):** SCED is also unsupported. Same pattern as A-5.
- **A-1 (138 total / 94 code):** DCPF is a single function call (`rundcpp`). The bulk
  of the code is result extraction and validation, not model setup.

### Tests with High Code Volume (> 200 code lines)

- **A-11 (338 total / 260 code):** Distributed slack OPF required extensive workaround
  code because `distributed_slack` has no effect on OPF functions. The script tests
  the parameter, discovers it does not work, and documents the limitation.
- **A-3 (309 total / 220 code):** DCOPF with Modified Tiny data requires manual cost
  function creation and bus index remapping (MATPOWER 1-indexed to pandapower 0-indexed).
- **A-12 (290 total / 221 code):** Multi-period DCOPF with storage requires workaround
  code for inter-temporal coupling that pandapower does not natively support.

### Code Volume Drivers

1. **Boilerplate overhead:** Each test includes ~40-50 lines of standard structure
   (imports, result dict initialization, error handling, JSON output). This is test
   harness code, not tool-specific.
2. **Workaround code:** Tests for unsupported features (A-5, A-6, A-9, A-10, A-11, A-12)
   contain either early-exit documentation or elaborate workaround attempts, inflating
   LOC beyond what the core feature would require.
3. **Result extraction:** pandapower's DataFrame-based results are concise to access
   (e.g., `net.res_bus["va_degree"]`), but validation and logging of results adds lines.

### Core API Calls vs Total LOC

For the tests that pandapower natively supports, the actual API surface is compact:

| Operation | API Calls Required |
|-----------|--------------------|
| Load network | 1 (`load_pandapower()` / `from_mpc()`) |
| Run DCPF | 1 (`rundcpp()`) |
| Run ACPF | 1 (`runpp()`) |
| Run DC OPF | 1 (`rundcopp()`) + N cost creation calls |
| Access results | Direct DataFrame access (`net.res_bus`, etc.) |

The ratio of boilerplate + validation code to actual pandapower API calls is high,
indicating that the tool's API is concise for supported operations.
