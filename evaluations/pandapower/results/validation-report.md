# Validation Report — pandapower Phase 1 Evaluation

## Summary

- **Files scanned:** 60 result files across 9 dimensions
- **Gaps:** 0
- **Violations:** 0
- **Warnings:** 0

## Coverage

All 59 test IDs from eval-config.yaml have corresponding result files:

| Dimension | Test IDs | Files | Status |
|-----------|----------|-------|--------|
| gate | G-1, G-2, G-3 | 3 | Complete |
| expressiveness | A-1, A-2, A-3, A-4, A-5, A-6, A-9, A-10, A-11, A-12 | 10 | Complete |
| extensibility | B-1, B-2, B-3, B-4, B-5, B-6, B-8, B-9 | 8 | Complete |
| scalability | C-1, C-2, C-3, C-4, C-5, C-7, C-8, C-9, C-10 | 10 | Complete (C-5 has SMALL + MEDIUM) |
| accessibility | D-1, D-2, D-3, D-4, D-5 | 5 | Complete |
| maturity | E-1, E-2, E-3, E-4, E-5, E-6, E-7 | 7 | Complete |
| supply_chain | F-1, F-2, F-3, F-4, F-5, F-6, F-7, F-8, F-9 | 9 | Complete |
| fnm_ingestion | G-FNM-1, G-FNM-2, G-FNM-3, G-FNM-4, G-FNM-5 | 5 | Complete |
| p2_readiness | P2-1, P2-2, P2-3 | 3 | Complete |

## Frontmatter Validation

All result files have:
- Required fields: test_id, tool, dimension, status
- Valid status values (pass/fail/qualified_pass/informational/skip)
- Valid workaround_class values (null/stable/fragile/blocking)
- protocol_version and skill_version present
- test_hash present
- qualified_pass files include Workarounds sections

## Observations

24 observation files in evaluations/pandapower/results/observations/ covering:
- api-friction (5 files)
- arch-quality (2 files)
- cascaded-failure (1 file)
- convergence-quality (1 file)
- doc-gaps (1 file)
- fnm-data-model (3 files)
- fnm-scale (2 files)
- formulation-difference (2 files)
- solver-issues (1 file)
- workaround-needed (9 files)

## Result Status Distribution

| Status | Count |
|--------|-------|
| pass | 24 |
| fail | 12 |
| qualified_pass | 2 |
| informational | 14 |
| skip | 8 |
