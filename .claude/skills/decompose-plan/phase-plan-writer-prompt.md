# Phase Plan Writer — Subagent Prompt Template

Write a phase plan for Phase {{phase_number}}: {{phase_name}}.

**Detail level:** `{{detail_level}}`

<!-- Guard: This prompt is never invoked for Tier 1 (task_card). The orchestrator skips DECOMPOSE_PHASES entirely for Tier 1. -->

## Context

### Executive Plan Summary

{{executive_summary}}

### Prior Phase Summaries

{{prior_phase_summaries}}

### Resolved Open Questions

{{resolved_oqs}}

## Instructions

Write a phase plan markdown file and a PRDs README index file. Use the Write tool to create both files.

### Phase Plan (`{{output_path}}`)

Follow this structure exactly:

```markdown
# Purpose

2-3 paragraphs explaining what this phase accomplishes, why it matters, and how it relates to the overall project. Include what the downstream consumer of this phase's outputs is.

---

# What This Phase Produces

**Output:** Describe the concrete outputs of this phase — what data structures, files, or capabilities are produced.

**Downstream consumer:** Which phase or system consumes these outputs.

---

# Design Decisions

{% if detail_level == "lean_prd" %}
(Optional) Document key architectural or design decisions only if they affect multiple deliverables. Brief bullet points are sufficient. Omit this section entirely if there are no cross-deliverable decisions.
{% else %}
Document key architectural or design decisions made for this phase. Each decision should explain the choice and rationale. Use subsections (##) for major decisions that affect multiple deliverables.
{% endif %}

---

# Deliverables

List each deliverable with a number, title, brief description{% if detail_level != "lean_prd" %}, and estimated test count{% endif %}.

Format:
### N. <Deliverable Title>
- **Description:** What this deliverable implements
{% if detail_level != "lean_prd" %}- **Estimated tests:** <number>
{% endif %}- **Dependencies:** Other deliverables this depends on (within this phase or from prior phases)

---

# Deliverable Dependencies

Dependency table and parallel execution tiers. Used to sequence implementation work.

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | <Title> | — | 2, 3 |
| 2 | <Title> | 1 | — |

**Implementation tiers** (deliverables within a tier have no mutual dependencies and can be implemented in parallel):

- **Tier 1:** 1. <Title>
- **Tier 2:** 2. <Title>, 3. <Title>

Include ALL deliverables in the dependency table — even those with no dependencies (use "—" in the Depends On column). "Depends On" lists deliverable numbers from this phase or prior phase references (e.g., "Phase 1"). "Enables" lists deliverable numbers that directly depend on this one. Tiers are derived from the dependency graph: Tier 1 has no dependencies, Tier N+1 items depend only on items in Tier N or earlier.

---

# Open Questions

List any unresolved questions using the format:

- [ ] OQ-P{{phase_number}}-01: <question> — *options: A / B / C*

If no open questions remain, write "None — all decisions resolved."
```

### PRDs README (`{{prds_readme_path}}`)

Create an index file listing all deliverables and their corresponding PRD files:

```markdown
# Phase {{phase_number}}: {{phase_name}} PRDs

This directory contains Product Requirement Documents for Phase {{phase_number}}.

## Deliverable Mapping

| # | PRD | Deliverable |
|---|-----|-------------|
| 01 | [<Title>](prd-01-<slug>.md) | <brief description> |
| 02 | [<Title>](prd-02-<slug>.md) | <brief description> |

## PRD Structure

Each PRD follows a consistent structure:

1. **Overview** — Brief description of the component
2. **Goals** — What the component achieves
3. **Non-Goals** — Explicit scope boundaries
4. **Data Structures** — Key classes and interfaces
5. **API** — Function signatures
6. **Success Criteria** — Unit tests that must pass
7. **File Location** — Where the code lives
8. **Dependencies** — Required modules
9. **Open Questions** — Unresolved design decisions

## Dependency Graph

| # | PRD | Depends On | Enables |
|---|-----|-----------|---------|
| 01 | <Title> | — | 02, 03 |
| 02 | <Title> | 01 | — |

**Implementation tiers** (PRDs within a tier can be implemented in parallel):

- **Tier 1:** PRD 01
- **Tier 2:** PRD 02, PRD 03
```

## Quality Criteria

- Each deliverable must be concrete enough to become a single PRD
- Deliverables should be roughly equal in scope ({% if detail_level == "lean_prd" %}3-6 acceptance criteria each is a good heuristic{% else %}8-18 tests each is a good heuristic{% endif %})
- Dependencies between deliverables must be explicit in both per-deliverable fields and the Deliverable Dependencies table
- The Deliverable Dependencies table must include every deliverable, with correct Depends On / Enables cross-references
- Implementation tiers must be topologically valid: no deliverable in Tier N may depend on a deliverable in Tier N or later
- Every dependency listed in a deliverable's Dependencies field must appear in the Depends On column of the table
- Open questions must include suggested resolution options
- The phase plan must not contradict the executive plan

## Context Exhaustion

On CRITICAL context warning, write whatever is complete to disk, then:

1. **Write** `.fragment-handoff.md` in the phase directory with header fields (`Subagent Type: phase-plan-writer`, `Unit: Phase {{phase_number}}`, `Timestamp`, `Progress`) and three sections: `## Completed` (files with complete/partial status), `## Remaining` (files/sections not yet written), `## Artifacts on Disk` (paths with status).
2. **Return** a message ending with: `status: CONTEXT_EXHAUSTED`

## Output

Write both files using the Write tool:
1. Phase plan to `{{output_path}}`
2. PRDs README to `{{prds_readme_path}}`
