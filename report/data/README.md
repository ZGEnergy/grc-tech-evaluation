# Report Data Directory

Single source of truth for all quantitative content on the report site.

## Files

| File | Purpose | Records | Source Material |
|------|---------|---------|-----------------|
| `grades.json` | Letter and numeric grades for 6 tools x 6 criteria | 36 grade entries | `report/selection-report-v10.md` |
| `sensitivity.json` | Ranking scenarios (baseline + 3 alternatives) | 4 scenarios | `report/selection-report-v10.md` |
| `risk-register.json` | Risks for the selected tool (PyPSA) | 5 risks | `report/selection-report-v10.md` |
| `head-to-head.json` | Phase 2 capability comparison matrix | 6 capabilities | `report/selection-report-v10.md` |
| `sweep-themes.json` | Cross-cutting themes from v4-to-v5 sweep | 13 themes | `sweep-data/v4-to-v5/aggregation/themes.md` |
| `probe-results.json` | All 18 spot-check probes with verdicts | 18 probes | `sweep-data/v4-to-v5/probes/*/probe-*.md` |
| `tool-profiles.json` | Metadata for each evaluated tool | 6 tools | Synthesis files (all 6 tools) |
| `test-results.json` | Per-tool, per-suite test outcomes | 6 tools x 8 suites | `evaluations/*/results/synthesis.md` |

## Schema Conventions

### Provenance

Every JSON file has a `_provenance` key at the top level containing:

- `source` or `sources`: path(s) to the source file(s) relative to repo root
- `lines` (optional): line range in the source file
- `extracted`: ISO date when data was extracted

### Grade Scale

Grades use a 13-point letter scale mapped to numeric values:

```
A+ = 4.3, A = 4.0, A- = 3.7
B+ = 3.3, B = 3.0, B- = 2.7
C+ = 2.3, C = 2.0, C- = 1.7
D+ = 1.3, D = 1.0, D- = 0.7
F  = 0.0
```

### Test Results

Test outcomes are normalized to three values:
- `pass`: includes both `P` (pass) and `QP` (qualified_pass) from the comparison matrix
- `fail`: `F` in the comparison matrix
- `skip`: `--` (not attempted/blocked) or `I` (informational) in the comparison matrix

### Probe Verdicts

Probes use three verdict categories:
- `DEBUNKED`: original claim was incorrect (4 probes)
- `CONFIRMED`: original claim was verified (10 probes with protocol implications)
- `PARTIALLY_CONFIRMED`: claim was directionally correct but attribution was wrong (4 probes)

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
- **Selection report**: `report/selection-report-v10.md` -- grades, rankings, risks, head-to-head
- **Themes analysis**: `sweep-data/v4-to-v5/aggregation/themes.md` -- 13 cross-cutting themes
- **Probe results**: `sweep-data/v4-to-v5/probes/*/probe-*.md` -- 18 individual probe files
- **Synthesis files**: `evaluations/*/results/synthesis.md` -- all 6 tools available (pypsa, pandapower, powermodels, matpower, gridcal, powersimulations)
- **Sweep findings**: `sweep-data/v4-to-v5/per-tool/*/findings.md` -- per-tool sweep findings for all 6 tools
