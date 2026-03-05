# Dependency Researcher — Subagent Prompt Template

Research the following dependency question for multi-repo work: **{{research_question}}**

## Context

### Scope Statement

{{scope_statement}}

### Target Repos

{{target_repos}}

### Workspace Root

`{{workspace_root}}`

## Instructions

Trace the dependency chain for the target repos to understand upstream interfaces and downstream consumers. Produce a structured summary that directly answers the research question.

### Step 1 — Read Workspace-Level Context

Read `{{workspace_root}}/CLAUDE.md` to understand the full repo map and dependency chain. Pay attention to the Repo Map section and how packages relate to one another.

### Step 2 — Read Target Repo Context

For each repo in `{{target_repos}}`, read:

1. `{{workspace_root}}/<repo>/CLAUDE.md` — architecture, key abstractions, and repo-specific conventions
2. `{{workspace_root}}/<repo>/pyproject.toml` — declared dependencies, optional extras, and version constraints. If `pyproject.toml` is absent, check `setup.py` or `setup.cfg` instead.

### Step 3 — Identify Upstream Packages

For each target repo, determine what it imports from other packages in the workspace:

- Scan `src/` (or the top-level package directory) for `import` and `from ... import` statements referencing internal packages (e.g., `zge-schemas`, `market-framework`, etc.)
- Cross-reference against the `[project.dependencies]` or `install_requires` declarations to confirm version constraints
- Note any interfaces (functions, classes, dataclasses, enums) that the target repo relies on from upstream packages

### Step 4 — Identify Downstream Consumers

Determine which other workspace repos depend on the target repos:

- For each other repo visible under `{{workspace_root}}`, check its `pyproject.toml` (or `setup.py`/`setup.cfg`) for references to the target repo's package name
- Note what the downstream consumer imports and uses — function calls, base classes, schema types, etc.
- Flag any version pins that would prevent a consumer from picking up changes

### Step 5 — Check Interface Contracts and Breaking Change Risks

- Identify public APIs (exported functions, classes, Pandera schemas, DAG task signatures) that downstream consumers call
- Note any interface that, if changed, would require coordinated updates across repos
- Check for version pinning that could prevent consumers from adopting a new release automatically

### Step 6 — Produce Structured Summary

Write a ~300 word summary with the sections below. Be specific: name actual packages, modules, classes, and functions. Avoid generic statements.

## Output Format

Produce a markdown report with the following sections:

## Upstream Dependencies

List the packages and internal repos that the target repo(s) depend on. For each, note:
- Package name and declared version constraint
- Key interfaces used (function names, class names, schema names)

## Downstream Consumers

List the workspace repos that depend on the target repo(s). For each, note:
- Repo name and declared version constraint on the target
- What they import or use from the target

## Interface Contracts

Enumerate the key interfaces that must be maintained or carefully extended:
- Public function signatures that downstream consumers call
- Base classes, abstract methods, or Pandera schemas that consumers extend or validate against
- DAG task signatures or config dataclasses that callers depend on

## Version Constraints

Summarize pinning and compatibility requirements:
- Exact pins (e.g., `==1.2.3`) vs. compatible-release pins (e.g., `~=1.2`)
- Any mismatch between what the target declares it needs and what consumers pin

## Breaking Change Risks

List concrete risks: what changes to the target would require coordinated updates in consumers? Examples:
- Removing or renaming a public function
- Changing a function signature in a non-backward-compatible way
- Changing a Pandera schema column name or type
- Bumping a dependency to a version incompatible with consumers

## Key Findings

2-4 sentences directly answering `{{research_question}}`. State conclusions plainly — what the plan author needs to know to scope and sequence multi-repo work correctly.
