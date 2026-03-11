# PRD-06: Updated Orchestrator — SKILL.md

## Overview

This deliverable makes two targeted updates to `.claude/skills/evaluate-tool/SKILL.md`,
the orchestrator that drives the evaluate-tool state machine. The current orchestrator
(protocol v7 era) dispatches 3 research agents in the RESEARCH state and provides no
mechanism to pass version capability data to code-evaluator agents in the EVALUATE state.

The two updates are:

1. **RESEARCH state — 4th agent dispatch.** Add Agent 4 alongside the existing 3 parallel
   research agents. Agent 4 uses the focus string `"Version-specific capabilities: installed
   version identification, changelog analysis, capability mapping to protocol test
   requirements, breaking changes between installed and latest versions"`. Its output path
   is `{{RESULTS_DIR}}/research-version.md`. The merge step is updated to concatenate 4
   research files instead of 3. The thin-research warning is updated to check 4 files.

2. **EVALUATE state — version capability report consumer contract.** In the variable
   replacement list for code-evaluator agents, add `{{version_capability_report}}` mapped
   to the contents of `{{RESULTS_DIR}}/research-version.md`. Add a note that code-evaluator
   agents may record `fail` with `failure_reason: unsupported_in_installed_version` for
   features not supported in the installed version.

These changes wire the version-awareness research pipeline (PRD-03) into the orchestrator
and connect its output to the code-evaluator's version-gated test guardrail (PRD-04),
completing the end-to-end version capability flow.

## Goals

1. **Dispatch Agent 4 in the RESEARCH state.** Add a 4th parallel research agent with the
   version-specific focus string, output path `research-version.md`, and the same variable
   replacement pattern used by Agents 1-3 (`{{tool_name}}`, `{{output_path}}`). Agent 4
   reads the same `research-prompt.md` template as Agents 1-3.

2. **Update the merge step to include 4 files.** The merge step currently concatenates 3
   research output files into `{{RESEARCH_PATH}}`. After this update it concatenates 4 files:
   `research-api.md`, `research-extensions.md`, `research-limitations.md`, and
   `research-version.md`, each with a section header.

3. **Update the thin-research warning for 4 files.** The current thin-research warning checks
   3 files for the 500-word minimum. After this update it checks all 4, including the new
   `research-version.md`.

4. **Add `{{version_capability_report}}` to code-evaluator variable replacement.** In the
   EVALUATE state, step 2b (variable replacement for code-evaluator agents), add
   `{{version_capability_report}}` mapped to the contents of
   `{{RESULTS_DIR}}/research-version.md`. This makes the structured capability report
   available to every code-evaluator agent dispatch.

5. **Document the `unsupported_in_installed_version` failure reason.** Add a note in the
   EVALUATE state that code-evaluator agents may record tests as `fail` with
   `failure_reason: unsupported_in_installed_version` when the capability report indicates
   the installed version does not support a required feature. This is informational context
   for the orchestrator (the decision logic lives in the code-evaluator prompt per PRD-04).

## Non-Goals

- **Modifying the research-prompt.md template.** The Agent 4 specification, capability report
  schema, and focus-specific guidance are PRD-03 scope. This PRD dispatches Agent 4 via the
  orchestrator; it does not define what Agent 4 does.

- **Modifying the code-evaluator-prompt.md template.** The `{{version_capability_report}}`
  input variable declaration and the version-gated test guardrail are PRD-04 scope. This PRD
  populates the variable at runtime; it does not define how the code-evaluator consumes it.

- **Changing the state machine topology.** The state sequence remains
  `CONFIGURE → RESEARCH → GATE → EVALUATE → VALIDATE → SYNTHESIZE`. No new states are added.

- **Modifying other states.** Only the RESEARCH and EVALUATE states are changed. CONFIGURE,
  GATE, VALIDATE, SYNTHESIZE, worktree isolation, observation routing, error handling, and
  context monitoring are unchanged.

- **Modifying audit-evaluator variable replacement.** The `{{version_capability_report}}`
  variable is added only to code-evaluator agents. Audit-evaluator agents do not receive it
  because audit dimensions (accessibility, maturity, supply_chain) do not exercise
  version-specific API features.

- **Adding Agent 4 to the observation routing table.** The version capability report is
  consumed via a dedicated variable, not via observation tags. No new observation tags are
  introduced.

## Data Structures

### Agent 4 Dispatch Parameters

