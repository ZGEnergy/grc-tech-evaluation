# Sweep Validation Report — v10 → v11

**Date:** 2026-03-15

## Checks Passed: 14 / 14

### Findings Report (`sweep-reports/v10-to-v11.md`)

| Check | Result |
|-------|--------|
| File exists | ✓ (514 lines) |
| Executive Summary present | ✓ |
| Cross-Tool Comparison Matrices present | ✓ |
| Low-Signal Tests section present | ✓ |
| Spot-Check Probe Results present | ✓ |
| Proposed Changes section present | ✓ |
| Test-ID Mapping Table present | ✓ |
| GitHub Issue Triage section present | ✓ |
| Deferred Items section present | ✓ |
| Methodology section present | ✓ |
| All PC-01–PC-17 referenced in report | ✓ |

### Protocol / Rubric

| Check | Result |
|-------|--------|
| Protocol stamped v11 | ✓ (version history table entry 2026-03-15) |
| Rubric stamped v11 | ✓ (version history table entry 2026-03-15) |
| PC-01 (C-SMALL gate decoupling) reflected in protocol | ✓ (Suite C gating structure section, line 327) |
| PC-07 (five-tier outcomes) reflected in rubric | ✓ (partial_pass, constrained_pass present) |
| PC-10 (DCOPF hard constraints) in protocol | ✓ (A-3 pass condition: max_loading ≤ 1.0 + 1e-4) |
| All proposed changes referenced in protocol changelog | ✓ |
| Protocol and rubric internally consistent | ✓ |

### Skill Files

| File | Lines | Status |
|------|-------|--------|
| references/cross-tool-watchpoints.md | 503 | ✓ 5 new watchpoints added |
| references/result-template.md | 183 | ✓ New frontmatter fields added |
| references/workaround-classification.md | 166 | ✓ Five-tier outcome system documented |
| references/convergence-protocol.md | 113 | ✓ Four-tier evidence hierarchy added |
| prompts/code-evaluator-prompt.md | 550 | ✓ Verification guardrails added |
| prompts/config-generator-prompt.md | 378 | ✓ v11 version, gate_minimum_bar, C-suite gate logic |
| prompts/synthesis-prompt.md | 194 | ✓ Pass rate exclusion rules added |
| prompts/audit-evaluator-prompt.md | 250 | ✓ JLL binary license audit added |
| SKILL.md | 550 | ✓ Outcome tiers, gate logic, cascade logic updated |

### Cross-Reference Consistency

| Check | Result |
|-------|--------|
| All PC-01–PC-17 appear in findings report | ✓ |
| All PC-01–PC-17 appear in aggregation/proposed-changes.yaml | ✓ |
| No in-scope GitHub issues missing from report | ✓ (zero issues found) |
| Deferred items have rationale | ✓ (6 deferred items with rationale) |

## No Issues Found

Validation completed with 0 failures. All outputs are complete and internally consistent.

## Output Summary

- **Findings report:** `sweep-reports/v10-to-v11.md` (514 lines)
- **Updated protocol:** `evaluation_guides/Phase1_Test_Protocol.md` (483 lines, v11)
- **Updated rubric:** `evaluation_guides/Phase1_Evaluation_Rubric.md` (471 lines, v11)
- **Updated skill:** `.claude/skills/evaluate-tool/` (9 files modified)
- **Sweep data:** `sweep-data/v10-to-v11/` (per-tool findings, probes, aggregation)
