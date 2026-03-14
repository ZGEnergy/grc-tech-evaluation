---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: matpower
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: NR convergence residual not stored in results struct

## Finding

MATPOWER's `runpf()` stores the NR iteration count in `results.iterations` but does not store the final convergence residual in the results struct. The residual is only visible in verbose output (level 2+), which must be parsed from printed text.

## Context

During A-2 ACPF testing, `verbose=2` output showed per-iteration max residual and max dx values, with the final residual at 3.319e-11 (well below the 1e-8 tolerance). However, extracting this value programmatically requires parsing stdout rather than accessing a struct field.

## Implications

This is a minor diagnostic quality limitation. For scalability tests (C-2) that need to record convergence residuals across many runs, parsing verbose output adds friction. For the Accessibility audit (D-4), note that MATPOWER's verbose output format is well-structured and machine-parseable, but the lack of a `results.residual` field is a missing convenience feature.
