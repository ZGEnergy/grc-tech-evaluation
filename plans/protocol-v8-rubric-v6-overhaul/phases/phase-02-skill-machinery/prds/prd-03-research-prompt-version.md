# PRD-03: research-prompt.md — Version-Awareness Agent (Agent 4)

## Overview

Add a 4th research agent specification to `.claude/skills/evaluate-tool/prompts/research-prompt.md`.
The existing prompt defines three research agents dispatched in parallel during the RESEARCH
state: Agent 1 (API & Formulations), Agent 2 (Extensions & Architecture), and Agent 3
(Limitations & Ecosystem). All three produce free-form markdown output following a shared
template structure (Key Findings, Detailed Notes, Sources, Gaps and Uncertainties).

Agent 4 (Version-Awareness) differs from the existing agents in two ways: (1) it has a
narrow, well-defined scope — identify the installed version, research its changelog and
capability set, and map capabilities to protocol test requirements; and (2) its output is
a **structured capability report** rather than free-form prose, because the code-evaluator
consumes it programmatically to determine whether specific tests should be attempted or
skipped based on the installed version's feature set.

This PRD modifies one file: `prompts/research-prompt.md`. It adds the Agent 4 specification
block, the capability report schema definition, and a new focus-specific guidance block for
"version" or "capability" focus strings. The SKILL.md orchestrator update that dispatches
Agent 4 and wires its output into the code-evaluator is covered by PRD-06; this PRD defines
the schema that PRD-06 references.

## Goals

1. **Agent 4 specification.** Add a clearly delineated Agent 4 section to the research
   prompt that instructs the agent to: identify the installed version of the tool, locate
   and analyze the changelog and release notes, and produce a structured capability report.

2. **Capability report schema.** Define the output schema inline in the prompt so that both
   Agent 4 (the producer) and the code-evaluator (the consumer, via SKILL.md's consumer
   contract) reference the same authoritative definition. The schema includes: installed
   version, release date, capability table, and breaking changes list.

3. **Capability table covers protocol-relevant features.** The capability table maps
   features that are exercised by protocol test suites (e.g., DCPF, ACPF, DC OPF, AC OPF,
   SCUC, SCED, PTDF extraction, CSV import, MATPOWER import, contingency analysis) to
   version availability data. This enables the code-evaluator to skip or fail tests for
   features that the installed version does not support, rather than producing misleading
   error traces.

4. **Focus-specific guidance.** Add a new block in the Focus-Specific Guidance section for
   research focus strings containing "version" or "capability", paralleling the existing
   blocks for "API", "extension", and "limitation" focuses.

5. **Output path convention.** Agent 4 writes its output to `research-version.md` (the
   focus slug), consistent with the existing `research-{focus_slug}.md` pattern used by
   Agents 1-3.

6. **Backward compatibility.** Agents 1-3 are not modified. The shared preamble (Research
   Methods, Quality Standards) continues to apply to all four agents. Agent 4 adds to the
   prompt; it does not alter existing content.

## Non-Goals

1. **No SKILL.md changes.** The orchestrator dispatch of Agent 4 and the
   `{{version_capability_report}}` variable wiring are PRD-06 scope.

2. **No code-evaluator changes.** The code-evaluator's consumption of the capability report
   (version-gated test skipping) is PRD-04 scope.

3. **No executable validation code.** The capability report is a markdown document with
   structured YAML frontmatter, not a programmatic artifact. Validation is via success
   criteria checks on the prompt text, not runtime code.

4. **No version pinning or upgrade recommendations.** Agent 4 reports what is installed and
   what capabilities it has. It does not recommend upgrading or changing versions.

5. **No modification to existing agent focus strings.** The focus strings for Agents 1-3
   are defined in SKILL.md, not in the research prompt. This PRD does not change them.

## Data Structures

### Capability Report Schema

Agent 4's output file (`research-version.md`) uses the following structure. The schema is
defined in the prompt so that Agent 4 produces conformant output without external references.

```yaml
---
tool: "{{tool_name}}"
installed_version: "X.Y.Z"          # semver or tool-native version string
release_date: "YYYY-MM-DD"          # release date of the installed version
latest_version: "X.Y.Z"             # latest stable release as of research date
latest_release_date: "YYYY-MM-DD"   # release date of the latest version
research_date: "YYYY-MM-DD"         # date this report was produced
---
```

#### Capability Table

A markdown table in the body of the report with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `feature` | string | Protocol-relevant feature name (e.g., "DC Power Flow", "AC OPF", "CSV Import"). Drawn from a canonical list in the prompt. |
| `supported` | boolean | Whether the installed version supports this feature. Values: `yes`, `no`, `partial`. |
| `since_version` | string | The version in which the feature was introduced or became stable. `unknown` if not determinable from changelog. |
| `notes` | string | Brief explanation. For `partial` support, describes what subset works. For `no`, describes whether it is planned, deprecated, or never existed. |

