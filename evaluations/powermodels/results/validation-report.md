# Validation Report — PowerModels Phase 1 Evaluation

**Protocol version:** v10
**Skill version:** v1
**Validated:** 2026-03-14

## Summary

- **Tests in config:** 59
- **Tests with results:** 59
- **Gaps:** 0
- **Frontmatter violations:** 0
- **Naming warnings:** 0

## Dimension Coverage

| Dimension | Tests | All Present |
|-----------|-------|-------------|
| gate | 3 (G-1, G-2, G-3) | Yes |
| expressiveness | 10 (A-1..A-12, excl A-7/A-8) | Yes |
| extensibility | 8 (B-1..B-9, excl B-7) | Yes |
| scalability | 9 (C-1..C-10, excl C-6) | Yes |
| accessibility | 5 (D-1..D-5) | Yes |
| maturity | 7 (E-1..E-7) | Yes |
| supply_chain | 9 (F-1..F-9) | Yes |
| fnm_ingestion | 5 (G-FNM-1..G-FNM-5) | Yes |
| p2_readiness | 3 (P2-1..P2-3) | Yes |

## Orphaned Files Deleted

- expressiveness/A-7_contingency_sweep_{MEDIUM,TINY}.md
- expressiveness/A-8_stochastic_timeseries_{SMALL,TINY}.md
- extensibility/B-7_ac_feasibility_extension_{MEDIUM,TINY}.md
- scalability/C-6_stochastic_dcopf_scale_SMALL.md
- scalability/C-5_contingency_sweep_scale_MEDIUM.md
- Plus 9 stale SMALL/MEDIUM tier files for Suite A/B tests locked to TINY in v10

## Result

**PASS** — All 59 test results present with correct frontmatter. Proceed to synthesis.
