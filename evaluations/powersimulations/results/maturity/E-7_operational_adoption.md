---
test_id: E-7
tool: powersimulations
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# E-7: Operational Adoption

## Summary

PowerSimulations.jl has **limited evidence of operational adoption** outside NREL. It is primarily used as a research tool within the DOE national laboratory ecosystem. No confirmed use by utilities, ISOs, or commercial energy traders was found. The broader Sienna platform is marketed to "researchers, utilities, and operators" but specific adopters are not publicly named.

## Quantitative Indicators

| Metric | Value |
|--------|-------|
| GitHub stars | 311 |
| GitHub forks | 78 |
| Total downloads (juliapkgstats) | 6,174 |
| Downloads last 30 days | 264 |
| Downloads last week | 132 |
| Contributors (all-time) | 20 |

## Download Geography (Last 30 Days)

| Region | Downloads |
|--------|-----------|
| US East | ~114 |
| US West | ~83 |
| EU Central | ~23 |
| India | ~12 |
| Australia | ~7 |
| Other | ~25 |

The US-heavy download pattern is consistent with NREL-internal and DOE-affiliated use.

## Known Adoption

### Confirmed
- **NREL:** Primary developer and user for DOE-funded grid modeling research
- **DOE Office of Electricity:** Funder via AGM/R2D2 and GMLC/FlexPower projects
- **G-PST (Global Power System Transformation Consortium):** Lists Sienna as a recognized open-source tool
- **Academic/research use:** Zenodo DOI indicates academic citation, and the Slack community exists for users

### Unconfirmed / No Evidence Found
- No confirmed use by any ISO (ERCOT, CAISO, MISO, PJM, etc.)
- No confirmed use by any electric utility
- No confirmed use by any commercial energy company
- No confirmed use in any regulatory filing or official grid planning study (outside NREL-authored reports)
- NREL's Sienna page states "more researchers, utilities, and operators are turning to Sienna" but names no specific entities

## Ecosystem Context

PowerSimulations.jl is part of the broader Sienna ecosystem with related packages:
- **PowerSystems.jl** -- data modeling
- **PowerSimulationsDynamics.jl** -- transient stability
- **PowerFlows.jl** -- power flow calculations
- **PowerNetworkMatrices.jl** -- network matrices
- **HydroPowerSimulations.jl** -- hydropower extensions
- **StorageSystemsSimulations.jl** -- storage extensions
- **PowerAnalytics.jl** -- results analysis

The ecosystem approach indicates institutional commitment, but also means adoption requires buy-in to the full Julia/Sienna stack rather than individual package adoption.

## Comparison Context

For reference, competing tools have much larger user bases:
- **pandapower:** 1,900+ GitHub stars, documented use by multiple European DSOs and TSOs
- **PyPSA:** 1,400+ GitHub stars, used in EU policy studies and by multiple research groups
- **MATPOWER:** decades of adoption in academia and industry

## Observations

- The 6,174 total downloads figure is low for a package with 8+ years of development, though Julia package download counts undercount due to precompilation caching (packages are downloaded once and reused).
- The 264 monthly downloads suggest a small but active user base, likely concentrated in the DOE/NREL research community.
- The Julia language barrier (niche compared to Python/MATLAB) significantly limits potential adoption.
- No evidence of production deployment in utility operations or market clearing -- the tool is positioned for research and planning studies.

## Sources

- GitHub repo: <https://github.com/NREL-Sienna/PowerSimulations.jl>
- Julia package stats: <https://juliapkgstats.com/pkg/PowerSimulations>
- NREL Sienna page: <https://www.nrel.gov/analysis/sienna>
- G-PST listing: <https://globalpst.org/sienna-modeling-framework/>
