# Report Data Directory

Single source of truth for all quantitative content on the report site.

## Files

| File | Purpose | Records | Source Material |
|------|---------|---------|-----------------|
| `grades.json` | Tier grades for 6 tools x 6 criteria | 36 grade entries | Per-tool synthesis files |
| `sensitivity.json` | Ranking scenarios (baseline + 3 alternatives) | 3 scenarios | Mechanical ranking recomputation |
| `risk-register.json` | Risks for the selected tool (PyPSA) | 5 risks | Synthesis evidence |
| `head-to-head.json` | Phase 2 capability comparison matrix | 6 capabilities x 6 tools | Synthesis files and P2 readiness findings |
| `tool-profiles.json` | Metadata for each evaluated tool | 6 tools | Synthesis files (all 6 tools) |
| `test-results.json` | Per-tool, per-suite test outcomes | 6 tools x 8 suites | `evaluations/*/results/synthesis.md` |

## Schema Conventions

### Provenance

Every JSON file has a `_provenance` key at the top level containing:

- `source` or `sources`: path(s) to the source file(s) relative to repo root
- `extracted`: ISO date when data was extracted

### Grade Scale

Grades use a 4-tier system mapped to numeric values:

```
Strong   = 3
Adequate = 2
Weak     = 1
Failing  = 0
```

### Test Results

Test outcomes are normalized to three values:
- `pass`: includes both `P` (pass) and `QP` (qualified_pass) from the comparison matrix
- `fail`: `F` in the comparison matrix
- `skip`: `--` (not attempted/blocked) or `I` (informational) in the comparison matrix

### Tool Identifiers

Canonical tool IDs used across all files:
- `pypsa`, `pandapower`, `powermodels`, `matpower`, `gridcal`, `powersimulations`

### Criteria Identifiers

Canonical criterion IDs:
- `expressiveness`, `extensibility`, `scalability`, `accessibility`, `maturity`, `supply_chain`

## Consumers

These JSON files are consumed by:
- Report site components (charts, tables, grade badges)
- Validation scripts
- Cross-referencing between report sections

## Source Material

Primary sources for data extraction:
- **Synthesis files**: `evaluations/*/results/synthesis.md` (all 6 tools)
- **Selection report**: `report/selection-report-v11.md` (grades, rankings, risks, head-to-head)
