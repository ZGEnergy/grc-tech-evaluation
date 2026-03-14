---
test_id: D-5
tool: powermodels
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T23:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "d085fcb6"
---

# D-5: Code Volume

## Counting Method

Non-blank, non-comment lines (NBNCL). A line is excluded if it is entirely whitespace
or if its first non-whitespace character is `#` (Julia line comment). Total lines
(including blanks and comments) are shown for reference.

Scripts are in `evaluations/powermodels/tests/expressiveness/`.

Where two scripts exist for a test (e.g., `_tiny` and `_medium` or `_small`), both are
listed. The `_tiny` variant is the primary functional evaluation script on the Modified Tiny
(IEEE 39-bus) network. Scale variants (`_medium`, `_small`) operate on larger networks
and include additional diagnostic/timing instrumentation.

## Suite A -- Expressiveness Tests (TINY primary scripts)

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| A-1 DCPF | test_a1_dcpf_tiny.jl | 250 | 187 |
| A-2 ACPF | test_a2_acpf_tiny.jl | 346 | 261 |
| A-3 DCOPF | test_a3_dcopf_tiny.jl | 354 | 280 |
| A-4 AC Feasibility | test_a4_ac_feasibility_check_tiny.jl | 455 | 342 |
| A-5 SCUC | test_a5_scuc_tiny.jl | 576 | 443 |
| A-6 SCED | test_a6_sced_tiny.jl | 501 | 384 |
| A-7 Contingency Sweep | test_a7_contingency_sweep_tiny.jl | 473 | 363 |
| A-8 Stochastic Timeseries | test_a8_stochastic_timeseries_tiny.jl | 524 | 418 |
| A-9 SCOPF | test_a9_scopf_tiny.jl | 870 | 654 |
| A-10 Lossy DCOPF/LMP | test_a10_lossy_dcopf_lmp_decomposition_tiny.jl | 494 | 379 |
| A-11 Distributed Slack | test_a11_distributed_slack_opf_tiny.jl | 265 | 176 |
| A-12 Multi-Period Storage | test_a12_multiperiod_dcopf_storage_tiny.jl | 892 | 663 |

## Suite A -- Scale Variant Scripts

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| A-1 DCPF | test_a1_dcpf_medium.jl | 280 | 234 |
| A-2 ACPF | test_a2_acpf_medium.jl | 379 | 322 |
| A-3 DCOPF | test_a3_dcopf_medium.jl | 308 | 251 |
| A-4 AC Feasibility | test_a4_ac_feasibility_check_medium.jl | 547 | 423 |
| A-7 Contingency Sweep | test_a7_contingency_sweep_medium.jl | 546 | 430 |
| A-9 SCOPF | test_a9_scopf_small.jl | 419 | 364 |
| A-10 Lossy DCOPF | test_a10_lossy_dcopf_lmp_decomposition_small.jl | 318 | 277 |

## Statistical Summary (TINY primary scripts only)

| Metric | Value |
|--------|-------|
| Tests with scripts | 12 of 12 |
| Mean NBNCL | 379 |
| Median NBNCL | 373 |
| Min NBNCL | 176 (A-11 distributed slack) |
| Max NBNCL | 663 (A-12 multi-period storage) |
| Std dev NBNCL | 143 |

## LOC Drivers

Script verbosity is moderate-to-high for a Julia power-system library. Several factors drive the line counts:

### 1. Manual post-processing (10-25 lines per script)

Branch flows are not in the result dict for `compute_dc_pf` or `compute_ac_pf`. Each script
that reports branch flows adds manual computation: the DC formula (`(va_from - va_to - shift)
/ (br_x * tap)`) or the two-step `update_data!` + `calc_branch_flow_ac` pattern.

### 2. Result extraction boilerplate (15-30 lines per script)

PowerModels returns nested `Dict{String,Any}` with string keys. Converting to typed arrays
or tables for validation requires explicit iteration loops. A typical extraction pattern:
```julia
for (id, bus) in result["solution"]["bus"]
    push!(bus_results, (id=parse(Int, id), va=bus["va"], vm=get(bus, "vm", NaN)))
end
```

