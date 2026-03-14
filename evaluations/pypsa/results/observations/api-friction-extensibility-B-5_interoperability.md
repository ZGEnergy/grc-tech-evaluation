---
tag: api-friction
source_dimension: extensibility
source_test: B-5
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Zero API friction for DataFrame export

## Finding

PyPSA stores all results natively as pandas DataFrames, making export to CSV/Parquet/HDF5
a single method call with no conversion, no unwrapping, and no custom serialization.

## Context

B-5 tested exporting DCPF results to CSV. After `n.lpf()`, voltage angles are in
`n.buses_t.v_ang` (a pandas DataFrame) and line flows are in `n.lines_t.p0` (also a
DataFrame). Export requires 2 lines: access + `.to_csv()`. Round-trip fidelity is
perfect (max error 9.19e-17).

## Implications

This is a strong positive for accessibility. Users familiar with pandas can immediately
work with PyPSA results without learning any tool-specific result extraction API. The
DataFrame-native design means all pandas ecosystem tools (matplotlib, seaborn, scikit-learn,
Excel export, database ingestion) work without friction.
