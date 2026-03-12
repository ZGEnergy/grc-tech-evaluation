---
test_id: G-FNM-1
tool: powermodels
dimension: fnm_ingestion
network: LARGE
status: fail
workaround_class: blocking
input_path: psse
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "9b6b545f"
wall_clock_seconds: 84.9
timing_source: measured
---

# G-FNM-1 — FNM Intermediate Ingestion Gate

## Summary

### Result: FAIL

PSS/E v31 RAW parsing failed at line 1 with a hard parser error. MATPOWER `.m` fallback loaded
successfully but all four record-count checks fail — the MATPOWER fallback is a pre-cleaned
derivative of the PSS/E source that has already dropped buses, loads, and branches relative to
the raw model.

## Input Path

- **Attempted:** PSS/E v31 RAW — `AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW`
- **Fallback used:** MATPOWER `.m` — `/workspace/data/fnm/reference/cleaned/fnm_main_island.m`
- `input_path` set to `psse` because PSS/E parsing was attempted (even though it failed and
  fallback was used).

## PSS/E Parse Failure

PowerModels raised a hard error at line 1 of the RAW file:

```

[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section CASE
IDENTIFICATION is not of type Int64.
[error | PowerModels]: Parsing failed at line 1

```

**Root cause:** The RAW v31 header places all Case Identification fields on a single line
(`IC SBASE REV XFRRAT NXFRAT BASFRQ`). PowerModels' PTI parser attempts to read the entire
first line as the `IC` field (integer), which fails because the string includes additional
values after the integer. This is a structural incompatibility: PowerModels does not support
the PSS/E v31 single-line Case Identification header format used by this file.

The `import_all=true` flag does not bypass this error — the failure occurs in the type-parsing
layer before any data is extracted.

## MATPOWER Fallback Results

Parsed `/workspace/data/fnm/reference/cleaned/fnm_main_island.m` in **84.9 seconds**.

```

Buses:     27862
Branches:  32606
Generators: 5741
Loads:      8624

```

PowerModels emitted several warnings during parse:
- 5 branches with `angmin`/`angmax` outside ±90°, clamped to ±60°
- Multiple branch orientation reversals (parallel-branch consistency enforcement)
- Generator cost record count mismatch (5741 generators, 0 cost records)

## Record Count Comparison

| Table              | Manifest Expected | PowerModels Actual | Delta   | % Diff | Status |
|--------------------|------------------:|--------------------|--------:|-------:|--------|
| bus                | 30307             | 27862              | −2445   | −8.1%  | FAIL   |
| load               | 15062             | 8624               | −6438   | −42.7% | FAIL   |
| generator          | 5768              | 5741               | −27     | −0.5%  | FAIL   |
| branch+transformer | 33840             | 32606              | −1234   | −3.6%  | FAIL   |

All four primary tables fail exact-count matching. No table is within 5%.

## Failure Analysis

The count mismatches stem from two distinct causes:

**1. PSS/E parse is unavailable.** PowerModels cannot read the source RAW file directly
(hard parser error, see above). This is a blocking limitation: PowerModels has no path to
ingest the authoritative input format.

**2. MATPOWER fallback is a pre-cleaned model.** The `fnm_main_island.m` file is a
cleaned derivative of the PSS/E source. It excludes isolated buses (`bus_type=4`),
de-energized equipment, and off-island network fragments. The manifest counts reflect the
raw PSS/E record counts before any cleaning, so the comparison is against different model
scopes:

- **bus (−8.1%):** The fallback excludes ~2445 buses, likely isolated or off-island buses
  removed during the cleaning step.
- **load (−42.7%):** The largest discrepancy. The fallback has 8624 vs 15062 in the
  manifest. This suggests the cleaned model removes loads on excluded buses, or that
  the PSS/E source contains many loads on isolated/off-network buses.
- **generator (−0.47%):** Small discrepancy; 27 generators excluded during cleaning.
- **branch+transformer (−3.6%):** 1234 fewer branch/transformer elements, consistent
  with exclusion of branches connected to removed buses.

Even if the PSS/E parse worked, confirming exact-count matches against the manifest
(which counts raw PSS/E records including isolated elements) may require `import_all=True`
semantics or a pre-filter step to match the manifested scope.

## Downstream Impact

G-FNM-1 fails. Per protocol, G-FNM-2 through G-FNM-5 are blocked and must be written
as blocked results.

## Observations Emitted

- `api-friction` — PSS/E v31 RAW parsing fails with a hard incompatibility at the Case
  Identification header. No workaround available within PowerModels.
- `fnm-data-model` — MATPOWER fallback record counts do not match manifest across all
  four primary tables. Bus deficit −8.1%, load deficit −42.7%, generator −0.5%,
  branch −3.6%.
