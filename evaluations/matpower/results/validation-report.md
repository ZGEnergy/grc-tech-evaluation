# Validation Report — MATPOWER v8.1

Generated: 2026-03-07

## Coverage

- **Total test IDs in config:** 57
- **Result files found:** 57
- **Gaps:** 0

## Status Summary

| Status | Count | Test IDs |
|--------|-------|----------|
| pass | 32 | G-1–G-3, A-1–A-4, A-6–A-9, B-1, B-3–B-5, B-7, B-9, C-1–C-3, C-5, C-7, F-1–F-5, F-7–F-8 |
| qualified_pass | 4 | A-5, A-10, A-11, B-2, B-8, C-9, C-10 |
| fail | 3 | C-4, C-6, C-8 |
| informational | 18 | B-6, D-1–D-5, E-1–E-7, F-6, F-9, P2-1–P2-3 |

## Frontmatter Validation

| Check | Result |
|-------|--------|
| `test_id` present | 57/57 ✓ |
| `tool: matpower` | 57/57 ✓ |
| `protocol_version: "v4"` | 57/57 ✓ |
| `status` valid value | 57/57 ✓ |
| `workaround_class` valid value | 57/57 ✓ |
| `qualified_pass` has workaround section | 5/5 ✓ |

## Naming Convention

All files follow `<test_id>_<slug>.md` or `<test_id>_<slug>_<TIER>.md` pattern. ✓

## Warnings

- **F-6 (distribution_integrity)** and **F-9 (getting_started_integrity)** use `status: informational` rather than pass/fail. These are supply chain gate tests — the findings are not disqualifying but the informational status deviates from the pass/fail expected for gate criteria. The underlying evidence supports a "pass" determination.

## Scalability Failures (Expected)

Three scalability tests failed due to MOST's monolithic formulation hitting solver/memory limits:
- C-4 (SCUC on SMALL): GLPK cannot solve 200K+ variable MILP
- C-6 (Stochastic on SMALL): MIPS cannot solve 1.3M+ variable QP
- C-8 (SCOPF on MEDIUM): 6.4M+ constraint problem exceeds solver capacity

These failures are legitimate scalability findings, not test execution errors.
