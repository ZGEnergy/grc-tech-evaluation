---
test_id: D-5
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: db465194
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
timestamp: 2026-03-24T18:30:00Z
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

Suite A test scripts for PyPSA (TINY tier) range from 156 to 558 total lines
(111 to 436 code lines excluding blanks and comments). Simpler analyses (DCPF)
require the least code; two-stage UC/ED (SCED) requires the most.

## Evidence

### LOC Table (TINY network test scripts)

| Test ID | Test Name | Total Lines | Code Lines | Script Path |
|---------|-----------|:-----------:|:----------:|-------------|
| A-1 | DCPF | 156 | 111 | `tests/expressiveness/test_a1_dcpf_tiny.py` |
| A-2 | ACPF | 257 | 187 | `tests/expressiveness/test_a2_acpf_tiny.py` |
| A-3 | DCOPF | 288 | 219 | `tests/expressiveness/test_a3_dcopf_tiny.py` |
| A-4 | AC Feasibility | 346 | 265 | `tests/expressiveness/test_a4_ac_feasibility_tiny.py` |
| A-5 | SCUC | 467 | 350 | `tests/expressiveness/test_a5_scuc_tiny.py` |
| A-6 | SCED | 558 | 436 | `tests/expressiveness/test_a6_sced_tiny.py` |
| A-9 | SCOPF | 335 | 249 | `tests/expressiveness/test_a9_scopf_tiny.py` |
| A-10 | Lossy DCOPF with LMP | 332 | 258 | `tests/expressiveness/test_a10_lossy_dcopf_lmp_tiny.py` |
| A-11 | Distributed Slack OPF | 326 | 259 | `tests/expressiveness/test_a11_distributed_slack_opf_tiny.py` |
| A-12 | Multi-period Storage | 541 | 415 | `tests/expressiveness/test_a12_multiperiod_dcopf_storage_tiny.py` |

### Statistical Summary

- **Mean code lines:** 275 (across 10 TINY test scripts)
- **Median code lines:** 259
- **Range:** 111 (A-1 DCPF) to 436 (A-6 SCED)
- **Standard deviation:** 94

### Grade-Tier Comparison (TINY vs SMALL/MEDIUM where available)

| Test | TINY (code) | SMALL (code) | MEDIUM (code) |
|------|:-----------:|:------------:|:-------------:|
| A-1 | 111 | -- | 137 |
| A-2 | 187 | -- | 203 |
| A-3 | 219 | -- | 227 |
| A-4 | 265 | -- | 229 |
| A-10 | 258 | -- | 231 |
| A-11 | 259 | 242 | -- |

TINY scripts are generally slightly larger than MEDIUM equivalents because they
include more detailed validation assertions and Modified Tiny recipe loading.

### Analysis

**Lowest-friction tests (under 200 code lines):** A-1 (DCPF, 111) and A-2 (ACPF,
187). These use PyPSA's core API (`n.lpf()`, `n.pf()`) with minimal setup.

**Highest-friction tests (over 350 code lines):** A-5 (SCUC, 350), A-6 (SCED, 436),
and A-12 (multi-period storage, 415).

- A-6 is the highest because the two-stage UC-then-ED workflow requires manual
  commitment schedule fixation (~20 lines of boilerplate). A `fix_commitment()`
  API would reduce this. [api-friction A-6](../observations/api-friction-expressiveness-A-6_sced.md)
- A-12 is inherently complex due to 24-hour temporal resolution, storage
  parametrization, and Modified Tiny cost recipe loading.
- A-5 includes detailed temporal parameter loading and UC variable validation.

**LOC counts include** test infrastructure (imports, assertions, result logging,
Modified Tiny recipe loading) that is consistent across tests. The incremental
code specific to each power system analysis is lower than the totals suggest.

### Observations Relevant to Code Volume

- **[api-friction A-6](../observations/api-friction-expressiveness-A-6_sced.md):**
  Lack of `fix_commitment()` adds ~20 lines to A-6.
- **[api-friction A-3](../observations/api-friction-expressiveness-A-3_dcopf.md):**
  Shadow price extraction via linopy adds ~10 lines vs auto-populated prices.
- **[api-friction A-12 (positive)](../observations/api-friction-expressiveness-A-12_multiperiod_dcopf_storage.md):**
  Native `StorageUnit` with `cyclic_state_of_charge` reduces storage code vs
  tools requiring manual constraint construction.

## Implications

PyPSA's code volume is moderate. Simple analyses (DCPF, ACPF) require minimal
code, consistent with a well-designed high-level API. Complex multi-stage
workflows (SCED) and multi-period analyses (A-12) show expected LOC growth.
The primary code volume driver beyond problem complexity is test infrastructure
boilerplate, not PyPSA API verbosity.
