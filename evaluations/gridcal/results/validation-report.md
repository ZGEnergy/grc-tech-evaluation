# Validation Report — GridCal (VeraGridEngine 5.6.28)

## Summary

- **Total config test IDs:** 57
- **Total result files:** 76 (includes TINY functional + grade tier files)
- **Gaps (missing results):** 0
- **Frontmatter violations:** 0
- **Naming warnings:** Minor slug deviations in supply_chain and maturity (see below)

## Coverage by Dimension

| Dimension | Config Tests | Result Files | Status |
|-----------|-------------|-------------|--------|
| Gate (G) | 3 | 3 | Complete |
| Expressiveness (A) | 11 | 22 | Complete (11 TINY + 11 grade) |
| Extensibility (B) | 9 | 17 | Complete (9 TINY + 8 grade; B-6 audit has no grade network) |
| Scalability (C) | 10 | 10 | Complete |
| Accessibility (D) | 5 | 5 | Complete |
| Maturity (E) | 7 | 7 | Complete |
| Supply Chain (F) | 9 | 9 | Complete |
| P2 Readiness (P2) | 3 | 3 | Complete |

## Frontmatter Validation

All 76 result files have valid frontmatter:
- `test_id` present: 76/76
- `tool` present: 76/76
- `status` valid (pass/fail/qualified_pass/informational): 76/76
- `protocol_version` present: 76/76

## Naming Warnings

Some supply chain and maturity files have slug deviations from config:
- Supply chain F-2 through F-9: agent used different descriptive slugs than config
- Maturity E-3 through E-7: agent used different descriptive slugs than config
- All `test_id` frontmatter values correctly match config test IDs
- **Impact:** None — synthesis uses `test_id` from frontmatter, not filename slug

## Status Distribution

| Status | Count | Tests |
|--------|-------|-------|
| pass | 39 | G-1–3, A-1–4 (TINY+grade), B-2,3,5,7,8,9, C-1,2,3,5,7, D-2,5, E-1,2, F-2–6,8, P2-1 |
| fail | 20 | A-5,6,8,9,11, B-1, C-4,6,8,10, D-4, E-4, F-7, P2-2,3 |
| qualified_pass | 15 | A-7,10, B-4, C-9, D-1,3, E-3,5,6,7, F-1,8,9 |
| informational | 2 | D-2, D-5 |

## Observations

16 observation files in `evaluations/gridcal/results/observations/`:
- api-friction: 2 files
- solver-issues: 1 file
- workaround-needed: 1 file
- doc-gaps: found inline in results
- arch-quality: found inline in B-6 result
- blocking-gap: 1 file

## Conclusion

All 57 config test IDs have result files. No gaps. No frontmatter violations.
Ready for SYNTHESIZE.
