---
test_id: P2-1
tool: powermodels
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T23:30:00Z"
protocol_version: v10
skill_version: v1
test_hash: "4ce7559b"
---

# P2-1: PSS/E RAW Parsing

## Summary

PowerModels.jl v0.21 includes a built-in PSS/E RAW parser (`parse_file("case.raw")`),
but support is limited to PSS/E RAW version 33. The FNM file in this evaluation is
**version 31**, which caused a parse failure due to an integer-type mismatch in the
CASE IDENTIFICATION section header. RAW v34 is not supported (open GitHub issue #921,
unresolved as of March 2026).

## Test Results

### FNM RAW File Parse Attempt

**File:** `/data/fnm-source/AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW`

#### FNM RAW version detected from file header:

```

Line 1:  0    100.00 31  0  0    0.0
Line 3: VER 31

```

The file is PSS/E RAW **version 31**.

#### Parse result:

```

[info | PowerModels]: The PSS(R)E parser currently supports buses, loads, shunts,
  generators, branches, transformers, and dc lines
[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section
  CASE IDENTIFICATION is not of type Int64.
[error | PowerModels]: Parsing failed at line 1: value '0    100.00 31  0  0    0.0'
  for IC in section CASE IDENTIFICATION is not of type Int64.
PSS/E parse FAILED: ErrorException("Parsing failed at line 1: ...")

```

The parser expected the IC (case identification) field to be a plain integer but the
FNM file has a non-standard format for that field (`0    100.00 31  0  0    0.0` where
the entire first record is concatenated). This is a version 31 format incompatibility,
not a version 34 issue.

## Capability Assessment

| Dimension | Finding |
|---|---|
| PSS/E parsing capability | Partial — parser exists but fails on this RAW v31 file |
| Supported RAW versions (documented) | v33 only |
| Supported RAW versions (tested) | v33 (per GitHub history); v31 failed on FNM file |
| FNM parse outcome | FAILED (IC field type mismatch on line 1) |
| RAW v34 support | Not supported (GitHub issue #921, filed Jul 2024, unresolved) |

### Known Open Issues (PSS/E Parser)

At least 12 open GitHub issues target the PTI/PSS/E parser:
- **#921** (Jul 2024): No support for RAW v34
- **#932** (Oct 2024): Incorrect behavior for active generators at load-type buses in PTI files
- **#918, #897, #893, #888, #856, #843, #842, #794, #749, #737**: Various field
  handling issues (blank fields, VSC data, transformer angle offsets >60°)

The parser is described in PowerModels documentation as supporting buses, loads, shunts,
generators, branches, transformers, and DC lines — but not FACTS, HVDC (VSC), or
switched shunts beyond basic shunts.

## Effort Estimate

### To fix PSS/E v31 parsing of the FNM file
#### Effort: LOW (1–2 days)

The FNM parse failure is on line 1 of the CASE IDENTIFICATION section — the IC field
parser expects a plain `Int64` but receives a string that includes additional columns.
This is a localized fix in the `parse_psse.jl` source file. The PSS/E v31 CASE
IDENTIFICATION format allows the entire first record on one line with space-separated
fields; the parser is not splitting correctly.

The fix would require:
1. Locating the `parse_case_identification` function in `PowerModels/src/io/psse.jl`
2. Changing the IC field parser to split on whitespace and take the first token only
3. Submitting a PR upstream (open-source fix)

No new parser infrastructure is required — the fix is a single-function correction.

### To add PSS/E v34 support
#### Effort: MEDIUM (2–4 weeks)

RAW v34 introduced several format changes relative to v33, including new section types
and modified field layouts. The existing v33 parser would need:
1. Version detection in the header (already present — the parser reads the version field)
2. Conditional parsing branches for v34-specific sections
3. Testing against v34 reference files

This is not a trivial change but also not a full rewrite — the parser architecture is
modular by section type. Community issue #921 documents this gap; no PR has been filed.

## Phase 2 Integration Impact

For Phase 2, if the production network model is delivered in PSS/E RAW format:
- **If v33 format**: parsing likely works with `import_all=true`, but the 12+ open
  issues indicate field-handling fragility on real-world files
- **If v31 format** (as in this evaluation's FNM file): parse fails on line 1 with a
  fixable one-liner bug
- **If v34 format**: not supported; requires 2–4 weeks of parser development or
  conversion to v33/MATPOWER format upstream

The safest Phase 2 ingestion path is to convert the network model to MATPOWER `.m`
format (which PowerModels parses reliably) rather than relying on the PSS/E parser.

## Recorded Metrics

| Metric | Value |
|---|---|
| psse_parsing_capability | partial (parser exists; FNM v31 parse fails) |
| supported_raw_versions | v33 (documented); v31 fails (FNM file); v34 not supported |
| effort_estimate_if_absent | LOW for v31 fix; MEDIUM for v34 support |
| fnm_parse_outcome | FAILED — IC field type error on line 1 |
| fnm_raw_version | 31 |
| open_issues_psse_parser | 12+ as of March 2026 |