The orchestrator dispatches Agent 4 with the same pattern as Agents 1-3. The dispatch
parameters are:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchAgentDispatch:
    """Parameters for dispatching a research agent in the RESEARCH state.

    This structure documents the variable replacement contract between SKILL.md
    and research-prompt.md for all 4 agents.
    """

    agent_number: int
    """1-4. Agent 4 is the version-awareness agent."""

    focus_label: str
    """Human-readable label (e.g., 'API & Formulations', 'Version-Awareness')."""

    research_focus: str
    """The {{research_focus}} value passed to the research-prompt.md template.

    Agent 1: 'API surface, supported problem formulations, solver interfaces,
              data model (bus/branch/gen abstractions), input/output formats'
    Agent 2: 'Extension mechanisms, plugin/callback APIs, internal architecture
              (separation of concerns), graph access, interoperability with
              DataFrames/NetworkX/Graphs.jl'
    Agent 3: 'Known limitations, open issues related to evaluation tests,
              ecosystem packages, community size, documentation quality, recent
              release history'
    Agent 4: 'Version-specific capabilities: installed version identification,
              changelog analysis, capability mapping to protocol test requirements,
              breaking changes between installed and latest versions'
    """

    output_path: str
    """Path to the output file. Follows {{RESULTS_DIR}}/research-{focus_slug}.md.

    Agent 1: '{{RESULTS_DIR}}/research-api.md'
    Agent 2: '{{RESULTS_DIR}}/research-extensions.md'
    Agent 3: '{{RESULTS_DIR}}/research-limitations.md'
    Agent 4: '{{RESULTS_DIR}}/research-version.md'
    """

    tool_name: str
    """The {{tool_name}} value, same for all agents."""
```

### Version Capability Report Variable Wiring

The orchestrator populates `{{version_capability_report}}` for code-evaluator agents by
reading the contents of the Agent 4 output file. This is the consumer contract between
SKILL.md and code-evaluator-prompt.md.

```python
@dataclass(frozen=True)
class CodeEvaluatorVariableSet:
    """Complete set of variables replaced in code-evaluator-prompt.md.

    Extends the existing variable set with version_capability_report.
    Listed here to document the full contract; only the new field is
    added by this PRD.
    """

    dimension: str
    """Dimension name (e.g., 'expressiveness', 'extensibility')."""

    test_ids: str
    """Comma-separated test IDs for this dimension + tier."""

    network_tier: str
    """Current tier: TINY, SMALL, or MEDIUM."""

    tool_name: str
    """Tool under evaluation."""

    tool_dir: str
    """Path to the tool's evaluation directory."""

    results_dir: str
    """Path to the dimension's results directory."""

    research_context: str
    """Contents of {{RESEARCH_PATH}} (merged research from all 4 agents)."""

    reference_files: str
    """Paths to all reference files in {{SKILL_DIR}}/references/."""

    observation_tags: str
    """Tags this dimension emits."""

    consumed_observations: str
    """Contents of observation files matching consumed tags."""

    version_capability_report: str
    """NEW — Contents of {{RESULTS_DIR}}/research-version.md.

    The structured capability report produced by Agent 4 during the RESEARCH
    state. Contains YAML frontmatter (installed_version, latest_version, etc.)
    and a capability table mapping protocol-relevant features to version
    availability.

    Used by the code-evaluator's version-gated test guardrail (PRD-04) to
    determine whether specific tests should be attempted or skipped based on
    the installed version's feature set. Tests for unsupported features are
    recorded as fail with failure_reason: unsupported_in_installed_version.

    If research-version.md does not exist (e.g., Agent 4 failed), this variable
    is set to an empty string and the code-evaluator proceeds without version
    gating.
    """
```

### Merge Step File List

The updated merge step concatenates 4 files with section headers:

```python
RESEARCH_FILES_TO_MERGE: list[tuple[str, str]] = [
    ("API & Formulations", "research-api.md"),
    ("Extensions & Architecture", "research-extensions.md"),
    ("Limitations & Ecosystem", "research-limitations.md"),
    ("Version Capabilities", "research-version.md"),  # NEW
]
"""Ordered list of (section_header, filename) pairs for the RESEARCH merge step.

Each file at {{RESULTS_DIR}}/{filename} is concatenated into {{RESEARCH_PATH}}
with a markdown H2 section header. The order matches the agent numbering.
"""
```

## API

No executable API. This deliverable modifies a markdown orchestrator document (`SKILL.md`).
The following verification functions describe checks against the orchestrator text.

### Orchestrator structure verification

```python
from __future__ import annotations

from pathlib import Path


SKILL_PATH = Path(".claude/skills/evaluate-tool/SKILL.md")


