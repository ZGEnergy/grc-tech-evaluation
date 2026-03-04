# Artifact Templates

Document skeletons for each artifact type in the hierarchical plan. These define the required sections and conventions. Subagents fill in the content; the orchestrator uses these to validate structure.

## Executive Plan Template

```markdown
# <Project Name> — Executive Plan

## Vision

<2-3 paragraphs: what are we building and why. High-level value proposition.>

## Objectives

<Numbered list of 3-7 concrete objectives. Each should be measurable or verifiable.>

1. <objective>
2. <objective>

## Constraints

<Bulleted list of technical, organizational, or timeline constraints.>

- <constraint>
- <constraint>

## Phases

### Phase 1: <Name>
- **Objective:** <one sentence>
- **Key deliverables:** <comma-separated list>
- **Target repository:** <repo directory name>
- **Dependencies:** <what must exist before this phase starts>
- **Estimated scope:** <rough size indicator>

### Phase 2: <Name>
- **Objective:** <one sentence>
- **Key deliverables:** <comma-separated list>
- **Target repository:** <repo directory name>
- **Dependencies:** <prior phases or external inputs>
- **Estimated scope:** <rough size indicator>

## Phase Dependencies

<Directed acyclic graph of phase dependencies. Phases in the same tier can run in parallel.>

| Phase | Depends On | Enables |
|-------|-----------|---------|
| Phase 1 | — | Phase 2 |
| Phase 2 | Phase 1 | — |

**Implementation tiers** (phases within a tier have no mutual dependencies and can be executed in parallel):

- **Tier 1:** Phase 1
- **Tier 2:** Phase 2

## Open Questions

- [ ] OQ-E01: <question> — *options: A / B / C*
```

## Phase Plan Template

```markdown
# Purpose

<2-3 paragraphs explaining what this phase accomplishes, why it matters, and how it connects to the broader project.>

---

# What This Phase Produces

**Output:** <concrete description of what this phase delivers>

**Downstream consumer:** <which phase or system uses these outputs>

---

# Design Decisions

<Document key architectural choices for this phase. Use subsections for major decisions.>

## <Decision Title>

<Rationale and chosen approach.>

---

# Deliverables

### 1. <Deliverable Title>
- **Description:** <what it does>
- **Target repository:** <repo directory name (defaults to phase target if omitted)>
- **Estimated tests:** <number>
- **Dependencies:** <other deliverables or prior phases>

### 2. <Deliverable Title>
- **Description:** <what it does>
- **Target repository:** <repo directory name (defaults to phase target if omitted)>
- **Estimated tests:** <number>
- **Dependencies:** <other deliverables or prior phases>

---

# Deliverable Dependencies

<Dependency table and parallel execution tiers. Used to sequence implementation work.>

| # | Deliverable | Depends On | Enables |
|---|-------------|-----------|---------|
| 1 | <Title> | — | 2, 3 |
| 2 | <Title> | 1 | 4 |
| 3 | <Title> | 1 | 4 |
| 4 | <Title> | 2, 3 | — |

**Implementation tiers** (deliverables within a tier have no mutual dependencies and can be implemented in parallel):

- **Tier 1:** 1. <Title>
- **Tier 2:** 2. <Title>, 3. <Title>
- **Tier 3:** 4. <Title>

---

# Open Questions

- [ ] OQ-P<N>-01: <question> — *options: A / B / C*
```

## PRDs README Template

```markdown
# Phase <N>: <Phase Name> PRDs

This directory contains Product Requirement Documents for Phase <N>.

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
8. **Repository** — Which repo the code belongs to
9. **Dependencies** — Required modules
10. **Open Questions** — Unresolved design decisions

## Dependency Graph

| # | PRD | Depends On | Enables |
|---|-----|-----------|---------|
| 01 | <Title> | — | 02, 03 |
| 02 | <Title> | 01 | 04 |

**Implementation tiers** (PRDs within a tier can be implemented in parallel):

- **Tier 1:** PRD 01
- **Tier 2:** PRD 02, PRD 03
- **Tier 3:** PRD 04
```

## PRD Template

