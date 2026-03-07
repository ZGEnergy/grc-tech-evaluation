---
test_id: B-7
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.2641
peak_memory_mb: null
loc: 50
timestamp: "2026-03-06T13:00:00Z"
---

# B-7: AC Feasibility as Extension on TINY (IEEE 39-bus)

## Result: PASS (no workaround needed)

## Approach

The DC OPF -> AC feasibility check workflow is a natural API flow in MATPOWER:

1. `dc_results = rundcopf(mpc, mpopt)` -- solve DC OPF
2. `mpc_ac.gen(:, PG) = dc_results.gen(:, PG)` -- transfer dispatch
3. `ac_results = runpf(mpc_ac, mpopt)` -- run AC power flow
4. Check `ac_results.success`, voltage bounds, reactive power bounds

Both DC OPF and AC PF use the identical `mpc` struct format. Generator dispatch
is a direct column (`PG`, column 2) in `mpc.gen`. No format conversion, no
adapter objects, no intermediate serialization.

## Results

### DC OPF

- Converged: YES
- Objective: 41263.94 $/hr
- Total dispatch: 6254.23 MW = total load

### AC Power Flow (feasibility check)

- Converged: YES
- Slack bus adjustment: +45.80 MW (AC losses)
- Total AC dispatch: 6300.03 MW

### AC Feasibility Assessment

| Check | Result |
|-------|--------|
| PF convergence | YES |
| Voltage violations | 1 (bus 36: Vm=1.0636 > Vmax=1.0600) |
| Reactive power violations | 1 |
| AC feasible | NO (marginal) |

The DC OPF dispatch is not strictly AC-feasible due to a minor voltage violation
at bus 36 (0.34% above Vmax). This is expected: DC OPF ignores reactive power
and voltage constraints, so the AC check will sometimes reveal violations.

### Voltage Profile

- Range: [0.9820, 1.0636] p.u.
- Angle range: [-19.79, 5.93] degrees
- Max apparent power flow: 689.32 MVA

## Workaround Classification

**No workaround needed.** This is a natural API flow:

- DC OPF and AC PF share the same data structure (`mpc` struct)
- Generator dispatch transfer is a single matrix column assignment
- AC PF automatically adjusts the slack generator for real power losses
- Voltage, reactive power, and flow results are all in standard struct fields
- No special "feasibility check" mode needed -- standard `runpf` suffices

The only implicit knowledge required is that AC PF uses the slack bus to absorb
the power mismatch from losses (which DC OPF does not model). This is standard
power systems knowledge, not a MATPOWER-specific workaround.

## Observations

- **arch-quality:** The unified `mpc` struct format across all analysis types
  (DCPF, ACPF, DCOPF, ACOPF) is a significant architectural strength. It enables
  seamless workflow composition without format conversion.
- **api-friction:** None. The three-step workflow (DC OPF -> set PG -> AC PF)
  requires ~5 lines of domain logic, all using standard API calls.

## Test Script

`evaluations/matpower/tests/extensibility/test_b7_ac_feasibility_extension_tiny.m`