**Canonical feature list** (Agent 4 must cover at minimum):

| Feature Name | Protocol Suite(s) |
|-------------|-------------------|
| DC Power Flow (DCPF) | A, G |
| AC Power Flow (ACPF) | A, G |
| DC Optimal Power Flow (DC OPF) | A |
| AC Optimal Power Flow (AC OPF) | A |
| Security-Constrained Unit Commitment (SCUC) | A |
| Security-Constrained Economic Dispatch (SCED) | A |
| PTDF / Shift Factor Extraction | B |
| Contingency Analysis (N-1) | B |
| Custom Constraint Injection | C |
| Network Graph Access | C |
| CSV Data Import | G |
| MATPOWER Case Import | A, G |
| Multi-Period / Time Series | B |
| Warm Start / Solution Reuse | D |
| Parallel Computation | D |

Agent 4 may add additional rows for tool-specific capabilities discovered during research,
but all 15 canonical features must appear.

#### Breaking Changes List

A markdown section listing breaking changes between the installed version and the latest
release (or the last 3 major/minor versions if no upgrade path is relevant). Each entry
includes:

```markdown
### Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|---------------------|
| X.Y.Z   | Removed `foo()` API | Affects test B-2 (PTDF extraction) |
| ...     | ...    | ...                 |
```

If the installed version is the latest, this section states "Installed version is the
latest stable release. No breaking changes to report."

#### Full Output Template

The complete output file structure that Agent 4 must produce:

```markdown
---
tool: "{{tool_name}}"
installed_version: "X.Y.Z"
release_date: "YYYY-MM-DD"
latest_version: "X.Y.Z"
latest_release_date: "YYYY-MM-DD"
research_date: "YYYY-MM-DD"
---

# {{tool_name}} — Version Capability Report

## Version Summary

- **Installed version:** X.Y.Z (released YYYY-MM-DD)
- **Latest stable version:** X.Y.Z (released YYYY-MM-DD)
- **Version gap:** N minor/major versions behind (or "up to date")
- **End-of-life status:** Active / Maintenance-only / EOL

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 0.1.0 | `network.lpf()` or equivalent |
| ... | ... | ... | ... |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|---------------------|
| ... | ... | ... |

## Changelog Analysis

### Key Changes in Installed Version
- <notable changes relevant to evaluation>

### Upcoming Features (next release / dev branch)
- <features in development that may affect future evaluations>

## Sources

1. <URL or file path>
2. ...

## Gaps and Uncertainties

- <what could not be determined>
```

## API

No executable API functions. This PRD modifies a markdown prompt template, not code. The
capability report schema above serves as the contract between Agent 4 (producer) and the
code-evaluator (consumer).

### Prompt template validation (conceptual)

The following checks are applied as success criteria against the prompt text, not as
runtime functions:

- **Agent 4 section exists** — a clearly delimited section for Agent 4 with a descriptive
  heading.
- **Schema is inline** — the capability report schema (YAML frontmatter fields, capability
  table columns, breaking changes format) is defined within the Agent 4 section, not in an
  external file.
- **Canonical feature list present** — all 15 protocol-relevant features are listed.
- **Focus-specific guidance block exists** — a new conditional block for "version" or
  "capability" focus strings.

## Success Criteria

Each criterion is a verifiable check on the updated `prompts/research-prompt.md` file.

### Agent 4 section structure (3 checks)

1. **SC-01: Agent 4 heading exists.** The prompt contains a clearly labeled section for
   Agent 4 (e.g., `### Agent 4 — Version-Awareness` or equivalent) that is visually
   distinct from the existing agent-agnostic content.

2. **SC-02: Agent 4 task description.** The Agent 4 section describes three tasks:
   (a) identify the installed version of the tool, (b) research the changelog and release
   notes for the installed and adjacent versions, (c) produce a structured capability
   report mapping features to version availability.

3. **SC-03: Agent 4 output path.** The Agent 4 section specifies that the output file
   uses the focus slug `research-version.md`, consistent with the `research-{focus_slug}.md`
   pattern.

### Capability report schema (5 checks)

4. **SC-04: YAML frontmatter schema.** The prompt defines the required YAML frontmatter
   fields: `tool`, `installed_version`, `release_date`, `latest_version`,
   `latest_release_date`, `research_date`.

5. **SC-05: Capability table columns.** The prompt defines the capability table with four
   columns: `feature` (string), `supported` (yes/no/partial), `since_version` (string),
   `notes` (string).

