# Phase 1: Protocol & Rubric Edits PRDs

This directory contains Product Requirement Documents for Phase 1.

## Deliverable Mapping

| # | PRD | Deliverable |
|---|-----|-------------|
| 01 | [Protocol v8 — G-FNM Input Path and Formulation Annotations](prd-01-protocol-gfnm-formulation.md) | Update Suite G to use intermediate CSVs as primary G-FNM-3/4 input path, add `formulation_difference` tag definition and decision procedure |
| 02 | [Protocol v8 — Thinning and Version Compatibility](prd-02-protocol-thinning-versioning.md) | Remove agent-facing notes from protocol body, add Version Compatibility section, update protocol_version to v8 |
| 03 | [Rubric v6 — Criterion 5 Split and Grade Matrix](prd-03-rubric-criterion5-split.md) | Split Criterion 5 into 5a (Demonstrated Maturity) and 5b (Sustainability Risk), add reviewer concentration sub-metric, define composite grade matrix |

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
| 01 | Protocol v8 — G-FNM Input Path and Formulation Annotations | Phase 0 | 02 |
| 02 | Protocol v8 — Thinning and Version Compatibility | 01 | Phase 2 |
| 03 | Rubric v6 — Criterion 5 Split and Grade Matrix | — | Phase 2 |

**Implementation tiers:**
- **Tier 1:** PRD 01, PRD 03
- **Tier 2:** PRD 02