### 3. Per-unit / MW conversion (5-10 lines per script)

Every result that needs real-world units requires an explicit multiply by `data["baseMVA"]`
(100.0 for case39). This is correct and necessary but adds lines. PowerModels operates
entirely in per-unit internally with consistent convention (positive observation from
unit-mismatch A-4), so the conversion is straightforward but repetitive.

### 4. User-assembled formulations (100-300 lines for A-5, A-8, A-9, A-11, A-12)

Tests requiring capabilities absent from PowerModels (SCUC, stochastic OPF, SCOPF, distributed
slack) contain large blocks of user-assembled JuMP code. A-5 SCUC (443 NBNCL) includes ~250
lines of custom MILP formulation. A-9 SCOPF (654 NBNCL) includes LODF computation and manual
security constraint injection. A-12 storage (663 NBNCL) includes multi-period data assembly,
cyclic SoC constraints, and BESS arbitrage validation. These line counts reflect the tool's
expressiveness gaps more than API verbosity.

### 5. Validation and reporting overhead (20-40% of each script)

Scripts include pass/fail assertion logic, metric reporting, and diagnostic output. This
overhead is evaluation-specific and would not be present in production code. The "minimum
working code" for each test is roughly 60-70% of the NBNCL count.

## Minimum Working Code Estimates

Stripping validation, reporting, and diagnostic output to estimate the minimum LOC needed
to achieve each test's functional goal:

| Test | NBNCL | Est. Min LOC | Notes |
|------|-------|-------------|-------|
| A-1 DCPF | 187 | ~40 | parse + solve + branch flow manual |
| A-2 ACPF | 261 | ~50 | parse + solve + calc_branch_flow_ac |
| A-3 DCOPF | 280 | ~60 | parse + cost setup + solve + LMP extraction |
| A-4 AC Feasibility | 342 | ~80 | DCOPF + ACPF + branch flow + violation check |
| A-5 SCUC | 443 | ~250 | Full JuMP MILP assembly (no native API) |
| A-6 SCED | 384 | ~150 | Multi-period data + ramp constraints |
| A-7 Contingency | 363 | ~60 | deepcopy loop + compute_dc_pf |
| A-8 Stochastic | 418 | ~120 | Scenario generation + solve loop |
| A-9 SCOPF | 654 | ~200 | LODF + security constraint injection |
| A-10 Lossy DCOPF | 379 | ~80 | DCPLLPowerModel + dual extraction |
| A-11 Distributed Slack | 176 | ~100 | PTDF computation + custom JuMP OPF |
| A-12 Multi-Period Storage | 663 | ~250 | Storage data model + mn_opf_strg + cyclic SoC |

## Observations

For tests where PowerModels has native API support (A-1, A-2, A-3, A-7), the minimum working
code is 40-80 lines. This is reasonable for a Julia library and compares favorably with
equivalent MATPOWER/Octave code for the same tasks.

For tests requiring user-assembled formulations (A-5, A-6, A-9, A-11, A-12), the minimum
code exceeds 100 lines and in some cases reaches 250 lines. This reflects the tool's design
boundary: PowerModels is a steady-state OPF library, not a production market simulation
framework. Users needing UC, stochastic, or multi-period capabilities must build significant
infrastructure.

The SCOPF test (A-9, 654 NBNCL) is disproportionately large because it implements LODF
computation from scratch (no `calc_lodf_matrix` in PowerModels), security constraint
formulation, and the `instantiate_model` + constraint injection pattern. This test effectively
validates the extensibility architecture more than it tests native expressiveness.

## Pass/Fail Rationale

**informational**: No pass/fail threshold is specified for D-5. Line counts are provided for
cross-tool comparison. The high per-script verbosity for non-native problem types (A-5, A-9,
A-12) is a significant accessibility concern reflecting missing built-in capabilities. For
native problem types, the code volume is moderate and dominated by result extraction
boilerplate rather than core logic complexity.
