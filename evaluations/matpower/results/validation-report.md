# Validation Report — MATPOWER Phase 1 Evaluation

**Generated:** 2026-03-13
**Protocol:** v10 | **Skill:** v1

## Coverage

All 56 test IDs from eval-config.yaml have corresponding result files (63 total files, accounting for SMALL+MEDIUM tier variants).

| Dimension | Test IDs | Result Files | Status |
|-----------|----------|-------------|--------|
| Gate | G-1, G-2, G-3 | 3 | Complete |
| Expressiveness (A) | A-1..A-12 (10 tests) | 10 | Complete |
| Extensibility (B) | B-1..B-9 (8 tests) | 8 | Complete |
| Scalability (C) | C-1..C-10 (9 tests) | 13 (SMALL+MEDIUM) | Complete |
| Accessibility (D) | D-1..D-5 | 5 | Complete |
| Maturity (E) | E-1..E-7 | 7 | Complete |
| Supply Chain (F) | F-1..F-9 | 9 | Complete |
| FNM Ingestion (G) | G-FNM-1..G-FNM-5 | 5 | Complete |
| P2 Readiness | P2-1..P2-3 | 3 | Complete |

## Gaps

**None.** All 56 test IDs have result files.

## Status Distribution

| Status | Count | Details |
|--------|-------|---------|
| pass/PASS | 27 | Core PF/OPF, extensibility, supply chain, gate |
| qualified_pass | 6 | A-5, A-11, A-12, B-1, B-4, B-5 |
| fail | 4 | A-9, A-10, C-4, G-FNM-1 |
| informational | 17 | D-1..D-5, E-1..E-7, G-FNM-4, G-FNM-5 |
| skip | 9 | 8 MEDIUM scalability (C-SMALL-gate) + G-FNM-2 |

## Frontmatter Validation

All 63 result files have complete frontmatter:
- test_id: present in all
- tool: matpower in all
- dimension: present in all
- network: present in all
- status: valid value in all
- workaround_class: present in all
- protocol_version: v10 in all
- skill_version: v1 in all
- test_hash: present in all

## Naming Convention

All files follow `<test_id>_<slug>.md` or `<test_id>_<slug>_<TIER>.md` pattern.

## Warnings

1. **Case inconsistency:** Gate test results use `PASS` (uppercase) while other tests use `pass` (lowercase). Both are valid per schema but inconsistent.

2. **MEDIUM scalability skipped:** All 8 MEDIUM-tier scalability tests were skipped due to C-SMALL-gate (C-4 cascaded failure from A-5 GLPK wrapper bug). This is a protocol-correct outcome but limits scalability evidence.

## Observations

16 observation files emitted across 7 tags:
- solver-issues: 6
- api-friction: 2
- arch-quality: 2
- fnm-scale: 2
- cascaded-failure: 1
- convergence-quality: 1
- workaround-needed: 1
- fnm-data-model: 1

## Conclusion

Validation passes. All test IDs covered, all frontmatter complete. Ready for synthesis.
