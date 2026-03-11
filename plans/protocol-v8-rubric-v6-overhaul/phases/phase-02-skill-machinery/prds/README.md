# Phase 2: Skill Machinery Updates PRDs

This directory contains Product Requirement Documents for Phase 2.

## Deliverable Mapping

| # | PRD | Deliverable |
|---|-----|-------------|
| 01 | [New Reference: test-methodology-notes.md](prd-01-test-methodology-notes.md) | Create `references/test-methodology-notes.md` with agent-facing implementation notes extracted from protocol v8 thinning |
| 02 | [Updated Reference: cross-tool-watchpoints.md](prd-02-cross-tool-watchpoints.md) | Add Suite G format context, formulation sophistication catalog, post-ingestion fidelity checks, baseMVA/Q-limit pitfalls, and PowerModels solve_dc_pf pitfall sections |
| 03 | [Updated Prompt: research-prompt.md](prd-03-research-prompt-version.md) | Add 4th version-awareness research agent with structured capability report schema |
| 04 | [Updated Prompt: code-evaluator-prompt.md](prd-04-code-evaluator-prompt.md) | G-FNM intermediate CSV input path, ingestion count verification gate, formulation_difference tag procedure, version capability report consumption |
| 05 | [Updated Prompt: audit-evaluator-prompt.md](prd-05-audit-evaluator-prompt.md) | Expand E-3 with reviewer/approval concentration sub-metric for rubric v6 Criterion 5b |
| 06 | [Updated Orchestrator: SKILL.md](prd-06-skill-md-orchestrator.md) | 4th research agent dispatch in RESEARCH state, version capability report consumer contract in EVALUATE state |
| 07 | [Updated Prompt: config-generator-prompt.md](prd-07-config-generator-prompt.md) | formulation_difference tag vocabulary, protocol_version v8, 5a/5b encoding, LARGE tier CSV path |

## PRD Structure

Each PRD follows a consistent structure:
1. **Overview** — Brief description of the component
2. **Goals** — What the component achieves
3. **Non-Goals** — Explicit scope boundaries
4. **Data Structures** — Key classes and interfaces
5. **API** — Function signatures
6. **Success Criteria** — Unit tests that must pass
7. **File Location** — Where the code lives
8. **Repository** — Which repo the code belongs to
9. **Dependencies** — Required modules
10. **Open Questions** — Unresolved design decisions

## Dependency Graph

| # | PRD | Depends On | Enables |
|---|-----|-----------|---------|
| 01 | test-methodology-notes.md | Phase 1 D2 | Phase 3 |
| 02 | cross-tool-watchpoints.md | — | 04 |
| 03 | research-prompt.md | — | 04, 06 |
| 04 | code-evaluator-prompt.md | 02, 03 | 06 |
| 05 | audit-evaluator-prompt.md | — | Phase 3 |
| 06 | SKILL.md | 03, 04 | Phase 3 |
| 07 | config-generator-prompt.md | Phase 1 | Phase 3 |

**Implementation tiers:**
- **Tier 1:** PRD 01, PRD 02, PRD 03, PRD 05, PRD 07
- **Tier 2:** PRD 04
- **Tier 3:** PRD 06