def load_skill() -> str:
    """Read SKILL.md and return its full text."""
    return SKILL_PATH.read_text(encoding="utf-8")


def extract_research_state(skill_text: str) -> str:
    """Extract the RESEARCH state section.

    Returns everything from '### State: RESEARCH' through the next H3 heading
    or end of file.
    """
    ...


def extract_evaluate_state(skill_text: str) -> str:
    """Extract the EVALUATE state section.

    Returns everything from '### State: EVALUATE' through the next H3 heading
    or end of file.
    """
    ...


def verify_agent4_dispatch(research_text: str) -> tuple[bool, list[str]]:
    """Verify Agent 4 dispatch in the RESEARCH state.

    Checks for:
    - Agent 4 listed alongside Agents 1-3 in the parallel dispatch step
    - Focus string contains 'Version-specific capabilities'
    - Focus string contains 'installed version identification'
    - Focus string contains 'changelog analysis'
    - Focus string contains 'capability mapping to protocol test requirements'
    - Focus string contains 'breaking changes'
    - Output path is '{{RESULTS_DIR}}/research-version.md'
    - {{tool_name}} and {{output_path}} variables are passed

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_merge_step(research_text: str) -> tuple[bool, list[str]]:
    """Verify the merge step includes 4 files.

    Checks for:
    - Reference to 4 research output files (not 3)
    - research-version.md included in the file list
    - All original files still listed (research-api, research-extensions,
      research-limitations or equivalent slugs)

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_thin_research_warning(research_text: str) -> tuple[bool, str]:
    """Verify the thin-research warning covers 4 files.

    Checks for:
    - Warning text mentions checking all research files (4, not 3)
    - Or the warning logic is generalized to 'any research file' without
      a hardcoded count

    Returns (updated, error_message_if_not).
    """
    ...


def verify_version_capability_variable(evaluate_text: str) -> tuple[bool, list[str]]:
    """Verify {{version_capability_report}} in code-evaluator variable replacement.

    Checks for:
    - '{{version_capability_report}}' appears in the variable replacement list
    - Mapped to contents of '{{RESULTS_DIR}}/research-version.md'
    - Only for code-evaluator agents (not audit-evaluator)
    - Appears in the step 2b variable list alongside existing variables

    Returns (complete, list_of_missing_elements).
    """
    ...


def verify_unsupported_failure_note(evaluate_text: str) -> tuple[bool, str]:
    """Verify the unsupported_in_installed_version failure reason note.

    Checks for:
    - 'unsupported_in_installed_version' mentioned in the EVALUATE state
    - Context indicating this is a valid failure_reason for code-evaluator results
    - Note is informational (decision logic is in code-evaluator prompt, not here)

    Returns (present, error_message_if_missing).
    """
    ...


def verify_other_states_unchanged(
    original_text: str,
    updated_text: str,
) -> tuple[bool, list[str]]:
    """Verify that states other than RESEARCH and EVALUATE are unchanged.

    Checks that CONFIGURE, GATE, VALIDATE, SYNTHESIZE, Worktree Isolation,
    Observation Routing, Error Handling, and Context Monitoring sections are
    identical in the original and updated text.

    Returns (unchanged, list_of_unexpected_changes).
    """
    ...
```

## Success Criteria

Each criterion is a verifiable check on the updated `.claude/skills/evaluate-tool/SKILL.md`.

### Update 1: RESEARCH state — Agent 4 dispatch (6 checks)

1. **SC-01: Agent 4 listed in parallel dispatch.** The RESEARCH state step 2 lists 4
   research agents dispatched in parallel (not 3). Agent 4 is clearly labeled with a
   descriptive name (e.g., "Agent 4 — Version Capabilities" or equivalent).

2. **SC-02: Agent 4 focus string.** Agent 4's `{{research_focus}}` value is
   `"Version-specific capabilities: installed version identification, changelog analysis,
   capability mapping to protocol test requirements, breaking changes between installed
   and latest versions"` (exact string from the phase plan).

3. **SC-03: Agent 4 output path.** Agent 4's output path is
   `{{RESULTS_DIR}}/research-version.md`, following the existing
   `research-{focus_slug}.md` convention.

4. **SC-04: Agent 4 receives standard variables.** Agent 4 receives the same
   `{{tool_name}}` and `{{output_path}}` variables as Agents 1-3.

5. **SC-05: Merge step includes 4 files.** The merge step (step 3 of RESEARCH) explicitly
   references 4 research output files to concatenate into `{{RESEARCH_PATH}}`. The text
   says "4" (not "3") or lists all four files by name. The new file
   `research-version.md` appears alongside the existing three.

