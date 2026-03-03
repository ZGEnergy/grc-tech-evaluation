# PowerSimulations.jl (Sienna) — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** PowerSimulations 0.30.2, PowerSystems 4.6.2,
PowerFlows 0.9.0, PowerNetworkMatrices 0.12.1, InfrastructureSystems 2.6.0
**Script:** [`../verify_install.jl`](../verify_install.jl)

## Summary

DCPF on IEEE 39-bus completed successfully. Full bus and flow results
returned as DataFrames. But dependency resolution was the most difficult
of all six tools.

## Findings

### [maturity] Fragile cross-package compat bounds — two rounds of fixes needed

Initial `Pkg.instantiate()` failed twice:

1. **Wrong UUIDs**: The Sienna ecosystem uses many packages with similar
   names and the UUIDs are not easy to discover. `PowerSimulations` in
   particular has a UUID (`e690365d-...`) that does not match the more
   commonly-seen `PowerModels` UUID (`c36e90e8-...`). Easy to confuse
   when setting up a fresh project.

2. **Incompatible compat bounds**: The initial compat constraints
   (`PowerFlows = "0.6"`, `InfrastructureSystems = "2"`) were too tight.
   `PowerFlows 0.6.x` requires `InfrastructureSystems < 2.0`, but
   `InfrastructureSystems 2.x` requires `PowerFlows >= 0.7`. The bounds
   had to be widened to `PowerFlows = "0.6 - 0.16"` and
   `InfrastructureSystems = "2, 3"` to find a satisfiable solution.

   This indicates the Sienna packages have rapid, coupled version churn.
   A user following the official docs for version X may find the
   constraints unsatisfiable if any package has advanced.

**Rubric relevance:** Maturity (dependency coupling), Accessibility (hard
to set up from scratch without version archaeology).

### [maturity] Large dependency footprint — 80+ packages

The resolved Manifest.toml contains 80+ dependencies including MKL, HDF5,
SQLite, CSV, DataFrames, Pardiso, and several MPI implementations.
For comparison, PowerModels.jl resolves ~30 dependencies for the same
DCPF task. The Sienna stack pulls in its full production cost modeling
infrastructure even for a simple power flow.

This is a supply chain surface area concern — more dependencies means
more potential for breakage, more code to audit, and longer install times
(~45 seconds for precompilation alone).

### [supply_chain] Many packages pinned below latest (⌅ markers)

The Pkg resolver reports multiple packages restricted by compat
constraints from upgrading:
```
Packages marked with ⌅ are restricted by compatibility constraints
from upgrading.
```

Affected: InfrastructureSystems, PowerFlows, PowerNetworkMatrices,
PowerSystems, PowerSimulations, MKL, HDF5, and others. This means the
ecosystem is not keeping up with its own dependency upgrades — a common
symptom of rapid development without coordinated release management.

### [accessibility] Verbose but informative output

Loading case39 produces detailed validation warnings:
```
Invalid range: ThermalStandard gen-2 active_power 6.77 exceeds
active_power_limits.max 6.46
```

The tool validates input data against physical constraints and reports
every violation with the component name, field, and value. This is good
for catching data issues but produces a lot of output for standard test
cases where the MATPOWER data has generators at their limits.

### [accessibility] Rich result format — DataFrames

DCPF results are returned as a nested Dict of DataFrames with 9 columns
per flow result (P_from_to, Q_from_to, P_to_from, etc.). This is the
most structured output of any tool — ready for analysis without post-
processing. Compare to PowerModels which returns nested dicts of dicts.

### [accessibility] Multi-package API requires knowing which package does what

```julia
using PowerSystems    # data model, System()
using PowerFlows      # solve_powerflow()
using PowerNetworkMatrices  # DCPowerFlow type
```

A user must import three packages and know which type lives where.
`DCPowerFlow()` comes from PowerNetworkMatrices, not PowerFlows. The
`System()` constructor comes from PowerSystems, not PowerSimulations.
This is well-documented but adds cognitive overhead.

### [gate] DCPF passes

39 buses, 46 branches (full flow results table), DC power flow converges.
