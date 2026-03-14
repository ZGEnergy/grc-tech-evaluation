---
test_id: D-5
tool: pypsa
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: db465194
---

# D-5: Code Volume

## Summary

Suite A test scripts for PyPSA range from 156 to 541 total lines (111 to 415 code
lines excluding blanks and comments). Simpler analyses (DCPF) require the least code;
multi-period storage optimization (A-12) requires the most.

## LOC Table (TINY network variants)

| Test ID | Test Name | Total Lines | Code Lines | Notes |
|---------|-----------|-------------|------------|-------|
| A-1 | DCPF | 156 | 111 | Simplest test. Load network, call `n.lpf()`, validate flows. |
| A-2 | ACPF | 257 | 187 | NR power flow with convergence validation. Requires separate loader path (no DC susceptance patch). |
| A-3 | DCOPF | 288 | 219 | OPF with shadow price extraction via linopy model constraints. |
| A-4 | AC Feasibility | 346 | 265 | Two-stage: DC OPF dispatch then AC PF feasibility check. Requires dual loader paths. |
| A-5 | SCUC | 395 | 297 | Unit commitment with modified Tiny recipe (differentiated costs, temporal params). |
| A-6 | SCED | 453 | 349 | Two-stage UC then ED. Significant boilerplate for commitment schedule fixation. |
| A-9 | SCOPF | 335 | 249 | Security-constrained OPF. Limited to line-only contingencies. |
| A-10 | Lossy DCOPF with LMP | 332 | 258 | Loss factors and LMP decomposition. |
| A-11 | Distributed Slack OPF | 326 | 259 | AC PF with distributed slack after DC OPF. |
| A-12 | Multi-period Storage | 541 | 415 | 24-hour DCOPF with BESS. Most complex test. |

## Analysis

**Mean code lines:** 261 (across 10 TINY test scripts)
**Median code lines:** 259
**Range:** 111 (A-1) to 415 (A-12)

The LOC counts include test infrastructure (imports, assertions, result logging)
that is consistent across tests. The incremental code specific to each power system
analysis is lower than the totals suggest.

**Lowest-friction tests (under 200 code lines):** A-1 (DCPF) and A-2 (ACPF). These
tests use PyPSA's core API (`n.lpf()`, `n.pf()`) with minimal setup.

**Highest-friction tests (over 300 code lines):** A-6 (SCED) and A-12 (multi-period
storage). A-6 requires manual commitment schedule fixation (~20 lines of boilerplate
that could be a single API call). A-12 is inherently complex due to 24-hour temporal
resolution, storage parametrization, and modified cost recipe loading.

## Observations Relevant to Code Volume

- **api-friction A-6:** The lack of a `fix_commitment()` API adds ~20 lines to A-6.
- **api-friction A-3:** Shadow price extraction via linopy adds ~10 lines vs. if
  prices were auto-populated on the network object.
- **api-friction A-12 (positive):** PyPSA's `StorageUnit` with native
  `cyclic_state_of_charge` support reduces storage modeling code compared to tools
  requiring manual constraint construction.
- **api-friction B-5 (positive):** DataFrame-native results eliminate the need for
  result extraction boilerplate.
