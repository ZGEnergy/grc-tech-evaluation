---
test_id: D-5
tool: pandapower
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 012a0a18
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# D-5: Code Volume Comparison

## Result: INFORMATIONAL

## Finding

Suite A test scripts total 2,185 lines (1,624 code lines). Scripts for natively supported
features (A-1, A-2, A-3) are compact (107-259 code lines), while scripts for unsupported
features (A-5, A-6) are minimal stubs. The highest LOC tests (A-3, A-11, A-12) are inflated
by workaround code and bus index remapping.

## Evidence

### Method

Counted lines of code for each Suite A test script in
`evaluations/pandapower/tests/expressiveness/`. Measured inside devcontainer on 2026-03-24.
Two metrics: total lines (including blanks/comments) and code lines (non-blank, non-comment).

### Results

| Test | File | Total Lines | Code Lines |
|------|------|-------------|------------|
| A-1 (DCPF) | test_a1_dcpf.py | 134 | 107 |
| A-2 (ACPF) | test_a2_acpf.py | 181 | 152 |
| A-3 (DCOPF) | test_a3_dcopf.py | 305 | 259 |
| A-4 (AC Feasibility) | test_a4_ac_feasibility_check.py | 293 | 246 |
| A-5 (SCUC) | test_a5_scuc.py | 80 | 67 |
| A-6 (SCED) | test_a6_sced.py | 73 | 60 |
| A-9 (SCOPF) | test_a9_scopf.py | 257 | 214 |
| A-10 (Lossy DCOPF) | test_a10_lossy_dcopf_lmp_decomposition.py | 242 | 198 |
| A-11 (Dist. Slack OPF) | test_a11_distributed_slack_opf.py | 331 | 276 |
| A-12 (Multi-period Storage) | test_a12_multiperiod_dcopf_storage.py | 289 | 245 |
| **Total** | | **2,185** | **1,624** |

### Analysis

**Low code volume (< 100 code lines):**
- **A-5 (67 code lines):** SCUC is not supported. Script documents the limitation and exits.
- **A-6 (60 code lines):** SCED is also unsupported. Same pattern as A-5.

**Moderate code volume (100-200 code lines):**
- **A-1 (107 code lines):** DCPF is a single function call (`rundcpp`). Bulk of code is
  result extraction and validation.
- **A-2 (152 code lines):** ACPF via `runpp()`. Slightly larger due to convergence
  verification and voltage profile checks.

**High code volume (> 200 code lines):**
- **A-11 (276 code lines):** Distributed slack OPF required extensive workaround code because
  `distributed_slack` has no effect on OPF functions.
- **A-3 (259 code lines):** DCOPF with Modified Tiny data requires manual cost function
  creation and MATPOWER-to-pandapower bus index remapping (1-indexed to 0-indexed).
- **A-4 (246 code lines):** AC feasibility check chains two operations with manual dispatch
  transfer between them.
- **A-12 (245 code lines):** Multi-period DCOPF with storage requires workaround code for
  inter-temporal coupling.

### Core API Calls vs Total LOC

For natively supported operations, the API surface is compact:

| Operation | API Calls Required |
|-----------|--------------------|
| Load network | 1 (`pn.case9()` / `from_mpc()`) |
| Run DCPF | 1 (`rundcpp()`) |
| Run ACPF | 1 (`runpp()`) |
| Run DC OPF | 1 (`rundcopp()`) + N cost creation calls |
| Access results | Direct DataFrame access (`net.res_bus`, etc.) |

The ratio of boilerplate + validation code to actual pandapower API calls is high, indicating
that the tool's API is concise for supported operations but test harness overhead dominates
LOC counts.

## Implications

pandapower's API is concise for its core capabilities (power flow, basic OPF). High LOC counts
on advanced tests are driven by workaround code for unsupported features and bus index
remapping, not by API verbosity. The stub scripts for A-5 and A-6 clearly communicate
capability boundaries.
