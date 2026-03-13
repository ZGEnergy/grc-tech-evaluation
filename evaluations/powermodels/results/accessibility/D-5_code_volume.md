---
test_id: D-5
tool: powermodels
dimension: accessibility
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "bfe66395"
---

# D-5: Code Volume

## Counting Method

Non-blank, non-comment lines (NBNCL). A line is excluded if it is entirely whitespace
or if its first non-whitespace character is `#` (Julia line comment). Multi-line `#= ... =#`
block comments are excluded at the block level (counted as comment lines). Total lines
(including blanks and comments) are shown for reference.

Scripts are in `evaluations/powermodels/tests/expressiveness/`.

Where two scripts exist for a test (e.g., `test_a1_dcpf.jl` and `test_a1_dcpf_tiny.jl`),
both are listed. The `_tiny` variant is the primary evaluation script using the Modified Tiny
dataset; the base variant operates on the SMALL/MEDIUM network or base case39.

## Suite A — Expressiveness Tests

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| A-1 | test_a1_dcpf.jl | 138 | 106 |
| A-1 | test_a1_dcpf_tiny.jl | 226 | 163 |
| A-2 | test_a2_acpf.jl | 144 | 112 |
| A-2 | test_a2_acpf_tiny.jl | 302 | 217 |
| A-3 | test_a3_dcopf.jl | 123 | 94 |
| A-3 | test_a3_dcopf_tiny.jl | 333 | 259 |
| A-4 | test_a4_ac_feasibility_check_tiny.jl | 423 | 310 |
| A-5 | test_a5_scuc.jl | 295 | 220 |
| A-7 | test_a7_contingency_sweep_tiny.jl | 436 | 326 |

Note: Tests A-6, A-8, A-9, A-10, A-11, A-12 did not have dedicated expressiveness scripts
in `tests/expressiveness/` at the time of this audit. These tests were either not yet
implemented, implemented in other test directories, or rolled into higher-level test scripts.

## Suite B — Extensibility Tests

Included for completeness (not strictly Suite A, but written by the same code evaluators).
Scripts are in `evaluations/powermodels/tests/extensibility/`.

| Test | Script | Total Lines | NBNCL |
|------|--------|-------------|-------|
| B-1 | test_b1_custom_constraints.jl | 211 | 153 |
| B-1 | test_b1_custom_constraints_tiny.jl | 245 | 184 |
| B-2 | test_b2_graph_access.jl | 178 | 137 |
| B-2 | test_b2_graph_access_tiny.jl | 220 | 164 |
| B-3 | test_b3_contingency_loop.jl | 228 | 180 |
| B-3 | test_b3_contingency_loop_tiny.jl | 249 | 198 |
| B-4 | test_b4_stochastic_wrapping.jl | 227 | 162 |
| B-4 | test_b4_stochastic_wrapping_small.jl | 196 | 154 |
| B-4 | test_b4_stochastic_scenario_wrapping_tiny.jl | 237 | 178 |
| B-5 | test_b5_interoperability.jl | 128 | 97 |
| B-5 | test_b5_interoperability_tiny.jl | 160 | 119 |
| B-7 | test_b7_ac_feasibility_extension.jl | 115 | 92 |
| B-7 | test_b7_ac_feasibility_extension_tiny.jl | 223 | 152 |
| B-8 | test_b8_reference_bus_config.jl | 372 | 301 |
| B-8 | test_b8_reference_bus_config_small.jl | 308 | 248 |
| B-8 | test_b8_reference_bus_configuration_tiny.jl | 283 | 209 |
| B-9 | test_b9_ptdf_extraction.jl | 196 | 142 |
| B-9 | test_b9_ptdf_extraction_tiny.jl | 266 | 194 |

## Observations

**Script verbosity is moderate-to-high** for a Julia power-system library. Several factors
drive the line counts:

1. **Manual post-processing** — branch flows are not in the result dict for `compute_dc_pf`
   or `compute_ac_pf`. Each script that reports branch flows adds 10–15 lines of manual
   computation (DC formula or `calc_branch_flow_ac` two-step).

2. **Result extraction boilerplate** — PowerModels returns nested `Dict{String,Any}` with
   string keys. Converting to typed arrays or tables for validation requires explicit iteration
   loops. A typical branch flow extraction loop is 5–8 lines.

3. **Per-unit / MW conversion** — every result that needs real-world units requires an explicit
   multiply by `data["baseMVA"]` (100.0 for case39). This is correct and necessary but adds
   lines.

4. **Comprehensive validation** — scripts include pass/fail assertion logic and result
   reporting, which adds ~20–40% overhead beyond the minimum working code.

The A-4 script (423 total / 310 NBNCL) is the longest expressiveness test and reflects the
AC feasibility workflow's complexity: DCOPF solve, voltage initialization from DC solution,
ACPF solve, branch flow post-processing, and feasibility verification across all branches.

The A-7 contingency sweep (436 total / 326 NBNCL) is similarly long due to the loop logic,
island detection, and per-contingency result collection.

**Comparison context:** For a Julia library where the core solve is a single function call,
these line counts suggest the data manipulation overhead (pre-processing network data,
post-processing results) dominates over the optimization logic itself.

## Pass/Fail Rationale

**informational**: No pass/fail threshold is specified for D-5. Line counts are provided for
cross-tool comparison. The high per-script verbosity is a moderate accessibility concern —
it reflects API friction (missing branch flows, manual unit conversion, dict-based result
access) rather than problem complexity.
