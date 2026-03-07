# Observation: doc-gaps -- A-8 stochastic_timeseries

**Test:** A-8 (Stochastic Timeseries DCOPF)
**Dimension:** expressiveness
**Tool:** PowerModels.jl v0.21.5

## Finding

PowerModels.jl has no native stochastic OPF capability. The multi-network framework (`replicate()` + `solve_mn_opf()`) supports multi-period (temporal) optimization but not multi-scenario. The documentation (issue #169, open since 2017) acknowledges sparse multi-network documentation, and there is no documentation at all clarifying what the multi-network framework can and cannot express (e.g., that it is one-dimensional -- time periods only, not scenario trees).

The stochastic OPF gap is documented in GitHub issue #112 (open since 2017) but not in the official documentation. Users must discover this limitation through GitHub issues or community forums.

StochasticPowerModels.jl (KU Leuven/Electa, 24 stars) exists but is a separate external package with different design philosophy (polynomial chaos expansion, not scenario-based). The relationship between core PowerModels and this extension package is not documented in core PowerModels' docs.

## Impact

Medium. Stochastic optimization is important for renewable-heavy grids. The lack of clear documentation about what the multi-network framework can/cannot express may mislead users into expecting scenario support that does not exist.
