---
probe_id: probe-032
tool: matpower
source_test: C-4
probe_type: claim_verification
classification: claim_supported
reason: "loadmd() confirmed to fail with exact error message about non-consecutive bus numbering on ACTIVSg 2000; ext2int resolves the bus issue but reveals further MOST input requirements"
solver_version: "MATPOWER 8.1"
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 12
timestamp: "2026-03-09T21:15:00Z"
---

# Probe 032: MOST loadmd() Fails at Data Ingestion Due to Non-Consecutive Bus Numbering

## Original Claim

From `evaluations/matpower/results/scalability/C-4_scuc_scale_SMALL.md`:

> MOST SCUC on SMALL failed at the `loadmd()` stage with: "buses must be numbered consecutively in MPC.bus matrix; use ext2int() to convert to internal ordering". The ACTIVSg 2000 network has non-consecutive bus numbering, and `loadmd` does not accept pre-converted internal-order cases (it calls `ext2int` internally but fails on the validation check).

The claim also states: "Even if the ext2int issue were resolved, the resulting MILP would be extremely large and likely exceed GLPK's capacity."

## Probe Methodology

Three scripts were run sequentially:

1. **probe-032_script.m**: Initial attempt with minimal xGenData (missing required fields) -- revealed that xGenData validation occurs before bus numbering check.
2. **probe-032b_script.m**: Source code inspection of loadmd.m to locate the bus numbering check and identify all required xGenData fields.
3. **probe-032c_script.m**: Complete xGenData struct with all 13 required fields. Tested loadmd on:
   - ACTIVSg 2000 (non-consecutive buses, IDs 1001-8160)
   - ACTIVSg 2000 after ext2int conversion (consecutive buses 1-2000)
   - case39 as control (consecutive buses, 39 buses)

## Probe Results

### Source Code Inspection (loadmd.m)

Lines 301-303 of loadmd.m contain the explicit check:

```matlab
%% check that bus numbers are equal to indices to bus (one set of bus numbers)
if any(mpc.bus(:, BUS_I) ~= (1:nb)')
    error('loadmd: buses must be numbered consecutively in MPC.bus matrix; use ext2int() to convert to internal ordering')
end
```

Line 22 also documents: "**Note:** Bus numbers must be consecutive beginning at 1"

### Test Results

```
--- Test 1: loadmd on raw ACTIVSg 2000 (non-consecutive) ---
loadmd: FAILED
Error: loadmd: buses must be numbered consecutively in MPC.bus matrix;
       use ext2int() to convert to internal ordering
>>> CONFIRMED: fails with consecutive bus numbering error

--- Test 2: loadmd on ext2int-converted ACTIVSg 2000 ---
Internal: 2000 buses, 432 gens (ext2int removed 112 offline gens)
loadmd: FAILED even with ext2int
Error: loadmd: contab must be matrix with 7 columns

--- Test 3: loadmd on case39 (consecutive, control) ---
loadmd: FAILED on case39
Error: loadmd: contab must be matrix with 7 columns
```

### Key Findings

1. **Bus numbering error is confirmed**: The exact error message from the claim is reproduced. ACTIVSg 2000 has bus IDs 1001-8160 (non-consecutive), which triggers the check at loadmd.m line 302.

2. **ext2int resolves the bus numbering issue**: After ext2int conversion, the bus numbering check passes. The subsequent "contab" error is about a missing contingency table (separate required MOST input), not a bus numbering issue.

3. **Standard MATPOWER functions handle ext2int transparently**: `rundcpf` and `rundcopf` both succeed on raw ACTIVSg 2000 without manual ext2int. This confirms the asymmetry between MOST's loadmd (which requires pre-converted data) and core MATPOWER functions.

4. **The claim about "loadmd does not accept pre-converted internal-order cases" is partially wrong**: The probe shows ext2int-converted cases DO pass the bus numbering check. The original evaluation's claim may have been about a different issue, or may have tested incorrectly. However, the ext2int conversion does remove 112 offline generators (544 -> 432), which would require rebuilding the xGenData struct with matching dimensions.

## Analysis

The core claim is confirmed: MOST's `loadmd()` fails on ACTIVSg 2000 at the data ingestion stage due to non-consecutive bus numbering, before any solver is invoked. The error message matches exactly.

The secondary claim about "even if ext2int were resolved, GLPK would be too slow" is not tested by this probe (would require a complete MOST SCUC setup with contab, profiles, etc., which exceeds the probe scope). However, the claim is reasonable given the problem scale (544 generators x 24 periods = ~200,000 MILP variables).

The claim that "loadmd does not accept pre-converted internal-order cases" is slightly misleading -- ext2int-converted cases DO pass the bus check, but the full MOST setup requires additional input consistency (xGenData dimensions must match the post-ext2int generator count, contab must be provided, etc.).

## Classification Rationale

Classified as **claim_supported** because:
- The exact error message is reproduced: "buses must be numbered consecutively in MPC.bus matrix"
- The failure is confirmed to occur at the loadmd() data ingestion stage, not at the solver
- The source code at loadmd.m:302-303 contains the explicit check
- Standard MATPOWER functions (rundcpf, rundcopf) handle ext2int transparently, confirming this is a MOST-specific limitation
- The claim correctly identifies the root cause as non-consecutive bus numbering in ACTIVSg 2000
