# Validation Report — pandapower v3.4.0

**Date:** 2026-03-06
**Protocol version:** v4

## Coverage

All 57 test IDs from eval-config.yaml have corresponding result files:

| Dimension | Test IDs | Result Files | Complete |
|-----------|----------|-------------|----------|
| gate | G-1..G-3 | 3 | Yes |
| expressiveness | A-1..A-11 | 22 (11 TINY + 11 grade) | Yes |
| extensibility | B-1..B-9 | 16 (9 TINY + 7 grade) | Yes |
| scalability | C-1..C-10 | 10 | Yes |
| accessibility | D-1..D-5 | 5 | Yes |
| maturity | E-1..E-7 | 7 | Yes |
| supply_chain | F-1..F-9 | 9 | Yes |
| p2_readiness | P2-1..P2-3 | 3 | Yes |
| **Total** | **57** | **75 result + 19 observation** | **Yes** |

## Frontmatter Validation

All 75 result files contain required frontmatter fields:
- `test_id`: present in all
- `status`: present in all (valid values: pass/fail/qualified_pass/informational)
- `protocol_version`: present in all ("v4")
- `tool`: present in all ("pandapower")

19 observation files follow observation schema (tag, source_dimension, source_test, severity).

## Status Distribution

| Status | Count |
|--------|-------|
| pass | 41 |
| fail | 16 |
| qualified_pass | 14 |
| informational | 4 |

## Gaps

None. All 57 test IDs are covered.

## Warnings

- Observation file naming is consistent with observation-schema.md
- Some tests have both TINY and grade-network result files (expected for expressiveness/extensibility)
- B-6 (code_architecture) and B-7 (ac_feasibility_extension) have single files (no tier variant — correct, as these are N/A tier)

## Conclusion

Validation passed. All test IDs covered, all frontmatter valid, no gaps. Ready for synthesis.
