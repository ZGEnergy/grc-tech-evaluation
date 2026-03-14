# Validation Report — GridCal Phase 1 Evaluation

## Summary

- **Total test IDs in config:** 59
- **Result files found:** 61 (C-5 and C-8 have SMALL + MEDIUM variants)
- **Gaps:** 0
- **Frontmatter violations:** 0
- **Naming warnings:** 0

## Coverage by Dimension

| Dimension | Expected | Found | Status |
|-----------|----------|-------|--------|
| Gate (G) | 3 | 3 | Complete |
| Expressiveness (A) | 10 | 10 | Complete |
| Extensibility (B) | 8 | 8 | Complete |
| Scalability (C) | 9 | 11 (2 dual-tier) | Complete |
| Accessibility (D) | 5 | 5 | Complete |
| Maturity (E) | 7 | 7 | Complete |
| Supply Chain (F) | 9 | 9 | Complete |
| FNM Ingestion (G-FNM) | 5 | 5 | Complete |
| P2 Readiness (P2) | 3 | 3 | Complete |
| **Total** | **59** | **61** | **Complete** |

## Status Distribution

| Status | Count |
|--------|-------|
| pass | 38 |
| fail | 5 (A-11, A-12, C-10, G-FNM-1, G-FNM-2*) |
| qualified_pass | 5 (A-10, B-1, B-4, C-4, G-FNM-3) |
| informational | 13 (D-1..D-5, E-1..E-7, G-FNM-4, G-FNM-5, B-6) |
| skip | 1 (G-FNM-2, blocked_by: G-FNM-1) |

*G-FNM-2 status is `skip` (blocked), not `fail`

## Frontmatter Validation

All 61 result files contain required fields:
- `test_id` ✓
- `tool` ✓
- `dimension` ✓
- `status` ✓
- `protocol_version` ✓
- `skill_version` ✓
- `test_hash` ✓

## Observations

24 observation files in `evaluations/gridcal/results/observations/`.
