# Validation Report — PowerModels Phase 1 Evaluation

**Protocol version:** v11
**Skill version:** v2
**Validated:** 2026-03-24

## Summary

- **Config tests:** 59
- **Result files found:** 59
- **Gaps:** 0
- **Violations:** 0
- **Warnings:** 0

## Status Distribution

| Status | Count | Tests |
|--------|-------|-------|
| pass | 23 | G-1, G-2, G-3, A-3, A-4, A-12, B-1, B-3, B-4, B-5, B-6, B-9, C-9, F-1, F-2, F-4, F-5, F-6, F-7, E-1, E-4, E-6, D-3 |
| qualified_pass | 19 | A-1, A-2, A-6, A-9, A-10, B-2, B-8, C-1, C-3, C-7, D-1, D-2, D-4, E-2, E-5, E-7, F-3, F-8, F-9 |
| constrained_pass | 1 | C-8 |
| fail | 8 | A-5, A-11, C-2, C-4, C-10, E-3, G-FNM-1, G-FNM-3 |
| skip | 1 | G-FNM-2 |
| informational | 7 | C-5, D-5, G-FNM-4, G-FNM-5, P2-1, P2-2, P2-3 |

## Cascaded Failures

| Failed Test | Blocked Tests | Reason |
|-------------|---------------|--------|
| A-5 (SCUC unsupported) | A-6 (ed_only), C-4 | No native UC formulation |
| A-11 (distributed slack unsupported) | C-10 | No distributed slack API |
| C-2 (ACPF MEDIUM diverges) | — | Ipopt diverges at 10k-bus scale |
| G-FNM-1 (no CSV ingestion) | G-FNM-2 | No intermediate format parser |

## Test Hash Verification

All 59 test hashes match the v11 eval-config. 12 supply chain + P2 files were corrected post-evaluation for hash alignment.

## Frontmatter Compliance

All result files contain required frontmatter fields: test_id, tool, dimension, network, status, workaround_class, timestamp, protocol_version, skill_version, test_hash.
