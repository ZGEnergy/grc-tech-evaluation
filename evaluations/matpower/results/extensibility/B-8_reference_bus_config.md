---
test_id: B-8
tool: matpower
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: "8c18d155"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.20
timing_source: measured
peak_memory_mb: 1.82
convergence_residual: null
convergence_iterations: null
loc: 195
solver: GLPK
timestamp: 2026-03-13T00:00:00Z
---

# B-8: Solve DC OPF with three slack configurations and compare LMPs

## Result: PASS

## Approach

Solved DC OPF on case39 with differentiated costs (hydro $5, nuclear $10, coal $25, gas $40) and 70% branch derating under three reference bus configurations:

1. **Config 1:** Original reference bus (bus 31, nuclear gen 2)
2. **Config 2:** Reference moved to bus 30 (hydro gen 1)
3. **Config 3:** Reference moved to bus 35 (nuclear gen 6)

Reference bus configuration in MATPOWER is accomplished by modifying the `BUS_TYPE` column in `mpc.bus`:
```matlab
mpc.bus(old_ref_idx, BUS_TYPE) = PV;     % demote old ref to PV
mpc.bus(new_ref_idx, BUS_TYPE) = REF;    % promote new bus to REF (type 3)
```

This is a single matrix element assignment -- no model reconstruction, no re-parsing, no API ceremony. The named constants `PV`, `REF` are provided by `define_constants`.

## Output

| Metric | Config 1 (bus 31) | Config 2 (bus 30) | Config 3 (bus 35) |
|--------|-------------------|-------------------|-------------------|
| Objective ($) | 126,125.36 | 126,125.36 | 126,125.36 |
| LMP range ($/MWh) | [5.00, 94.21] | [5.00, 94.21] | [5.00, 94.21] |
| LMP spread | 89.21 | 89.21 | 89.21 |
| Max |LMP diff| vs Config 1 | -- | 5.3e-12 | 1.2e-11 |
| Max |dispatch diff| vs Config 1 (MW) | -- | 38.0 | 2.6e-10 |
| Ref bus angle (deg) | 0.000 | -7.370 | 1.777 |

**Key findings:**

- **LMPs are identical** across all three configurations (differences < 1e-11, numerical noise). This is mathematically correct: DC OPF LMPs are dual variables of the power balance constraints and are invariant to the reference bus choice.
- **Voltage angles shift** as expected -- the reference bus angle is zero in each config, and all other angles are relative to it.
- **Dispatch differs between Config 1 and Config 2** by up to 38 MW. This occurs because changing the reference bus from bus 31 to bus 30 moves the slack generation from one generator to another in the power flow solution that underlies the OPF initial point, leading to a different (but equally optimal) dispatch among generators with the same marginal cost.
- **Objectives are identical** -- confirming the economic optimality is preserved.

## Workarounds

None required. Reference bus configuration is a first-class API operation via direct matrix modification of `mpc.bus(:, BUS_TYPE)`. The `BUS_TYPE` column uses well-documented integer codes (1=PQ, 2=PV, 3=REF, 4=isolated) defined in `idx_bus.m`. This is core MATPOWER functionality since version 1.0.

## Timing

- **Wall-clock:** 0.20 s (three DC OPF solves)
- **Timing source:** measured
- **Peak memory:** 1.82 MB
- **Per-config solve:** ~0.07 s

## Test Script

**Path:** `evaluations/matpower/tests/extensibility/test_b8_reference_bus_config.m`

API for reference bus reconfiguration (2 lines of code):
```matlab
mpc.bus(mpc.bus(:, BUS_TYPE) == REF, BUS_TYPE) = PV;    % demote old
mpc.bus(new_ref_idx, BUS_TYPE) = REF;                    % promote new
```
