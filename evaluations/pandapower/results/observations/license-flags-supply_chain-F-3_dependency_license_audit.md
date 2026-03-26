---
tag: license-flags
source_dimension: supply_chain
source_test: F-3
tool: pandapower
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: LightSim2Grid uses MPL 2.0 (weak copyleft)

## Finding

LightSim2Grid (v0.12.2), an optional performance dependency of pandapower installed via
the `[performance]` extra, is licensed under the Mozilla Public License 2.0. This is the
only non-permissive license in the pandapower dependency tree.

## Details

- **Package:** LightSim2Grid 0.12.2
- **License:** MPL 2.0 (Mozilla Public License 2.0)
- **Source:** https://github.com/Grid2op/lightsim2grid
- **Developed by:** RTE France (Grid2Op team)
- **Role:** C++ accelerated Newton-Raphson power flow solver, optional alternative to
  pandapower's built-in pure-Python solver

## Risk Assessment

- **MPL 2.0 is file-level copyleft only:** Modifications to MPL-licensed files must be
  released under MPL 2.0, but the larger work is not affected. Importing/linking to
  LightSim2Grid does not trigger copyleft obligations.
- **Optionality:** LightSim2Grid is not required. pandapower functions without it, falling
  back to its own pure-Python/NumPy/SciPy Newton-Raphson solver. Excluding the
  `[performance]` extra removes it entirely.
- **OSI-approved:** MPL 2.0 is an OSI-approved license.

## Implications

This is a low-severity finding. For organizations with strict permissive-only license
policies, LightSim2Grid can be excluded by not installing the `[performance]` extra. The
remaining 38 packages in the dependency tree are all permissive (BSD, MIT, Apache 2.0,
PSF 2.0). No legal review is required for typical usage (importing the library); review
would only be needed if modifying LightSim2Grid source files.
