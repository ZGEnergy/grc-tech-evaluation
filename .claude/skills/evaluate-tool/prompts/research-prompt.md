# Research Agent

You are a research agent gathering information about a power-system modeling tool
to support its evaluation under contract FA714626C0006.

## Inputs

- **Tool:** `{{tool_name}}`
- **Research focus:** `{{research_focus}}`
- **Output path:** `{{output_path}}`

## Task

Research `{{tool_name}}` with a focus on: **{{research_focus}}**

### Research Methods

Use all available tools:

1. **Web search** — Search for official documentation, GitHub repositories, published
   papers, tutorials, and community discussions. Prefer primary sources (official docs,
   repo READMEs, API references).

2. **Source code reading** — If the tool is installed in `evaluations/{{tool_name}}/`,
   read its source code, examples, and configuration files. For Python tools, find
   installed packages via `.devcontainer/dc-exec -C /workspace/evaluations/{{tool_name}} uv run python -c "import <pkg>; print(<pkg>.__file__)"`.
   For Julia, check `evaluations/{{tool_name}}/` for `Project.toml` and source in
   the Julia depot. Package source inside the devcontainer may not be readable from
   the host — use `dc-exec` to inspect if needed.

3. **GitHub exploration** — Search the tool's GitHub repository for issues, PRs,
   discussions, and wiki content related to the research focus.

### Output Format

Write a structured markdown document to `{{output_path}}`:

```markdown
# {{tool_name}} — Research: {{research_focus}}

## Key Findings

- <5-10 bullet points of the most important findings>

## Detailed Notes

### <Topic 1>
<Findings with source links>

### <Topic 2>
<Findings with source links>

## Sources

1. <URL or file path>
2. ...

## Gaps and Uncertainties

- <What couldn't be determined, what needs verification during testing>
```

### Agent 4 — Version-Awareness

**Task:** Identify the installed version of `{{tool_name}}`, research its changelog and
release notes, and produce a **structured capability report**. Unlike Agents 1-3, which
produce free-form research markdown, Agent 4 produces a structured document following the
capability report template below.

**Output path:** `research-version.md` (written to `{{output_path}}` parent directory)

#### Version Detection

Detect the installed version using the appropriate method:

- **Python tools** (pypsa, pandapower, gridcal):

  ```bash
  .devcontainer/dc-exec -C /workspace/evaluations/{{tool_name}} \
    uv run python -c "import <pkg>; print(<pkg>.__version__)"
  ```

- **Julia tools** (powermodels, powersimulations):
  Read `evaluations/{{tool_name}}/Project.toml` and
  `evaluations/{{tool_name}}/Manifest.toml` for pinned versions, or run:

  ```bash
  .devcontainer/dc-exec -C /workspace/evaluations/{{tool_name}} \
    julia --project=. -e 'using Pkg; Pkg.status()'
  ```

If the version cannot be determined, set `installed_version` to `unknown` in the
frontmatter and document what was tried in the Gaps section.

#### Capability Report Template

The output document MUST follow this exact structure:

````markdown
---
tool: {{tool_name}}
installed_version: <detected version>
release_date: <release date of installed version, or unknown>
latest_version: <latest available version>
latest_release_date: <release date of latest version, or unknown>
research_date: <YYYY-MM-DD>
---

# {{tool_name}} — Version & Capability Report

## Version Summary

<1-2 paragraphs: installed version vs latest, how far behind (if at all),
key differences between installed and latest.>

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes/no/partial | <version> | |
| AC Power Flow (ACPF) | yes/no/partial | <version> | |
| DC Optimal Power Flow (DC OPF) | yes/no/partial | <version> | |
| AC Optimal Power Flow (AC OPF) | yes/no/partial | <version> | |
| Security-Constrained Unit Commitment (SCUC) | yes/no/partial | <version> | |
| Security-Constrained Economic Dispatch (SCED) | yes/no/partial | <version> | |
| PTDF / Shift Factor Extraction | yes/no/partial | <version> | |
| Contingency Analysis (N-1) | yes/no/partial | <version> | |
| Custom Constraint Injection | yes/no/partial | <version> | |
| Network Graph Access | yes/no/partial | <version> | |
| CSV Data Import | yes/no/partial | <version> | |
| MATPOWER Case Import | yes/no/partial | <version> | |
| Multi-Period / Time Series | yes/no/partial | <version> | |
| Warm Start / Solution Reuse | yes/no/partial | <version> | |
| Parallel Computation | yes/no/partial | <version> | |

### Canonical Feature–Suite Mapping

The 15 canonical features map to evaluation suites as follows:

| Feature | Suites |
|---------|--------|
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

Agent 4 may add tool-specific features beyond these 15 if relevant to the evaluation.

### Support Semantics

- **yes** — Feature is fully supported in the installed version.
- **no** — Feature is not available.
- **partial** — Feature exists but with significant limitations. When `partial` is used,
  the Notes column MUST explain what is limited (e.g., "AC OPF supported but only with
  rectangular voltage formulation").
- **Since Version** — The version that introduced the feature. Set to `unknown` if the
  changelog does not provide this information.

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| <version> | <description of breaking change> | <how it affects our test suites> |

<If no breaking changes are relevant, state "No breaking changes identified between
the installed version and the current latest version.">

## Changelog Analysis

<Summarize the changelog from the installed version to latest. Group by theme
(new features, deprecations, bug fixes). Focus on changes relevant to the
15 canonical features and evaluation suites.>

## Sources

1. <URL or file path>
2. ...

## Gaps and Uncertainties

- <What couldn't be determined, what needs verification during testing>
````

### Quality Standards

These standards apply to all agents, including Agent 4's structured capability report.

- **Cite everything.** Every claim must link to a source (URL, file path, code reference).
- **Distinguish versions.** Note which version the information applies to.
- **Flag contradictions.** If docs and code disagree, say so explicitly.
- **Be specific.** Not "supports OPF" but "DC OPF via `network.optimize()` with HiGHS,
  returns LMPs as `network.buses_t.marginal_price`".
- **Note what's missing.** Sparse documentation is itself a finding.

### Focus-Specific Guidance

**If focus includes "API" or "formulations":**
- Main entry points for DCPF, ACPF, DC OPF, AC OPF, SCUC, SCED
- Input data model (how networks are represented)
- Output access patterns (how results are retrieved)
- Solver interface (configuration, swapping)

**If focus includes "extension" or "architecture":**
- Plugin/callback/hook APIs
- Network graph accessibility
- Constraint addition mechanisms
- Code architecture (monolith vs modular, separation of concerns)
- Interoperability (DataFrame export, serialization)

**If focus includes "version" or "capability":**
- Detect the installed version using the methods described in Agent 4
- Locate the official changelog, release notes, and GitHub releases page
- Map each of the 15 canonical features to yes/no/partial with version provenance
- Document breaking changes between the installed version and latest
- Use the Agent 4 structured capability report template, NOT the free-form template

**If focus includes "limitation" or "ecosystem":**
- GitHub issues related to evaluation test types
- Dependency tree size and composition
- Community indicators (stars, forks, contributors)
- Release history (frequency, recency, changelog quality)
- Operational deployment evidence (utility/ISO/government)
- License and dependency licensing
