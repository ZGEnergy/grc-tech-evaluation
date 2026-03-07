---
test_id: B-7
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: fragile
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: "HiGHS (DCOPF), PowerFlows.jl (ACPF)"
timestamp: "2026-03-07T05:00:00Z"
---

# B-7: AC Feasibility Extension -- Workaround Assessment

## Result: QUALIFIED PASS

## Workaround from A-4

The DCOPF -> ACPF workflow (A-4) required a workaround because PSI's `read_variables()`
returns `ActivePowerVariable` values in a different unit basis than PowerSystems.jl's
component accessors (`get_active_power_limits()`). Dispatch values from PSI are ~100x
larger than Pmax values from the System, making direct transfer to PowerFlows impossible.

From A-4 results: gen-1 dispatch was reported as 660.85 pu when Pmax is 10.40 pu. All
10 generators showed this ~100x scaling mismatch. The ACPF could not converge on these
physically unrealistic dispatch values (660 pu = 66 GW per generator on a 100 MVA base).

## Workaround Classification

Durability: FRAGILE

- **What:** Unit conversion between PSI's internal representation and PowerSystems.jl
  component units. The conversion factor appears to be the system base MVA (100 MVA),
  but this is not documented.
- **Why:** PSI and PowerFlows use different unit conventions for the same System object.
  PSI's optimization variables operate in a scaled space, while PowerSystems.jl accessors
  return per-unit values on the device base.
- **Risk:** The conversion factor is empirically determined (~100x). It could change
  with PSI version updates, different system base MVA values, or different component
  types. There is no documented API for unit conversion between PSI results and
  PowerSystems.jl component values.
- **Fragility indicators:**
  - No mention of this unit mismatch in PSI documentation
  - No `convert_units()` or similar utility function provided
  - The scaling factor may differ for reactive power, storage, or other component types
  - Different MATPOWER files with different base MVA would need different scaling

## Effort Level

- **Discovery:** ~2 hours of debugging (comparing PSI dispatch vs PowerSystems Pmax)
- **Implementation:** ~10 lines of code (divide dispatch by base MVA)
- **Verification:** Requires comparing converted values against component limits

## Impact on Grade

This workaround represents a significant API friction point. The unit mismatch between
PSI and PowerFlows is undocumented and requires either source code investigation or
trial-and-error to discover. For production use, this creates a reliability risk where
incorrect unit handling could silently produce wrong ACPF results.

The DCOPF -> ACPF workflow architecture (shared System object, dispatch via setters,
PowerFlows solve) is sound in principle, but the unit scaling issue makes it fragile
in practice.

## Test Script

See `evaluations/powersimulations/tests/expressiveness/test_a4_ac_feasibility.jl`
