# Phase 0: FNM Intermediate CSV Export & Validation PRDs

This directory contains Product Requirement Documents for Phase 0.

## Deliverable Mapping

| # | PRD | Deliverable |
|---|-----|-------------|
| 01 | [Export Pipeline Script](prd-01-export-pipeline-script.md) | Python script that reads the cleaned MATPOWER case, splits branches/transformers, applies cleaning conventions, and writes per-table CSVs with JSON Schema validation |
| 02 | [Intermediate CSV Materialization](prd-02-csv-materialization.md) | Execute the pipeline in the devcontainer and commit the output CSVs and manifest to `data/fnm/reference/cleaned/intermediate/` |
| 03 | [dcpf_reference.py Separate-Table Support](prd-03-dcpf-reference-update.md) | Update dcpf_reference.py to accept separate branch and transformer CSVs and read baseMVA from the sidecar manifest |
| 04 | [DCPF Reference Reproducibility Validation](prd-04-dcpf-reproducibility-validation.md) | Validate that the DCPF reference solution computed from intermediate CSVs matches the existing reference to floating-point tolerance |

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
| 01 | Export Pipeline Script | — | 02, 03 |
| 02 | Intermediate CSV Materialization | 01 | 04 |
| 03 | dcpf_reference.py Separate-Table Support | 01 | 04 |
| 04 | DCPF Reference Reproducibility Validation | 02, 03 | — |

**Implementation tiers:**
- **Tier 1:** PRD 01
- **Tier 2:** PRD 02, PRD 03
- **Tier 3:** PRD 04
