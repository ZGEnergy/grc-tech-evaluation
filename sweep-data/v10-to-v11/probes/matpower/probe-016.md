---
probe_id: probe-016
tool: matpower
source_test: A-5
probe_type: claim_verification
classification: claim_debunked
reason: exitflag=-9 is GLP_ETMLIM (time limit, no feasible solution found) not GLP_EMIPGAP; the SCUC did not solve successfully in 1.1s
solver_version: MATPOWER 8.1 / MOST 1.3.1 / Octave 8.4.0 GLPK
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 0.48
timestamp: "2026-03-14T00:00:00Z"
---

# Probe 016: GLPK Exit-Flag Mapping Bug Claim Verification

## Original Claim

> "GLPK exit-flag mapping bug (GLP_EMIPGAP mapped to failure) causes A-5 SCUC to report failure
> when the actual SCUC solve succeeded (162K variables in 1.1s). This cascades into C-4 fail and
> blanks all 8 MEDIUM scalability tests."

The claim further asserts:
- GLPK found a feasible integer solution for case39 SCUC
- GLPK returned GLP_EMIPGAP (errnum=9) which MATPOWER mapped to exitflag=-9
- A one-line fix in exit flag mapping would recover the result

## Probe Methodology

1. Read A-5 and C-4 result files to understand the documented failure mode
2. Verified Octave 8.4.0 GLPK error code constants via built-in documentation
3. Read `miqps_glpk.m` (MATPOWER 8.1 `mp-opt-model/lib/miqps_glpk.m`) exit flag mapping code
4. Reproduced the A-5 SCUC scenario (case39, 24h) with the same parameters from the original test script
5. Captured raw `mdo.QP.exitflag`, `mdo.QP.output.errnum`, `mdo.QP.output.status`, and objective value

## Probe Results (Raw Output)

```
=== Probe 016: GLPK Exit Flag Mapping Verification ===

MATPOWER version: 8.1
Octave version: 8.4.0

--- Part 1: GLPK Error Code Constants ---
Octave GLPK error codes (from documentation):
  errnum=9  = GLP_ETMLIM  (time limit reached)
  errnum=14 = GLP_EMIPGAP (relative MIP gap tolerance reached)

Test 1: Simple MILP that solves to optimality
  errnum=0, status=5 (expected: errnum=0, status=5 for optimal)

--- Part 2: Reproduce A-5 SCUC (case39 TINY, 24-hour) ---
Loaded case39: 39 buses, 10 generators, 24 periods
Solving SCUC...

--- Part 3: Raw GLPK Output ---
mdo.QP.exitflag = -9
Solve time: 0.4785 s
mdo.QP.output.errnum = 9
mdo.QP.output.status = -1
Solution vector size: 3576 variables
Objective value: NA
Non-zero variables: 0

--- Part 4: Exit Flag Decoding ---
exitflag = -9
STATUS: MOST treated as FAILURE
errnum=9 = GLP_ETMLIM (TIME LIMIT) in Octave GLPK
NOTE: This is NOT GLP_EMIPGAP (errnum=14)

--- Part 5: Retry with mipgap=0 (force true optimality) ---
Solving with mipgap=0 (true optimality)...
exitflag = -9, solve_time = 0.5016 s
errnum=9, status=-1
=> Failed with mipgap=0 too
```

## Analysis

### Finding 1: Incorrect Error Code Identification

The claim states that GLP_EMIPGAP has errnum=9. This is false in Octave 8.4.0:

| Code | Octave GLPK Meaning |
|------|---------------------|
| errnum=9 | **GLP_ETMLIM** — time limit reached |
| errnum=14 | **GLP_EMIPGAP** — relative MIP gap tolerance reached |

The A-5 result document states "GLPK exits with GLP_EMIPGAP (errnum=9)" — this is a misidentification. errnum=9 in Octave is the time limit code, not the MIP gap code.

### Finding 2: No Feasible Solution Was Found

The most critical finding is that `extra.status = -1` (undefined / no solution). In Octave's GLPK:
- `status=2` (GLP_FEAS) = a feasible integer solution was found before termination
- `status=-1` = no feasible integer solution was found at all

The objective is `NA` and the solution vector has zero non-zero variables. This is not a solution that exists but cannot be extracted — there is no solution at all. GLPK terminated (via time limit, errnum=9) before finding any feasible integer point.

### Finding 3: miqps_glpk.m Does Have Dead-Code Path for errnum=9

Examining `miqps_glpk.m` line 240-241:
```matlab
eflag = -errnum;
if (eflag == 0 && extra.status == 5) || (errnum == 9 && extra.status == 2)
    eflag = 1;
end
```

The condition `(errnum == 9 && extra.status == 2)` was intended to handle the case where the time limit is hit but a feasible solution exists. This would correctly set `eflag=1`. However, in practice when Octave GLPK hits the time limit without finding a feasible solution, `extra.status=-1` (not 2), so this branch is never taken.

This code path would only be relevant if GLPK had found a feasible integer solution before the time limit. In the actual A-5/C-4 runs, no feasible solution was found.

### Finding 4: The Solve Time Claim is Misleading

The A-5 and C-4 results document "solve time: 0.68s / 1.112s" and present this as evidence the problem was solved. However, the probe confirms the solve returns in ~0.5s with no feasible solution — GLPK is terminating quickly because the problem is infeasible or very hard (likely due to tight min-up/min-down constraints combined with the load profile making the MILP infeasible in the given case39 configuration).

### Finding 5: The 162K Variable Claim (C-4)

The C-4 result (ACTIVSg2000, 432 generators × 24 periods ≈ 162K variables) may have the same issue — GLPK returns errnum=9 with status=-1 quickly, indicating no feasible solution found within the time limit, not a "solved" problem with an extraction bug.

### Finding 6: No Simple One-Line Fix

Since there is no feasible solution to extract, a fix to the exit flag mapping would not recover a working SCUC result. The actual problem is:
1. The case39 24-hour SCUC with the given min-up/min-down constraints is infeasible or extremely hard for GLPK
2. The solver exits quickly (time limit or preprocessing detection of infeasibility)
3. There is nothing to extract

## Classification Rationale

**claim_debunked** — The claim has three incorrect sub-claims:

1. **Wrong error code**: GLP_EMIPGAP is errnum=14 in Octave, not errnum=9. errnum=9 is GLP_ETMLIM (time limit).

2. **Wrong characterization of failure**: The claim says "GLPK finds a feasible integer solution" but `extra.status=-1` proves no feasible solution was ever found. The objective is NA, variables are all zero.

3. **One-line fix is wrong**: Since there is no feasible solution, fixing the exit flag mapping (which already partially handles errnum=9 when status=2) would not make the test pass. The SCUC problem is genuinely failing — it is not a post-processing extraction bug.

The underlying A-5 failure (FAIL→qualified_pass on ex_case3b workaround) and C-4 failure are real, but the mechanism is a genuine inability of GLPK to solve the SCUC problem to feasibility, not an exit flag mapping bug obscuring a successful solve.
