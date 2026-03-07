# Validation Report — PyPSA v1.1.2

**Generated:** 2026-03-07
**Protocol version:** v4

## Completeness

- **Expected test IDs:** 57
- **Test IDs with result files:** 57 (100%)
- **Total result files:** 76 (includes TINY, SMALL, MEDIUM tier variants)
- **Gaps:** None

## Status Breakdown

| Status | Count |
|--------|-------|
| pass | 45 |
| qualified_pass | 7 |
| fail | 12 |
| informational | 12 |

## Frontmatter Validation

All 76 result files have valid YAML frontmatter with required fields:
- `test_id`: present in all files
- `tool`: present in all files (value: pypsa)
- `dimension`: present in all files
- `status`: present in all files (valid values only)
- `workaround_class`: present in all files
- `protocol_version`: present in all files (value: "v4")
- `timestamp`: present in all files

## Naming Convention

All files follow the `<test_id>_<slug>.md` or `<test_id>_<slug>_<TIER>.md` convention.

## Observation Files

15 observation files in `observations/` directory covering tags:
- api-friction (7 files)
- doc-gaps (2 files)
- workaround-needed (1 file)
- solver-issues (2 files)
- arch-quality (3 files)

## Warnings

None.
