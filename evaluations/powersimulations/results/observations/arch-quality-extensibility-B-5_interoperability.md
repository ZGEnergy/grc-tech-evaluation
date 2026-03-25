---
tag: arch-quality
source_dimension: extensibility
source_test: B-5
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Native DataFrame output eliminates serialization impedance mismatch

## Finding

PowerFlows.jl and PowerSimulations.jl return results as DataFrames.jl objects natively.
Exporting to CSV requires exactly 2 lines of code (`CSV.write(path, df)`) with zero
type conversion or custom serialization logic.

## Context

B-5 tested interoperability by exporting DCPF results to CSV. The Julia ecosystem's
composability (DataFrames.jl + CSV.jl + PowerFlows.jl) means these packages work together
without explicit integration code. This is a strength of the language-level multiple
dispatch design.

## Implications

This is a positive architectural finding for the Maturity audit. The native DataFrame
result format means users never need to write custom serialization code, reducing
error-prone boilerplate. The 2-LOC export is well under any reasonable friction threshold.
