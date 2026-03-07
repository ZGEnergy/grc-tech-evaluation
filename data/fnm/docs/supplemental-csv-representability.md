# Supplemental CSV Representability Summary

**Version:** 1.0
**Source document:** [Supplemental CSV Reference Documentation](supplemental-csvs.md)
**Audience:** evaluate-tool agents, human reviewers
**Purpose:** Cross-tool summary of supplemental CSV representability,
  optimized for quick Extensibility grading consumption. All classifications
  are derived from the per-field analysis in the source document.

## Representability Tiers

| Tier | Label | Definition |
|------|-------|------------|
| Native | `native` | Tool has a built-in attribute, property, or field that directly represents this data. No custom code or extension mechanism required. |
| Extension | `extension` | Tool can carry this data via its documented extension mechanisms (custom attributes, metadata dictionaries, user-defined component fields) without forking or patching the tool's source code. |
| External | `external` | No representation path within the tool. Data must be carried in an external data structure (DataFrame, dict, database) alongside the tool's network model. |

## CSV-Level Representability Matrix

| CSV | Fields | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|-----|--------|-------|------------|---------|----------------|---------------------|----------|
| LINE_AND_TRANSFORMER.csv | 10 | 40% native, 60% extension, 0% external | 40% native, 60% extension, 0% external | 40% native, 60% extension, 0% external | 60% native, 40% extension, 0% external | 40% native, 60% extension, 0% external | 60% native, 40% extension, 0% external |
| TRADING_HUB.csv | 4 | 25% native, 0% extension, 75% external | 25% native, 0% extension, 75% external | 25% native, 0% extension, 75% external | 25% native, 0% extension, 75% external | 25% native, 0% extension, 75% external | 25% native, 0% extension, 75% external |
| GEN_DISTRIBUTION_FACTOR.csv | 5 | 40% native, 20% extension, 40% external | 40% native, 20% extension, 40% external | 40% native, 20% extension, 40% external | 40% native, 20% extension, 40% external | 40% native, 20% extension, 40% external | 20% native, 40% extension, 40% external |
| CONTINGENCY.csv | 6 | 50% native, 17% extension, 33% external | 50% native, 17% extension, 33% external | 83% native, 17% extension, 0% external | 50% native, 17% extension, 33% external | 83% native, 17% extension, 0% external | 50% native, 17% extension, 33% external |
| INTERFACE.csv | 5 | 0% native, 0% extension, 100% external | 0% native, 0% extension, 100% external | 0% native, 0% extension, 100% external | 0% native, 0% extension, 100% external | 60% native, 40% extension, 0% external | 40% native, 40% extension, 20% external |
| INTERFACE_ELEMENT.csv | 6 | 33% native, 17% extension, 50% external | 33% native, 17% extension, 50% external | 33% native, 17% extension, 50% external | 33% native, 17% extension, 50% external | 67% native, 33% extension, 0% external | 67% native, 33% extension, 0% external |
| OUTAGE.csv | 8 | 38% native, 12% extension, 50% external | 38% native, 12% extension, 50% external | 38% native, 12% extension, 50% external | 38% native, 12% extension, 50% external | 38% native, 12% extension, 50% external | 38% native, 12% extension, 50% external |
| **Totals** | **44** | 34% native, 23% extension, 43% external | 34% native, 23% extension, 43% external | 39% native, 23% extension, 38% external | 39% native, 18% extension, 43% external | 50% native, 30% extension, 20% external | 45% native, 27% extension, 28% external |

