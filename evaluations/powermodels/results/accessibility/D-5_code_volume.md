---
test_id: D-5
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: bfe66395
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
timestamp: 2026-03-24T18:00:00Z
---

# D-5: Code Volume

## Result: INFORMATIONAL

## Finding

Suite A test scripts range from 176 to 663 NBNCL (non-blank, non-comment lines). Scripts for
natively supported capabilities (A-1 DCPF, A-2 ACPF, A-3 DCOPF, A-7 contingency) average
~300 NBNCL. Scripts requiring user-assembled JuMP formulations (A-5 SCUC, A-9 SCOPF, A-12
storage) exceed 450 NBNCL and reach 663 for the most complex test.

## Evidence

### Counting Method

Non-blank, non-comment lines (NBNCL): excluded lines that are entirely whitespace or whose
first non-whitespace character is `#` (Julia comment). Counted via `grep -cvP '^\s*$|^\s*#'`.
Verified on 2026-03-24 against current file contents.

Scripts located in `evaluations/powermodels/tests/expressiveness/`.

### Suite A -- TINY Primary Scripts

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| A-1 DCPF | test_a1_dcpf_tiny.jl | 250 | 187 |
| A-2 ACPF | test_a2_acpf_tiny.jl | 423 | 322 |
| A-3 DCOPF | test_a3_dcopf_tiny.jl | 394 | 314 |
| A-4 AC Feasibility | test_a4_ac_feasibility_check_tiny.jl | 455 | 342 |
| A-5 SCUC | test_a5_scuc_tiny.jl | 600 | 467 |
| A-6 SCED | test_a6_sced_tiny.jl | 608 | 473 |
| A-7 Contingency Sweep | test_a7_contingency_sweep_tiny.jl | 473 | 363 |
| A-8 Stochastic Timeseries | test_a8_stochastic_timeseries_tiny.jl | 524 | 418 |
| A-9 SCOPF | test_a9_scopf_tiny.jl | 870 | 654 |
| A-10 Lossy DCOPF/LMP | test_a10_lossy_dcopf_lmp_decomposition_tiny.jl | 495 | 380 |
| A-11 Distributed Slack | test_a11_distributed_slack_opf_tiny.jl | 265 | 176 |
| A-12 Multi-Period Storage | test_a12_multiperiod_dcopf_storage_tiny.jl | 892 | 663 |

### Suite A -- Scale Variant Scripts

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| A-1 DCPF | test_a1_dcpf_medium.jl | 280 | 234 |
| A-2 ACPF | test_a2_acpf_medium.jl | 379 | 322 |
| A-3 DCOPF | test_a3_dcopf_medium.jl | 308 | 251 |
| A-4 AC Feasibility | test_a4_ac_feasibility_check_medium.jl | 547 | 423 |
| A-7 Contingency Sweep | test_a7_contingency_sweep_medium.jl | 546 | 430 |
| A-9 SCOPF | test_a9_scopf_small.jl | 419 | 364 |
| A-10 Lossy DCOPF | test_a10_lossy_dcopf_lmp_decomposition_small.jl | 318 | 277 |

### Statistical Summary (TINY primary scripts only)

| Metric | Value |
|--------|-------|
| Tests with scripts | 12 of 12 |
| Mean NBNCL | 397 |
| Median NBNCL | 381 |
| Min NBNCL | 176 (A-11 distributed slack) |
| Max NBNCL | 663 (A-12 multi-period storage) |
| Std dev NBNCL | 139 |

### LOC Drivers

**1. Manual post-processing (10-25 lines per script).** Branch flows not in result dict for
`compute_dc_pf`/`compute_ac_pf`. Each script computing branch flows adds manual DC formula
or `calc_branch_flow_ac` two-step.

**2. Result extraction boilerplate (15-30 lines per script).** PowerModels returns nested
`Dict{String,Any}` with string keys. Typed extraction requires explicit iteration.

**3. Per-unit / MW conversion (5-10 lines per script).** All results in per-unit; explicit
`* baseMVA` for human-readable output.

**4. User-assembled formulations (100-300 lines for A-5, A-8, A-9, A-11, A-12).** Tests
requiring absent capabilities contain large JuMP code blocks. A-5 SCUC: ~250 lines MILP.
A-9 SCOPF: LODF + security constraints. A-12: multi-period + storage + cyclic SoC.

**5. Validation and reporting (20-40% of each script).** Evaluation-specific pass/fail
assertions, metric reporting, diagnostics. Minimum working code is ~60-70% of NBNCL.

### Minimum Working Code Estimates

| Test | NBNCL | Est. Min LOC | Notes |
|------|-------|-------------|-------|
| A-1 DCPF | 187 | ~40 | parse + solve + branch flow manual |
| A-2 ACPF | 322 | ~50 | parse + solve + calc_branch_flow_ac |
| A-3 DCOPF | 314 | ~60 | parse + cost setup + solve + LMP extraction |
| A-4 AC Feasibility | 342 | ~80 | DCOPF + ACPF + branch flow + violation check |
| A-5 SCUC | 467 | ~250 | Full JuMP MILP assembly (no native API) |
| A-6 SCED | 473 | ~150 | Multi-period data + ramp constraints |
| A-7 Contingency | 363 | ~60 | deepcopy loop + compute_dc_pf |
| A-8 Stochastic | 418 | ~120 | Scenario generation + solve loop |
| A-9 SCOPF | 654 | ~200 | LODF + security constraint injection |
| A-10 Lossy DCOPF | 380 | ~80 | DCPLLPowerModel + dual extraction |
| A-11 Distributed Slack | 176 | ~100 | PTDF + custom JuMP OPF |
| A-12 Multi-Period Storage | 663 | ~250 | Storage data model + mn_opf_strg + cyclic SoC |

## Implications

For natively supported operations (A-1, A-2, A-3, A-7), minimum working code is 40-80 lines --
reasonable for a Julia power systems library. For user-assembled formulations (A-5, A-6, A-9,
A-11, A-12), code exceeds 100-250 lines, reflecting the tool's expressiveness boundary.
PowerModels is a steady-state OPF library; UC, stochastic, and multi-period capabilities
require significant user infrastructure. The SCOPF test (654 NBNCL) is disproportionately large
because it implements LODF from scratch.
