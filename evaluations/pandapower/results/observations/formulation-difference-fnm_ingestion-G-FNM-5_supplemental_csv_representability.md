---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: pandapower
severity: low
timestamp: 2026-03-24T12:00:00Z
---

# Observation: pandapower thermal rating uses kA (current) not MVA (power)

## Finding

pandapower's native thermal rating field `line.max_i_ka` stores current limits in
kA rather than power limits in MVA. The supplemental CSV RATE_A field is specified
in MVA. Ingesting RATE_A requires a voltage-dependent conversion:
`max_i_ka = rate_a_mva / (sqrt(3) * vn_kv)`. This is a unit convention difference,
not a data model gap, but it introduces a conversion step that could be a source
of errors if voltage levels are mismatched.

## Context

During G-FNM-5 representability classification, RATE_A was classified as N (native)
for pandapower because `line.max_i_ka` directly represents a thermal limit. However,
the MVA-to-kA conversion is required at ingestion time for all LINE_AND_TRANSFORMER.csv
records. Transformer ratings use `trafo.sn_mva` which is already in MVA, so the
conversion asymmetry applies only to lines.

## Implications

This affects the Accessibility dimension: users ingesting FNM thermal ratings must
be aware of the unit convention difference and apply the correct conversion formula.
The conversion is straightforward but differs from other tools (PyPSA uses `s_nom` in
MVA, PowerModels uses MVA directly) which may cause confusion when comparing results
across tools.