6. **SC-06: Thin-research warning covers 4 files.** The thin-research warning (step 4 of
   RESEARCH) checks all 4 research files for the 500-word minimum. The text either says
   "4 files" or uses language that encompasses all research output files without a
   hardcoded count of 3.

### Update 2: EVALUATE state — version capability variable (4 checks)

7. **SC-07: Variable in replacement list.** The EVALUATE state step 2b (variable
   replacement for code-evaluator agents) includes `{{version_capability_report}}` as a
   listed variable with an arrow or mapping to its source.

8. **SC-08: Variable mapped to research-version.md.** The `{{version_capability_report}}`
   variable is mapped to the contents of `{{RESULTS_DIR}}/research-version.md`. The
   mapping specifies reading the file contents, not just passing the file path.

9. **SC-09: Variable scoped to code-evaluator only.** The `{{version_capability_report}}`
   variable appears in the code-evaluator variable list but not in the audit-evaluator
   variable list. The distinction is clear from the prompt structure (step 2a determines
   archetype, step 2b applies archetype-specific variables).

10. **SC-10: Unsupported feature failure note.** The EVALUATE state contains a note
    indicating that code-evaluator agents may record `fail` with
    `failure_reason: unsupported_in_installed_version` for features not supported by the
    installed version. The note is informational — it does not define the decision
    procedure (that is in the code-evaluator prompt per PRD-04).

### Preservation checks (4 checks)

11. **SC-11: Agents 1-3 unchanged.** The existing Agent 1 (API & Formulations), Agent 2
    (Extensions & Architecture), and Agent 3 (Limitations & Ecosystem) dispatch
    specifications in the RESEARCH state are unchanged in focus string, output path, and
    variable replacement.

12. **SC-12: Other states unchanged.** The CONFIGURE, GATE, VALIDATE, and SYNTHESIZE
    state sections are unchanged. No additions, deletions, or modifications to their
    content.

13. **SC-13: Observation routing unchanged.** The Observation Routing section is unchanged.
    No new observation tags are introduced by this PRD.

14. **SC-14: Support sections unchanged.** The Argument Parsing, Execution Environment,
    Worktree Isolation, Error Handling, and Context Monitoring sections are unchanged.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `.claude/skills/evaluate-tool/SKILL.md` | Edit | Add Agent 4 dispatch to RESEARCH state; add `{{version_capability_report}}` to EVALUATE state code-evaluator variable replacement |

No new files are created. No files are deleted.

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

### Internal Dependencies

- **PRD-03 (`research-prompt.md`)** — Defines the Agent 4 specification, capability report
  schema, and focus-specific guidance that Agent 4 executes when dispatched. This PRD
  dispatches Agent 4; PRD-03 defines what Agent 4 does. The output file path
  (`research-version.md`) and the capability report schema (YAML frontmatter with
  `installed_version`, capability table) are defined in PRD-03 and referenced here.

- **PRD-04 (`code-evaluator-prompt.md`)** — Declares the `{{version_capability_report}}`
  input variable and the version-gated test guardrail that consumes it. This PRD populates
  the variable at runtime; PRD-04 defines how the code-evaluator uses it. The
  `unsupported_in_installed_version` failure reason is defined in PRD-04 and referenced
  here as informational context.

### External Dependencies

None. This deliverable modifies only a markdown orchestrator document with no code execution.

### Downstream Consumers

- **All subsequent evaluation runs.** Once SKILL.md is updated, every `/evaluate-tool`
  invocation dispatches Agent 4 and passes the capability report to code-evaluator agents.
  This is a runtime behavior change with no opt-out mechanism.

- **Phase 3 (Validation).** Verifies that the SKILL.md orchestrator correctly dispatches
  Agent 4, merges 4 research files, and passes `{{version_capability_report}}` to
  code-evaluator agents.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Agent 4 focus string: exact string provided in the phase plan, used verbatim.
- Output path `research-version.md`: follows the existing slug convention.
- `{{version_capability_report}}` as a separate variable (not embedded in
  `{{research_context}}`): confirmed. Separate variable enables the code-evaluator to
  parse the structured capability report independently from the free-form merged research.
- Code-evaluator only (not audit-evaluator): confirmed. Audit dimensions do not exercise
  version-specific API features.
- Merge step includes 4 files: confirmed. The merged research context grows to include
  the version capability section, so downstream consumers (synthesis) see it in the
  unified research context as well.
