---
probe_id: probe-021
tool: powersimulations
source_test: A-4
probe_type: claim_verification
classification: claim_debunked
reason: "Dispatch values from read_variables() are in MW, not pu; they match Pmax when compared in the same units. The A-4 evaluation mislabeled MW values as pu, creating a false appearance of ~100x mismatch."
solver_version: "HiGHS v1.21.1"
solver_version_match: true
timeout_seconds: 600
wall_clock_seconds: 65
timestamp: "2026-03-09T00:00:00Z"
---

# Probe 021: PSI dispatch values ~100x larger than component limits

## Original Claim

From `evaluations/powersimulations/results/expressiveness/A-4_ac_feasibility.md` (v4 eval):

> **Dispatch values (system-base pu on 100 MVA base):**
>
> | Generator | Dispatch (pu) | Dispatch (MW) | Pmax (pu) |
> |-----------|--------------|---------------|-----------|
> | gen-1 | 660.85 | 66,085 | 10.40 |
>
> "The dispatch values returned by PSI are ~100x larger than Pmax."

The A-4 evaluation also concluded: "the user must understand PSI's internal unit conventions
to correctly interpret optimization results" and that ACPF could not converge because
"the dispatch values (660 pu = 66 GW per generator) are physically unrealistic."

## Probe Methodology

Wrote a Julia script that:
1. Loads IEEE 39-bus via `System("case39.m")`
2. Adds time series boilerplate, builds and solves DCOPF with PTDFPowerModel + HiGHS
3. Extracts dispatch values via **both** the `read_variables()` API and direct JuMP variable access
4. Compares dispatch values to component Pmax in both pu and MW

Scripts: `probe-021_script.jl` and `probe-021b_script.jl`

## Probe Results

Raw output from probe-021b:

```
ActivePowerVariable__ThermalStandard from read_variables():
1x11 DataFrame
 Row | DateTime             gen-2    gen-9    gen-1    ...
     | DateTime             Float64  Float64  Float64  ...
     | 2024-01-01T00:00:00  646.0    660.845  660.846  ...

--- Comparison ---
Gen       API_val        JuMP_val       Pmax_pu     Pmax_MW     API/Pmax_pu
----------------------------------------------------------------------------
gen-2     646.0          6.46           6.46        646.0       100.0
gen-9     660.8451       6.6085         8.65        865.0       76.4
gen-1     660.8461       6.6085         10.4        1040.0      63.54
gen-3     660.8431       6.6084         7.25        725.0       91.15
gen-7     580.0          5.8            5.8         580.0       100.0
gen-6     660.8416       6.6084         6.87        687.0       96.19
gen-8     564.0          5.64           5.64        564.0       100.0
gen-5     508.0          5.08           5.08        508.0       100.0
gen-4     652.0          6.52           6.52        652.0       100.0
gen-10    660.8541       6.6085         11.0        1100.0      60.08
```

Key observations:
- **JuMP internal variables** are in system-base pu (gen-2 = 6.46)
- **`read_variables()` API** returns values in MW (gen-2 = 646.0)
- **`get_active_power_limits()`** returns limits in system-base pu (gen-2 Pmax = 6.46)
- The API dispatch values equal JuMP values times base_power (100): `6.46 * 100 = 646.0`
- All generators at their limit (gen-2, gen-5, gen-7, gen-8, gen-4) have API dispatch
  exactly equal to Pmax_MW: 646/646, 508/508, 580/580, 564/564, 652/652

## Analysis

The A-4 evaluation's claim of a "~100x mismatch" is a **unit labeling error in the
evaluation itself**, not a PSI behavior issue:

1. The A-4 table labels dispatch values as "Dispatch (pu)" with values like 660.85.
   These are actually in **MW** (as the `read_variables()` API returns them).

2. The A-4 table labels Pmax as "Pmax (pu)" with values like 10.40. These **are** in
   pu (system-base), as returned by `get_active_power_limits()`.

3. When both are compared in MW: dispatch 660.85 MW vs Pmax 1040 MW (= 10.40 * 100).
   The ratio is 0.635 -- gen-1 is dispatched at 63.5% of its capacity. Entirely
   reasonable.

4. The A-3 evaluation (same tool, same test) correctly reports the same values as MW:
   "gen-1: Dispatch (MW) = 660.85, Pmax (MW) = 1040.0" -- no mismatch claimed.

5. Interestingly, the `read_variables()` API does convert to MW while
   `get_active_power_limits()` returns pu. This is a real API inconsistency (one auto-
   converts, the other doesn't), but it does NOT mean the dispatch exceeds limits.

**The ACPF non-convergence in A-4** was caused by applying MW dispatch values (660.85)
directly via `set_active_power!(gen, value)` to a system in pu. The setter interprets
the value as pu, so gen-1 was set to 660.85 pu = 66,085 MW -- indeed physically
unrealistic. This is a user error in the evaluation script (unit-unaware transfer),
not a PSI defect.

## Classification Rationale

Classified as **claim_debunked** because:

- The claim that "PSI dispatch values are ~100x larger than component limits" is incorrect.
  Dispatch values from `read_variables()` are in MW and are within component limits when
  compared in the same unit system.
- The ~100x factor is simply the base_power (100 MVA) conversion factor between pu and MW.
- The A-3 evaluation of the same DCOPF on the same network correctly identified the
  dispatch as MW and showed no mismatch.
- The A-4 evaluation mislabeled MW values as "pu", creating the false appearance of
  limit violations.
- The ACPF non-convergence was caused by unit-unaware dispatch transfer, not by a solver
  or API defect in PSI.
