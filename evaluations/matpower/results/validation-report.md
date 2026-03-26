# Validation Report — MATPOWER Phase 1 Evaluation

**Protocol version:** v11
**Skill version:** v2
**Validated:** 2026-03-24

## Completeness

All 59 test IDs from eval-config.yaml have corresponding result files.

| Dimension | Expected | Found | Status |
|-----------|----------|-------|--------|
| gate | 3 | 3 | Complete |
| expressiveness | 10 | 10 | Complete |
| extensibility | 8 | 8 | Complete |
| scalability | 10 | 14 (tier-specific) | Complete |
| accessibility | 5 | 5 | Complete |
| maturity | 7 | 7 | Complete |
| supply_chain | 9 | 9 | Complete |
| fnm_ingestion | 5 | 5 | Complete |
| p2_readiness | 3 | 3 | Complete |
| **Total** | **59** | **64 files** | **Complete** |

## Frontmatter Validation

- All files have required fields: test_id, tool, dimension, protocol_version, skill_version, test_hash, status, workaround_class, timestamp
- All files have `protocol_version: v11` and `skill_version: v2`
- All test_hashes match eval-config.yaml
- All status values are valid (pass, fail, qualified_pass, partial_pass, constrained_pass, informational, skip)

## Gaps

None.

## Violations

None.

## Warnings

None.

## Test Status Summary

| Status | Count |
|--------|-------|
| pass | 34 |
| fail | 5 (A-9, A-10, C-4 SMALL, C-8, G-FNM-1) |
| qualified_pass | 3 (A-11, B-1, B-5, C-10) |
| constrained_pass | 2 (A-5, A-12) |
| informational | 10 (B-6, C-5 SMALL/MED, D-1..D-5, G-FNM-4) |
| skip | 2 (C-4 MEDIUM, G-FNM-2) |
