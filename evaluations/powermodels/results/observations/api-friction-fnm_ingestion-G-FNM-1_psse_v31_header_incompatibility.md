# Observation: api-friction — PSS/E v31 RAW Header Parse Failure

**observation_type:** api-friction
**test_id:** G-FNM-1
**dimension:** fnm_ingestion
**tool:** powermodels
**severity:** blocking
**timestamp:** 2026-03-11T00:00:00Z

## Finding

PowerModels `parse_file()` / `parse_psse()` fails with a hard error when reading a PSS/E v31
RAW file whose Case Identification record uses the standard single-line format:

```

0    100.00 31  0  0    0.0

```

The parser attempts to read this entire line as the `IC` field (an integer), fails because the
string contains additional whitespace-separated values, and raises an unrecoverable error before
reading any bus, branch, or generator data.

### Error produced:

```

[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section CASE
IDENTIFICATION is not of type Int64.
Parsing failed at line 1

```

## Scope

- Affects: `PowerModels.parse_file("*.raw")`, `PowerModels.parse_psse("*.raw")`
- `import_all=true` does not bypass the error
- File: `AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW` (PSS/E v31, production FNM)

## Workaround

No in-tool workaround available. To use PowerModels with PSS/E data, external pre-processing
is required to convert the RAW file to MATPOWER `.m` format (e.g., via MATPOWER's
`psse2mpc()` in Octave, or an equivalent Python/Julia converter). This is a significant
operational burden for production FNM workflows.

## Impact

G-FNM-1 fails on the primary PSS/E input path. The MATPOWER fallback can be loaded but
has cleaned data that diverges from manifest counts. All downstream G-FNM tests (2–5)
are blocked.
