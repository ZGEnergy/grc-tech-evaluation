# Validation Report — PowerSimulations.jl

**Generated:** 2026-03-24
**Protocol version:** v11
**Skill version:** v2

## Completeness

| Category | Count |
|----------|-------|
| Tests in config | 59 |
| Result files found | 60 (C-5 has SMALL + MEDIUM tier files) |
| Gaps | 0 |
| Orphaned files | 0 |

## Status Distribution

| Status | Count |
|--------|-------|
| pass | 20 |
| informational | 26 |
| qualified_pass | 5 |
| partial_pass | 2 |
| constrained_pass | 1 |
| fail | 5 |
| skip | 1 |

## Dimension Coverage

| Dimension | Files | Notes |
|-----------|-------|-------|
| gate | 3 | G-1, G-2, G-3 all pass |
| expressiveness | 10 | A-1 through A-12 |
| extensibility | 8 | B-1 through B-9 |
| scalability | 10 | C-1 through C-10 (C-5 has 2 tier files) |
| accessibility | 5 | D-1 through D-5 |
| maturity | 7 | E-1 through E-7 |
| supply_chain | 9 | F-1 through F-9 |
| fnm_ingestion | 5 | G-FNM-1 through G-FNM-5 |
| p2_readiness | 3 | P2-1 through P2-3 |

## Frontmatter Validation

- **Violations:** 0
- **Warnings:** 0
- All required fields present in all files
- All status values valid
- All workaround_class values valid
- All protocol_version = v11
- All skill_version = v2
- All test_hash values match config

## Naming Validation

All files follow `<test_id>_<slug>.md` or `<test_id>_<slug>_<TIER>.md` convention.

## Summary

**No gaps, no violations, no warnings.** All 59 test IDs have corresponding result files with valid frontmatter. Ready for synthesis.
