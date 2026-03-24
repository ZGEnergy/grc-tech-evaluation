# Validation Report — GridCal Phase 1 Evaluation

**Protocol version:** v11
**Skill version:** v2
**Validation date:** 2026-03-24

## Summary

- **Total test IDs in config:** 59
- **Result files found:** 59/59 (plus 2 dual-tier variants for C-5 and C-8)
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

| Status | Count | Tests |
|--------|-------|-------|
| pass | 22 | G-1, G-2, G-3, A-1, A-2, A-4, A-9, B-2, B-3, B-5, B-8, B-9, C-1, C-2, C-5, C-8, C-9, F-1–F-9 |
| qualified_pass | 6 | A-5, A-6, B-4, C-3, C-4, C-7 |
| partial_pass | 2 | A-3, B-1 |
| constrained_pass | 1 | A-10 |
| fail | 4 | A-11, A-12, C-10, G-FNM-1 |
| informational | 19 | B-6, D-1–D-5, E-1–E-7, G-FNM-3 (qualified_pass), G-FNM-4, G-FNM-5, P2-1–P2-3 |
| skip | 1 | G-FNM-2 (blocked by G-FNM-1) |

## Frontmatter Validation

All result files verified:
- [x] Required YAML frontmatter fields present (test_id, tool, dimension, network, status, workaround_class, protocol_version, skill_version, test_hash, timestamp)
- [x] `protocol_version: v11` in all files
- [x] `skill_version: v2` in all files
- [x] `test_hash` matches eval-config.yaml for all tests
- [x] Valid status values
- [x] Valid workaround_class values
- [x] No blocking + qualified_pass violations

## Observations

34 observation files in `evaluations/gridcal/results/observations/`.

## No Orphaned Files

No result files exist for test IDs not in the current config.
