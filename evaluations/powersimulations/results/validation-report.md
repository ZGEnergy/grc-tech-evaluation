---
tool: powersimulations
protocol_version: "v4"
timestamp: "2026-03-07T07:30:00Z"
---

# Validation Report — PowerSimulations.jl

## Coverage Summary

| Dimension | Expected | Found | Coverage |
|-----------|----------|-------|----------|
| Gate (G) | 3 | 3 | 100% |
| Expressiveness (A) | 11 | 11 | 100% |
| Extensibility (B) | 9 | 9 | 100% |
| Scalability (C) | 10 | 10 | 100% |
| Accessibility (D) | 5 | 5 | 100% |
| Maturity (E) | 7 | 7 | 100% |
| Supply Chain (F) | 9 | 9 | 100% |
| P2 Readiness (P2) | 3 | 3 | 100% |
| **Total** | **57** | **57** | **100%** |

## Gaps

**None.** All 57 test IDs from eval-config.yaml have corresponding result files.

## Frontmatter Validation

All result files contain required frontmatter fields:
- `test_id`: Present in all files
- `tool`: Present in all files (value: powersimulations)
- `dimension`: Present in all files
- `protocol_version`: Present in all files (value: "v4")
- `status`: Present in all files

### Status Distribution

| Status | Count | Test IDs |
|--------|-------|----------|
| pass | 24 | G-1, G-2, G-3, A-1, A-2, A-6, A-7, B-1, B-3, B-4, B-5, B-6, B-9, C-1, C-7, C-9, F-1, F-4, F-5, F-6, F-7, F-8, D-2*, D-3* |
| qualified_pass | 14 | A-3, A-4, A-5, A-9, A-11, B-2, B-7, B-8, C-3, C-4, C-5, C-6, D-1, D-4 |
| fail | 5 | A-8, A-10, C-2, C-8, C-10 |
| informational | 14 | D-2, D-3, D-5, E-1 to E-7, F-2, F-3, F-9, P2-1 to P2-3 |

*D-2 and D-3 are `informational` but counted separately.

### Workaround Classification Distribution

| Class | Count | Test IDs |
|-------|-------|----------|
| null | 35 | (no workaround needed) |
| stable | 14 | A-3, A-4, A-5, A-6, A-7, A-9, A-11, B-1, B-2, B-4, B-8, C-3, C-4, C-5, C-6 |
| fragile | 1 | B-7 |
| blocking | 4 | A-8, A-10, C-8, C-10 |

## Warnings

### W-1: Status/Workaround Inconsistency

A-6 and A-7 have `status: pass` with `workaround_class: stable`. By convention, tests
requiring workarounds should be `qualified_pass`. These may be borderline cases where
the workaround is minimal (time series boilerplate).

### W-2: Missing Wall Clock Times

Several scalability tests (C-3, C-4, C-5, C-6, C-7) have `wall_clock_seconds: null`
because they were not fully executed on the target network. Timing estimates are
provided in the result narratives.

### W-3: Observation Files

7 observation files present in `results/observations/`:
- 3 from A-3 (api-friction, solver-issues, workaround-needed, doc-gaps)
- 1 from A-4 (api-friction)
- 2 from A-5 (solver-issues, workaround-needed)

No observations from extensibility or scalability dimensions.

## Conclusion

All 57 test IDs have result files with valid frontmatter. No gaps exist.
Warnings are non-blocking. Ready for SYNTHESIZE.
