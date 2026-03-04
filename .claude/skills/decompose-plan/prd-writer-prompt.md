# PRD Writer — Subagent Prompt Template

Write a PRD for deliverable {{prd_number}} in Phase {{phase_number}}: **{{prd_title}}**.

**Detail level:** `{{detail_level}}`

## Context

### Executive Plan Summary

{{executive_summary}}

### Parent Phase Plan

{{phase_plan_summary}}

### Adjacent PRD Summaries

{{adjacent_prd_summaries}}

### Resolved Open Questions

{{resolved_oqs}}

## Instructions

{% if detail_level == "task_card" %}

Write a task card following the Task Card Template from `artifact-templates.md`. Return the task card content as text (the orchestrator will assemble the container file).

```markdown
### TC-{{prd_number}}: {{prd_title}}

**Description:** 1-2 paragraphs explaining what this task does, why it matters, and how it fits into the overall plan.

**File locations:**
- Source: `<exact/path/to/source.py>`
- Test: `<exact/path/to/test_source.py>`

**Repository:** `{{target_repo}}`

**Acceptance criteria:**
1. <criterion — concrete, testable, implementable from this description alone>
2. <criterion>
3. <criterion> (optional, 2-4 total)

**Dependencies:** None | TC-NN, TC-NN
```

### Quality Criteria (Task Card)

- Description must be self-contained: an implementer should be able to code the task from the description and acceptance criteria alone
- 2-4 acceptance criteria, each concrete and testable
- File locations must be exact paths following project conventions
- Dependencies reference other task card numbers (TC-NN format)

### Output (Task Card)

Return the task card content as text. Do NOT write to a file — the orchestrator assembles the container.

{% elif detail_level == "lean_prd" %}

Write a lean PRD markdown file to `{{output_path}}` using the Write tool. Follow this structure exactly:

```markdown
# PRD: {{prd_title}}

## Overview

1 paragraph explaining what this component does, why it exists, and how it fits into the larger system.

## Goals

Numbered list of 3-5 concrete goals. Each goal should be testable or verifiable.

1. <goal>
2. <goal>

## File Location

`src/<package>/<module>.py`

Specify the exact file path where this code will live.

## Repository

`{{target_repo}}`

## Key Decisions (optional)

Bulleted list of key design or architectural decisions for this component. Include the chosen approach and brief rationale. Omit this section if there are no noteworthy decisions.

- <decision>: <chosen approach and brief rationale>

## Acceptance Criteria

Define 3-6 named acceptance criteria. Each has a descriptive test name and a 1-2 sentence description.

1. **test_<descriptive_name>** — <what it verifies, including expected inputs and outputs>
2. **test_<descriptive_name>** — <what it verifies>

## Dependencies

### Internal Dependencies
- PRD <NN> (<title>) — <what is used from it>

### External Dependencies
- <library> — <what for>

## Open Questions

List any unresolved questions using the format:

- [ ] OQ-D{{phase_number}}.{{prd_number}}-01: <question> — *options: A / B / C*

If no open questions remain, write "None — all decisions resolved."
```

### Quality Criteria (Lean PRD)

- Goals must be concrete and testable (3-5 per PRD)
- 3-6 acceptance criteria, each specific enough that a developer could implement the test from the name and description alone
- Dependencies must reference specific PRD numbers, not vague descriptions
- The PRD must not contradict its parent phase plan or the executive plan
- The implementer has design freedom for data structures and API — do NOT specify them

### Output (Lean PRD)

Write the lean PRD using the Write tool to `{{output_path}}`.

{% else %}

Write a PRD markdown file to `{{output_path}}` using the Write tool. Follow this structure exactly:

```markdown
# PRD: {{prd_title}}

## Overview

1-2 paragraphs explaining what this component does, why it exists, and how it fits into the larger system.

## Goals

Numbered list of 3-6 concrete goals. Each goal should be testable or verifiable.

1. <goal>
2. <goal>

## Non-Goals

Bulleted list of things explicitly out of scope. This prevents scope creep and clarifies boundaries with adjacent PRDs.

- <non-goal> (<which PRD handles this instead>)
- <non-goal>

## Data Structures

Define the key data structures using concrete Python code blocks. Use dataclasses with type annotations. Include docstrings and constraints as comments.

**Symbol completeness rule:** Every class, enum, TypeAlias, and named constant that this PRD's module exports must appear in a Python code block in this section. If a type is used as a parameter type, return type, or field type in the API section and it belongs to *this* PRD's module, it must have a code block definition here. A downstream PRD type-checking tool verifies that every symbol imported from your module by other PRDs has a matching declaration in your code blocks — prose descriptions alone are not sufficient.

```python
@dataclass
class <ClassName>:
    """<docstring>"""
    field: type  # constraint or notes