```markdown
# PRD: <Deliverable Title>

## Overview

<1-2 paragraphs: what this component does, why it exists, how it fits.>

## Goals

1. <goal>
2. <goal>

## Non-Goals

- <non-goal> (<which PRD handles this instead>)
- <non-goal>

## Data Structures

```python
@dataclass
class <Name>:
    """<docstring>"""
    field: type  # notes
```

## API

```python
def function_name(param: Type) -> ReturnType:
    """<docstring with Args, Returns, Raises>"""
```

## Success Criteria

### Unit Tests

1. **test_<name>**
   - <what it verifies>

2. **test_<name>**
   - <what it verifies>

## File Location

`src/<package>/<module>.py`

## Repository

`<repo-directory-name>`

## Dependencies

### Internal Dependencies
- PRD <NN> (<title>) — <what is used>

### External Dependencies
- <library> — <what for>

## Open Questions

- [ ] OQ-D<phase>.<prd>-01: <question> — *options: A / B / C*

```

## Task Card Container Template (Tier 1)

Used when the complexity assessment selects Tier 1 (≤1 phase, ≤5 files, single repo). All task cards live in a single flat file instead of a phase/PRD hierarchy.

```markdown
# <Project Name> — Task Cards

## Overview

<1-2 paragraphs: what we're building, why, and the target repository.>

## Task Cards

### TC-01: <Task Title>

**Description:** <1-2 paragraphs: what this task does, why it matters, and how it fits.>

**File locations:**
- Source: `<path/to/source.py>`
- Test: `<path/to/test_source.py>`

**Repository:** `<repo-directory-name>`

**Acceptance criteria:**
1. <criterion — concrete, testable>
2. <criterion>

**Dependencies:** None | TC-NN

---

### TC-02: <Task Title>

**Description:** <1-2 paragraphs>

**File locations:**
- Source: `<path/to/source.py>`
- Test: `<path/to/test_source.py>`

**Repository:** `<repo-directory-name>`

**Acceptance criteria:**
1. <criterion>
2. <criterion>

**Dependencies:** TC-01

## Execution Order

| # | Task | Depends On | Enables |
|---|------|-----------|---------|
| 01 | <Title> | — | 02 |
| 02 | <Title> | 01 | — |
```

## Task Card Template (Tier 1 — Individual)

Used by the PRD writer subagent when `{{detail_level}}` is `task_card`.

```markdown
### TC-{{prd_number}}: {{prd_title}}

**Description:** <1-2 paragraphs: what this task does, why it matters, how it fits into the overall plan.>

**File locations:**
- Source: `<exact/path/to/source.py>`
- Test: `<exact/path/to/test_source.py>`

**Repository:** `<repo-directory-name>`

**Acceptance criteria:**
1. <criterion — concrete, testable, implementable from this description alone>
2. <criterion>
3. <criterion> (optional, 2-4 total)

**Dependencies:** None | TC-NN, TC-NN
```

## Lean PRD Template (Tier 2)

Used when the complexity assessment selects Tier 2 (2-3 phases, 5-15 files). Omits Data Structures, API, and Non-Goals sections. Gives the implementer design freedom while providing enough structure for consistency.

```markdown
# PRD: <Deliverable Title>

## Overview

<1 paragraph: what this component does, why it exists, how it fits into the larger system.>

## Goals

1. <goal — concrete, testable>
2. <goal>
3. <goal> (3-5 total)

## File Location

`src/<package>/<module>.py`

## Repository

`<repo-directory-name>`

## Key Decisions (optional)

- <decision>: <chosen approach and brief rationale>

## Acceptance Criteria

1. **test_<descriptive_name>** — <what it verifies, including expected inputs and outputs>
2. **test_<descriptive_name>** — <what it verifies>
3. **test_<descriptive_name>** — <what it verifies> (3-6 total)

## Dependencies

### Internal Dependencies
- PRD <NN> (<title>) — <what is used>

### External Dependencies
- <library> — <what for>

## Open Questions

- [ ] OQ-D<phase>.<prd>-01: <question> — *options: A / B / C*
```
