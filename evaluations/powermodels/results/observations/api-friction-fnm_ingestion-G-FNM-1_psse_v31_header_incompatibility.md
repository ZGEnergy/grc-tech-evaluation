---
tag: api-friction
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powermodels
severity: high
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: PSS/E v31 RAW Header Parse Failure and No CSV Parser

## Finding

PowerModels.jl cannot ingest the FNM intermediate CSV format (no CSV parser exists) and
its PSS/E RAW parser fails on v31 header format. The only viable ingestion path is the
MATPOWER `.m` fallback, which requires an external conversion step.

## Context

During G-FNM-1 (intermediate format ingestion gate), three ingestion paths were evaluated:

1. **Intermediate CSV:** PowerModels has no CSV ingestion capability. The intermediate
   format's 17 CSV tables cannot be loaded.

2. **PSS/E v31 RAW:** `PowerModels.parse_file()` fails with a hard error at line 1.
   The parser reads the entire Case Identification line as the `IC` field (integer type),
   which fails because the v31 single-line header contains multiple fields:
   ```
   [error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section CASE
   IDENTIFICATION is not of type Int64.
   ```
   The `import_all=true` flag does not bypass this error.

3. **MATPOWER `.m` fallback:** Loads successfully in 2.97 seconds with correct baseMVA,
   slack bus, and tap ratio handling. However, this is a pre-cleaned derivative with
   fewer records than the raw source.

## Implications

This finding is relevant to the Accessibility dimension -- PowerModels' format support
is limited to MATPOWER `.m` and its own JSON format for practical use. The PSS/E parser
exists but has compatibility issues with real-world v31 files. Analysts working with
ISO-provided FNM data (universally distributed in PSS/E format) would need an external
conversion pipeline before using PowerModels.