```

For enums, use StrEnum:

```python
class <EnumName>(StrEnum):
    """<docstring>"""
    VALUE = "value"
```

## API

Define the public API with function signatures, docstrings, and type annotations:

```python
def function_name(
    param: Type,
    param: Type,
) -> ReturnType:
    """
    <description>

    Args:
        param: <description>

    Returns:
        <description>

    Raises:
        ValueError: <when>
    """
```

## Success Criteria

### Unit Tests

Define 8-18 named unit tests. Each test has a descriptive name and a 1-2 sentence description of what it verifies.

1. **test_<descriptive_name>**
   - <what the test verifies, including expected inputs and outputs>

2. **test_<descriptive_name>**
   - <what the test verifies>

Target test count: aim for thorough coverage of happy paths, edge cases, error handling, and boundary conditions.

### Integration Tests (if applicable)

List any tests that verify integration with adjacent PRDs.

## File Location

`src/<package>/<module>.py`

Specify the exact file path where this code will live. Follow the project's existing code organization conventions.

## Repository

`{{target_repo}}`

Specify the repository directory name where this code will live. This must match
a directory in the workspace (e.g., `market-framework`, `market-ercot`).

## Dependencies

### Internal Dependencies
- PRD <NN> (<title>) — <what is used from it>

### External Dependencies
- <library> — <what for>

**Import cross-check rule:** Review every `from <module> import <symbol>` statement in your Data Structures and API code blocks. If the module resolves to another PRD in this phase (or a prior phase), that PRD must appear in Internal Dependencies. Do not rely on transitive dependencies — if your code block imports directly from a module, list it.

## Open Questions

List any unresolved questions using the format:

- [ ] OQ-D{{phase_number}}.{{prd_number}}-01: <question> — *options: A / B / C*

If no open questions remain, write "None — all decisions resolved."

```

{% endif %}

## Quality Criteria (Full PRD)

The following criteria apply only when `{{detail_level}}` is `full_prd`. For `lean_prd` and `task_card`, see the quality criteria in their respective sections above.

- Data structures must use concrete Python types (not pseudocode or abstract descriptions)
- Function signatures must include full type annotations
- **Symbol completeness**: Every type this module defines that appears in any code block (as a parameter type, return type, field type, or base class) must have its own code block declaration in Data Structures. Enums, TypeAliases, and config dataclasses are commonly missed — include them.
- **Import-dependency consistency**: Every `from <module> import <name>` in your code blocks that references another PRD must have a corresponding entry in Internal Dependencies. Verify this before finalizing.
- **Parameter naming consistency**: When your API uses the same concept as an adjacent PRD (e.g., an hour identifier, an entity ID), use the same parameter name that adjacent PRDs use. Check the adjacent PRD summaries for naming precedent. Avoid abbreviations that differ from siblings (e.g., don't use `he` if siblings use `hour_ending`).
- Test names must be specific enough that a developer could implement the test from the name and description alone
- Dependencies must reference specific PRD numbers, not vague descriptions
- Non-goals must reference which other PRD handles the excluded scope
- The PRD must not contradict its parent phase plan or the executive plan
- Test count should be 8-18 per PRD; fewer suggests the PRD is too narrow, more suggests it should be split

## Discoveries (full_prd and lean_prd only)

If `{{detail_level}}` is `task_card`, skip this section.

If while writing this PRD, something conflicts with or requires changes to the phase plan or executive plan, note it at the end of the file in a section:

```markdown
## Discoveries

- **DISCOVERY [type]:** <description of what conflicts or needs updating>
  - Affected document: <path>
  - Suggested resolution: <what should change>
```

Discovery types: `DEPENDENCY`, `SCOPE_CHANGE`, `INTERFACE_MISMATCH`, `ORDERING_CHANGE`, `FEASIBILITY`.

## Context Exhaustion

On CRITICAL context warning, write the partial PRD to `{{output_path}}` (mark incomplete sections with `<!-- INCOMPLETE: to be continued -->`), then:

1. **Write** `.fragment-handoff.md` in the PRD's directory with header fields (`Subagent Type: prd-writer`, `Unit: Phase {{phase_number}} PRD {{prd_number}}`, `Timestamp`, `Progress: sections done of total`) and three sections: `## Completed`, `## Remaining`, `## Artifacts on Disk`.
2. **Return** a message ending with: `status: CONTEXT_EXHAUSTED`

## Output

If `{{detail_level}}` is `task_card`: return the task card content as text (do not write to a file).

If `{{detail_level}}` is `lean_prd` or `full_prd`: write the PRD using the Write tool to `{{output_path}}`.