**Derivation Note:** Percentages are calculated as `(fields in tier / total classifiable fields) * 100` per CSV per tool. The Totals row uses field-count-weighted aggregation: each CSV's native/extension/external field counts are summed across all 7 CSVs, and the percentage is computed from the aggregate counts divided by the total field count (44). This means a CSV with more fields (e.g., LINE_AND_TRANSFORMER.csv with 10 fields) contributes proportionally more to the total than a CSV with fewer fields (e.g., TRADING_HUB.csv with 4 fields). The source field counts and per-field classifications are in the [Supplemental CSV Reference Documentation](supplemental-csvs.md), in each CSV's "Per-Field Representability" section (e.g., [LINE_AND_TRANSFORMER per-field representability](supplemental-csvs.md#line-and-transformer--per-field-representability)).

## Concept-Level Representability Matrix

| Data Concept | Source CSV(s) | PyPSA | pandapower | GridCal | PowerModels.jl | PowerSimulations.jl | MATPOWER |
|--------------|---------------|-------|------------|---------|----------------|---------------------|----------|
| Thermal Ratings (4-tier) | LINE_AND_TRANSFORMER.csv | `extension` | `extension` | `extension` | `extension` | `extension` | `extension` |
| Seasonal / Temporal Rating Variations | LINE_AND_TRANSFORMER.csv | `extension` | `extension` | `extension` | `extension` | `extension` | `extension` |
| Trading Hub Definitions | TRADING_HUB.csv | `external` | `external` | `external` | `external` | `external` | `external` |
| Generator Distribution Factors | GEN_DISTRIBUTION_FACTOR.csv | `external` | `external` | `external` | `external` | `external` | `external` |
| Contingency Definitions | CONTINGENCY.csv | `external` | `external` | `native` | `external` | `native` | `external` |
| Interface Definitions and Flow Limits | INTERFACE.csv, INTERFACE_ELEMENT.csv | `external` | `external` | `external` | `external` | `extension` | `extension` |
| Outage Actions / Planned Outage Parameters | OUTAGE.csv | `external` | `external` | `external` | `external` | `external` | `external` |
| Ownership and Operational Metadata | LINE_AND_TRANSFORMER.csv | `extension` | `extension` | `extension` | `extension` | `extension` | `extension` |

**Classification Rule:** The concept-level classification for each tool follows a conservative (lowest-tier) aggregation rule: the concept's tier is the lowest tier among all its constituent fields, where `native` > `extension` > `external`. This means a concept is classified as `native` only if ALL constituent fields are natively representable. If any single field within the concept is `external`, the entire concept is classified as `external` for that tool. This reflects the practical reality that an analyst cannot fully use a data concept within the tool if any part of it requires external handling. For the per-field breakdown that produces each concept-level classification, see the [Supplemental CSV Reference Documentation](supplemental-csvs.md).

## Key Findings

### Richest Native Coverage

PowerSimulations.jl achieves the highest native-tier percentage in the CSV-Level Representability Matrix at 50% native across all 44 fields. This lead is driven by its first-class support for contingency definitions (83% native in CONTINGENCY.csv via the `Contingency` type), transmission interfaces (60% native in INTERFACE.csv and 67% native in INTERFACE_ELEMENT.csv via `TransmissionInterface`), and standard network element fields. MATPOWER ranks second at 45% native overall, benefiting from native support for 3 thermal rating tiers (RATE_A/B/C in `mpc.branch`) and interface definitions (`mpc.if` and `mpc.iflim`).

In the Concept-Level Matrix, PowerSimulations.jl is the only tool with `native` classification for contingency definitions. Both PowerSimulations.jl and MATPOWER achieve `extension` for interface definitions and flow limits, while all other tools classify this concept as `external`.

GridCal matches PowerSimulations.jl in contingency coverage (83% native in CONTINGENCY.csv) thanks to its native `ContingencyGroup` object, but lacks interface support, resulting in a lower overall native percentage of 39%.

PyPSA and pandapower cluster at 34% native, while PowerModels.jl reaches 39% native (matching GridCal) due to its native support for 3 thermal rating tiers. All four tools share similar gaps: no native concepts for contingencies (except GridCal), interfaces, or market-layer data.

### Universally Tool-External CSVs

**TRADING_HUB.csv** is the most uniformly tool-external CSV: all 6 tools have identical representability profiles (25% native, 0% extension, 75% external). The only natively representable field is BUS_NUMBER (the physical bus reference); HUB_NAME, DISTRIBUTION_FACTOR, and HUB_TYPE are tool-external across all tools because trading hubs are a market-layer abstraction with no analog in any power flow tool's domain model.

**OUTAGE.csv** is effectively universally tool-external for its domain-specific fields: all 6 tools have identical profiles (38% native, 12% extension, 50% external). The natively representable fields are physical element identifiers (bus numbers) rather than outage-specific data. The outage schedule fields (OUTAGE_START, OUTAGE_END, OUTAGE_TYPE, ELEMENT_TYPE) are tool-external across all tools because no tool models temporal outage schedules.

**INTERFACE.csv** is 100% tool-external in 4 of 6 tools (PyPSA, pandapower, GridCal, PowerModels.jl). Only PowerSimulations.jl and MATPOWER have any native interface representation.

### Most Consequential Gaps for Phase 2

**Interface definitions and flow limits** represent the most consequential representability gap for Phase 2 congestion analysis readiness. Interfaces (flowgates) are the primary mechanism CAISO uses to manage transmission corridor congestion, and the inability to represent interface definitions within a tool means congestion analysis must rely entirely on external data structures and custom scripting. PyPSA, pandapower, GridCal, and PowerModels.jl all classify INTERFACE.csv as 100% external and INTERFACE_ELEMENT.csv as 50% external (Table 1), with the concept-level classification of `external` (Table 2). This gap is not addressable via extension mechanisms for these four tools because the interface concept itself -- a named group of branches with aggregate flow limits and direction coefficients -- has no structural analog in their data models. Only PowerSimulations.jl (via `TransmissionInterface`) and MATPOWER (via `mpc.if`/`mpc.iflim`) can carry this data internally.

See [INTERFACE per-field representability](supplemental-csvs.md#interfacecsv) and [INTERFACE_ELEMENT per-field representability](supplemental-csvs.md#interface_elementcsv) in D1 for the per-field evidence.

**Trading hub definitions** are the second most consequential gap. Without hub definitions, a tool cannot model hub-based congestion revenue rights (CRRs) or compute hub-level locational marginal prices (LMPs) from nodal results. All 6 tools classify the trading hub concept as `external` (Table 2), meaning hub data must be maintained in external DataFrames or dictionaries and manually associated with bus-level results post-solution. This gap is inherent to all tools because hubs are a market construct outside the power flow domain.

See [TRADING_HUB per-field representability](supplemental-csvs.md#trading_hubcsv) in D1.

**Contingency definitions** affect 4 of 6 tools (PyPSA, pandapower, PowerModels.jl, MATPOWER), which classify CONTINGENCY_NAME and ELEMENT_TYPE as tool-external. Without native contingency definitions, these tools require external scripting to enumerate and apply contingency scenarios for N-1/N-2 analysis. The gap is partially addressable via extension mechanisms (storing contingency metadata in custom fields) but the absence of a native contingency object means the tool's solver cannot directly consume contingency definitions. GridCal and PowerSimulations.jl do not have this gap.

See [CONTINGENCY per-field representability](supplemental-csvs.md#contingencycsv) in D1.

### Tool Landscape Summary

The supplemental CSV representability landscape reveals a clear stratification among the six tools. PowerSimulations.jl stands out with the broadest native coverage (50%) due to its first-class support for contingencies, interfaces, and standard network elements. MATPOWER follows (45%) with native interface and multi-tier thermal rating support. GridCal and PowerModels.jl sit at 39% native, with GridCal's advantage in contingency support offset by PowerModels.jl's additional thermal rating tiers. PyPSA and pandapower trail at 34% native. The practical implication for analysts is significant: even with the best-performing tool, half of supplemental CSV fields require extension or external handling, and market-layer concepts (trading hubs, generator distribution factors) and temporal concepts (outage schedules, seasonal ratings) are universally outside all tools' native domain models.

## Traceability Index

| Matrix | Row | D1 Section Reference |
|--------|-----|---------------------|
| Table 1 | LINE_AND_TRANSFORMER.csv | [LINE_AND_TRANSFORMER per-field representability](supplemental-csvs.md#line_and_transformercsv) -- fields: FROM_BUS, TO_BUS, CKT, ELEMENT_TYPE, RATE_A, RATE_B, RATE_C, RATE_D, STATUS, EFFECTIVE_DATE |
| Table 1 | TRADING_HUB.csv | [TRADING_HUB per-field representability](supplemental-csvs.md#trading_hubcsv) -- fields: HUB_NAME, BUS_NUMBER, DISTRIBUTION_FACTOR, HUB_TYPE |
| Table 1 | GEN_DISTRIBUTION_FACTOR.csv | [GEN_DISTRIBUTION_FACTOR per-field representability](supplemental-csvs.md#gen_distribution_factorcsv) -- fields: GEN_BUS, GEN_ID, HUB_NAME, PARTICIPATION_FACTOR, GEN_NAME |
| Table 1 | CONTINGENCY.csv | [CONTINGENCY per-field representability](supplemental-csvs.md#contingencycsv) -- fields: CONTINGENCY_NAME, ELEMENT_TYPE, ELEMENT_FROM_BUS, ELEMENT_TO_BUS, ELEMENT_CKT, ELEMENT_BUS |
| Table 1 | INTERFACE.csv | [INTERFACE per-field representability](supplemental-csvs.md#interfacecsv) -- fields: INTERFACE_ID, INTERFACE_NAME, NORMAL_LIMIT_MW, EMERGENCY_LIMIT_MW, DIRECTION |
| Table 1 | INTERFACE_ELEMENT.csv | [INTERFACE_ELEMENT per-field representability](supplemental-csvs.md#interface_elementcsv) -- fields: INTERFACE_ID, FROM_BUS, TO_BUS, CKT, DIRECTION_COEFF, WEIGHT_FACTOR |
| Table 1 | OUTAGE.csv | [OUTAGE per-field representability](supplemental-csvs.md#outagecsv) -- fields: ELEMENT_TYPE, ELEMENT_FROM_BUS, ELEMENT_TO_BUS, ELEMENT_CKT, ELEMENT_BUS, OUTAGE_START, OUTAGE_END, OUTAGE_TYPE |
| Table 2 | Thermal Ratings (4-tier) | [LINE_AND_TRANSFORMER per-field representability](supplemental-csvs.md#line_and_transformercsv) -- fields: RATE_A, RATE_B, RATE_C, RATE_D |
| Table 2 | Seasonal / Temporal Rating Variations | [LINE_AND_TRANSFORMER per-field representability](supplemental-csvs.md#line_and_transformercsv) -- fields: EFFECTIVE_DATE, STATUS |
| Table 2 | Trading Hub Definitions | [TRADING_HUB per-field representability](supplemental-csvs.md#trading_hubcsv) -- fields: HUB_NAME, BUS_NUMBER, DISTRIBUTION_FACTOR, HUB_TYPE |
| Table 2 | Generator Distribution Factors | [GEN_DISTRIBUTION_FACTOR per-field representability](supplemental-csvs.md#gen_distribution_factorcsv) -- fields: GEN_BUS, GEN_ID, HUB_NAME, PARTICIPATION_FACTOR, GEN_NAME |
| Table 2 | Contingency Definitions | [CONTINGENCY per-field representability](supplemental-csvs.md#contingencycsv) -- fields: CONTINGENCY_NAME, ELEMENT_TYPE, ELEMENT_FROM_BUS, ELEMENT_TO_BUS, ELEMENT_CKT, ELEMENT_BUS |
| Table 2 | Interface Definitions and Flow Limits | [INTERFACE per-field representability](supplemental-csvs.md#interfacecsv) and [INTERFACE_ELEMENT per-field representability](supplemental-csvs.md#interface_elementcsv) -- all fields from both CSVs |
| Table 2 | Outage Actions / Planned Outage Parameters | [OUTAGE per-field representability](supplemental-csvs.md#outagecsv) -- fields: ELEMENT_TYPE, OUTAGE_START, OUTAGE_END, OUTAGE_TYPE |
| Table 2 | Ownership and Operational Metadata | [LINE_AND_TRANSFORMER per-field representability](supplemental-csvs.md#line_and_transformercsv) -- fields: CKT, ELEMENT_TYPE, STATUS, EFFECTIVE_DATE |
