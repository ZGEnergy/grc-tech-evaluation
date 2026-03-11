# Phase 3: Validation PRDs

This directory contains Product Requirement Documents for Phase 3.

## Deliverable Mapping

| # | PRD | Deliverable |
|---|-----|-------------|
| 01 | [Config Generation Smoke Test](prd-01-config-smoke-test.md) | Run config-generator against v8 protocol for pypsa, validate structural correctness of output eval-config.yaml |
| 02 | [Cross-Reference Checklist](prd-02-cross-reference-checklist.md) | Map each of 8 GitHub issues (#43, #48, #49, #54, #55, #56, #57, #59) to fix locations in protocol, rubric, and skill files |
| 03 | [Protocol-to-Skill Traceability Audit](prd-03-traceability-audit.md) | Bidirectional test ID traceability, PHASE2 marker cleanup verification, cross-reference integrity between skill files |

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
| 01 | Config Generation Smoke Test | Phase 1, Phase 2 | — |
| 02 | Cross-Reference Checklist | Phase 1, Phase 2 | — |
| 03 | Protocol-to-Skill Traceability Audit | Phase 1, Phase 2 | — |

**Implementation tiers:**
- **Tier 1:** PRD 01, PRD 02, PRD 03 (all independent; can proceed in parallel)