6. **SC-06: Canonical feature list.** The prompt includes a canonical list of at least 15
   protocol-relevant features that Agent 4 must cover, including at minimum: DCPF, ACPF,
   DC OPF, AC OPF, SCUC, SCED, PTDF extraction, contingency analysis, custom constraint
   injection, network graph access, CSV import, MATPOWER import, multi-period/time series,
   warm start, and parallel computation.

7. **SC-07: Breaking changes section.** The prompt defines a breaking changes section
   format with columns: `Version`, `Change`, `Impact on Evaluation`. The prompt specifies
   behavior when the installed version is the latest (explicit "no breaking changes"
   statement).

8. **SC-08: Full output template.** The prompt includes a complete output template showing
   the assembled document structure (frontmatter + Version Summary + Capability Table +
   Breaking Changes + Changelog Analysis + Sources + Gaps and Uncertainties).

### Focus-specific guidance (2 checks)

9. **SC-09: New guidance block.** The Focus-Specific Guidance section contains a new
   conditional block triggered by focus strings containing "version" or "capability".

10. **SC-10: Guidance content.** The new guidance block instructs the agent to: identify
    the installed version via package metadata or CLI, locate the official changelog and
    release notes, map each canonical feature to version availability, and document breaking
    changes between installed and latest versions.

### Version identification methods (2 checks)

11. **SC-11: Python version detection.** The Agent 4 section or the version-specific
    guidance describes how to detect the installed version for Python tools (e.g.,
    `import <pkg>; print(<pkg>.__version__)` via `dc-exec`).

12. **SC-12: Julia version detection.** The Agent 4 section or the version-specific
    guidance describes how to detect the installed version for Julia tools (e.g.,
    reading `Project.toml` / `Manifest.toml` or `using Pkg; Pkg.status()`).

### Quality and compatibility (4 checks)

13. **SC-13: Quality standards apply.** The Agent 4 section does not exempt itself from the
    existing Quality Standards (cite everything, distinguish versions, flag contradictions,
    be specific, note what's missing). Either the section explicitly states that Quality
    Standards apply, or it is placed within the scope of the existing Quality Standards
    section so inheritance is unambiguous.

14. **SC-14: Agents 1-3 unchanged.** The existing Research Methods, Output Format, Quality
    Standards, and Focus-Specific Guidance sections for Agents 1-3 are not modified. The
    only additions are: the Agent 4 section and the new focus-specific guidance block.

15. **SC-15: Structured output distinct from free-form.** The prompt clearly distinguishes
    Agent 4's structured output format from the free-form markdown template used by
    Agents 1-3. The agent is instructed to use the capability report template instead of
    the generic Key Findings / Detailed Notes template.

16. **SC-16: Partial support semantics.** The capability table's `supported` column allows
    three values (`yes`, `no`, `partial`), and the prompt explains that `partial` requires
    the `notes` field to describe what subset of the feature works.

### Schema completeness (2 checks)

17. **SC-17: Suite mapping present.** Each canonical feature in the list is annotated with
    the protocol suite(s) it relates to (e.g., "DC Power Flow (DCPF) — Suites A, G"),
    enabling the code-evaluator to correlate capabilities with specific test IDs.

18. **SC-18: Unknown version handling.** The schema defines behavior when the agent cannot
    determine `since_version` for a feature: the field should be set to `unknown` rather
    than omitted or left blank.

## File Locations

| File | Action | Description |
|------|--------|-------------|
| `.claude/skills/evaluate-tool/prompts/research-prompt.md` | Edit | Add Agent 4 specification, capability report schema, version/capability focus-specific guidance block |

## Repository

`grc-tech-evaluation` (this repo).

## Dependencies

- **None within Phase 2.** This PRD is Tier 1 — it has no intra-phase dependencies and
  can be implemented in parallel with Deliverables 1, 2, and 5.

- **Downstream consumers:**
  - **PRD-04 (code-evaluator-prompt.md):** References the capability report schema when
    defining the `{{version_capability_report}}` input variable and version-gated test
    skipping logic.
  - **PRD-06 (SKILL.md):** References the Agent 4 output path (`research-version.md`) in
    the RESEARCH state dispatch and the consumer contract for the code-evaluator variable
    replacement.

## Open Questions

None. All design decisions were resolved in the phase plan:

- Structured output (not free-form): confirmed. The code-evaluator needs to parse
  capability data programmatically.
- Schema defined inline in the prompt (not in a separate reference file): confirmed.
  Keeps the contract co-located with the producing agent's instructions.
- 15 canonical features covering Suites A-D and G: confirmed. The list is extensible
  (Agent 4 may add tool-specific rows) but the canonical set is mandatory.
- `partial` as a third support value: confirmed. Binary yes/no is insufficient for
  features with subset implementations.
- Output path `research-version.md`: confirmed. Follows the existing slug convention.
