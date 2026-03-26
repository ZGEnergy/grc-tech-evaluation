---
tag: api-friction
source_dimension: extensibility
source_test: B-5
tool: matpower
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No DataFrame or structured export in Octave/MATPOWER

## Finding

MATPOWER results are bare numeric matrices with no column name metadata. Exporting to CSV with column headers requires a manual `fopen/fprintf/fclose/dlmwrite` pattern (4 lines per table). Octave's `csvwrite()` cannot write string headers. There is no built-in equivalent to Python's `DataFrame.to_csv()` or Julia's `CSV.write(DataFrame(...))`.

## Context

B-5 tested DCPF result export to CSV. The minimal export (3 `csvwrite` calls, no headers) is under 5 lines, but produces headerless CSVs that are not self-documenting. Production-quality export with column headers requires 12 lines.

## Implications

This is relevant to the accessibility dimension (D-5, code volume) and the maturity dimension. The lack of structured data output increases integration effort when MATPOWER results need to feed downstream tools (Python, R, databases). Users must maintain manual column-index mappings or write custom export functions.
