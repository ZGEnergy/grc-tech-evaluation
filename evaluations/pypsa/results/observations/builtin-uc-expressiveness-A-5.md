# Observation: PyPSA Has Comprehensive Built-in UC Constraints

**Test:** A-5 (SCUC)
**Dimension:** expressiveness
**Tool:** pypsa 1.1.2

## Finding

PyPSA provides 7 of 8 common SCUC constraint types as built-in generator attributes
(min_up_time, min_down_time, start_up_cost, shut_down_cost, ramp_limit_up,
ramp_limit_down, p_min_pu). Only reserve requirements need user assembly via the
`extra_functionality` callback.

The `extra_functionality` mechanism is well-documented and provides direct access
to the linopy model, allowing arbitrary linear constraints to be added using
xarray-aligned expressions. The interface is clean but requires knowledge of
the internal variable naming convention (e.g., "Generator-status" for commitment
binary variables, with dimension "name" for generators).

## Implication

Strong expressiveness for SCUC. The only user-assembled constraint (reserve) is
added via a documented, stable callback mechanism -- not a workaround. This
positions PyPSA well for operational UC formulations.
