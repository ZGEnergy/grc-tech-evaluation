---
tag: arch-quality
source_dimension: extensibility
source_test: B-5
tool: pandapower
severity: low
timestamp: 2026-03-06T00:00:00Z
---

# Observation: Native pandas DataFrame results enable trivial interoperability

## Finding

pandapower stores all simulation results as pandas DataFrames (`net.res_bus`, `net.res_line`, etc.), making data export trivially simple. CSV export requires exactly 2 lines of code. JSON, Excel, Parquet, and numpy exports are equally simple via standard pandas methods. No custom serialization, format conversion, or API calls are needed.

## Context

B-5 tested exporting DCPF results to CSV. The entire export (bus results + line results) was accomplished with `net.res_bus.to_csv()` and `net.res_line.to_csv()`. Round-trip verification confirmed data integrity. This is the strongest possible result for interoperability.

## Implications

pandapower's pandas-native data model is a significant architectural strength. It eliminates the interoperability friction that tools with custom data structures typically impose. This should be noted positively in the Accessibility and Maturity assessments.
