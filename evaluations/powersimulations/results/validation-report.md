# Validation Report — PowerSimulations.jl

## Summary

- **Total result files:** 60
- **Expected test IDs:** 58 (C-5 has SMALL + MEDIUM = 2 files)
- **Gaps:** None
- **Frontmatter violations:** None
- **Naming violations:** None

## Status Distribution

| Status | Count |
|--------|-------|
| informational | 26 |
| pass | 18 |
| qualified_pass | 10 |
| fail | 6 |

## Workaround Class Distribution

| Class | Count |
|-------|-------|
| null | 42 |
| stable | 7 |
| fragile | 7 |
| blocking | 4 |

## Frontmatter Validation

All 60 result files contain required fields:
- test_id: 60/60
- tool: 60/60
- status: 60/60
- protocol_version: 60/60
- skill_version: 60/60
- test_hash: 60/60

## Files by Dimension

| Dimension | Files | Test IDs |
|-----------|-------|----------|
| gate | 3 | G-1, G-2, G-3 |
| expressiveness | 9 | A-1, A-2, A-3, A-4, A-5, A-6, A-9, A-10, A-11, A-12 |
| extensibility | 8 | B-1, B-2, B-3, B-4, B-5, B-6, B-8, B-9 |
| scalability | 10 | C-1, C-2, C-3, C-4, C-5 (×2), C-7, C-8, C-9, C-10 |
| fnm_ingestion | 5 | G-FNM-1, G-FNM-2, G-FNM-3, G-FNM-4, G-FNM-5 |
| accessibility | 5 | D-1, D-2, D-3, D-4, D-5 |
| maturity | 7 | E-1, E-2, E-3, E-4, E-5, E-6, E-7 |
| supply_chain | 9 | F-1, F-2, F-3, F-4, F-5, F-6, F-7, F-8, F-9 |
| p2_readiness | 3 | P2-1, P2-2, P2-3 |

## Warnings

None.
