---
tag: arch-quality
source_dimension: extensibility
source_test: B-5
tool: pandapower
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: DataFrame-native results enable zero-friction data export

## Finding

pandapower stores all power flow and OPF results as pandas DataFrames (`net.res_bus`, `net.res_line`, `net.res_gen`, etc.), making data export to CSV, Parquet, or any pandas-supported format a single `.to_csv()` call per result table. No custom serialization, format conversion, or intermediate data structures are needed.

## Context

During B-5 (interoperability), exporting full DCPF results for all buses, lines, generators, and transformers required exactly 4 lines of code -- one `.to_csv()` call per table. CSV roundtrip verification confirmed lossless serialization. This is a direct consequence of pandapower's architectural decision to use pandas DataFrames as its primary data model.

## Implications

This positive architectural finding is relevant for the Accessibility dimension: any user familiar with pandas can immediately work with pandapower results without learning a custom data format or API. It also benefits integration workflows -- results feed directly into downstream analysis (plotting, statistics, comparison) without transformation. This is one of the strongest interoperability designs among the evaluated tools.
