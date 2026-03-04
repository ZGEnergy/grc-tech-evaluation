# Consistency Checker (Intra-Phase) — Subagent Prompt Template

Audit artifacts within Phase {{phase_number}} ({{phase_name}}) for contradictions, gaps, and inconsistencies.

## Executive Plan Context

Use this to verify cross-phase dependency references from PRDs in this phase. Do NOT check other phases' internal artifacts — other agents handle that.

{{executive_plan_content}}

## Artifact Files

Read all of the following files using the Read tool:

{{artifact_file_list}}

These files include only the phase plan, PRDs README, and all PRDs within Phase {{phase_number}}. Do not attempt to read files from other phases.

## Check Categories

After reading all artifacts, check for these inconsistency types **within this phase only**:

### 1. Interface Mismatches
An output type, data structure, or function signature in one PRD does not match what a sibling PRD within this phase expects as input.

Look for:
- PRD A produces `TypeX` but sibling PRD B expects `TypeY` from PRD A
- Function return types that don't match caller expectations within this phase
- Data structure field names or types that differ between producer and consumer PRDs in this phase

**Cross-phase references:** If a PRD declares a dependency on a PRD in another phase, verify that the referenced phase exists in the executive plan and the dependency direction is consistent with the Phase Dependencies table. Do NOT check the actual content of the other phase's PRDs — the edge checker handles that.

### 2. Scope Gaps
Something needed by a downstream artifact within this phase that no upstream artifact produces.

Look for:
- Phase plan lists a capability that no PRD in this phase implements
- PRD depends on functionality not covered by any sibling PRD (and doesn't declare it as a cross-phase dependency)
- Phase plan's "What This Phase Produces" section describes outputs not implemented by any PRD

### 3. Scope Overlaps
Two PRDs within this phase implementing the same or substantially overlapping functionality.

Look for:
- Duplicate data structures defined in multiple PRDs within this phase
- Same function or capability described in multiple sibling PRDs without clear ownership
- Ambiguous boundaries between adjacent PRDs in this phase

### 4. Open Question Conflicts
A question resolved in one artifact within this phase contradicts the resolution or assumptions in another artifact within this phase.

Look for:
- Same question resolved differently in different documents within this phase
- An assumption in a PRD that contradicts a resolved OQ in the phase plan
- Unresolved questions that block resolved decisions elsewhere in this phase

### 5. Naming and Convention Violations
Inconsistencies in naming, numbering, or structural conventions within this phase.

Look for:
- PRD numbers in phase plan don't match actual PRD files
- Deliverable titles differ between phase plan and PRD headers
- File paths referenced in PRDs don't match the actual file organization
- Open question IDs that don't follow the `OQ-<scope>-<NN>` format
- Cross-references using wrong relative paths
- Repository names in `## Repository` sections don't match known repos in the workspace

### 6. Dependency Violations
Stated dependencies within this phase that create cycles or contradict the dependency graph.

Look for:
- Circular dependencies between PRDs in this phase
- **Import-dependency mismatches**: If a PRD's code blocks contain `from <module> import <symbol>` and that module maps to a sibling PRD (based on File Location paths), the importing PRD must list that sibling in its Internal Dependencies section. Check every import statement in every code block.
- PRD declares a dependency on a phase that the executive plan's Phase Dependencies table does not show as an upstream dependency of Phase {{phase_number}}

### 7. Symbol Completeness
Every symbol (class, enum, function, TypeAlias, constant) that sibling PRDs import from a given PRD's module must be declared in that PRD's Python code blocks.

Look for:
- PRD A's code blocks contain `from <module> import Foo` where `<module>` maps to PRD B's File Location, but PRD B has no code block defining `Foo` (no `class Foo`, `def Foo`, `Foo =`, or `Foo: TypeAlias`)
- PRD B mentions a type in prose (e.g., "returns a `CanonicalId`") but never provides a Python code block declaring it
- Enums, TypeAliases, and configuration dataclasses are commonly missing — check for these specifically

### 8. Dependency Graph Inconsistencies
The dependency tables and implementation tiers within this phase must be internally consistent.

Look for:
- **Phase plan Deliverable Dependencies table**: Does "Depends On" for each deliverable match the per-deliverable "Dependencies" field? Are "Enables" cross-references symmetric? Are implementation tiers topologically valid (no deliverable in Tier N depends on a deliverable in Tier N or later)?
- **PRDs README Dependency Graph**: Does it match the parent phase plan's Deliverable Dependencies table?
- **Cross-level consistency**: If a deliverable says it depends on a prior phase, does the executive plan's Phase Dependencies table confirm that Phase {{phase_number}} depends on that phase?

## Output Format

Report findings in this exact format:

```
INCONSISTENCY [<type>] [<severity>]: <one-line description>
  Files: <file1>, <file2>
  Detail: <2-3 sentences explaining the inconsistency>
  Suggested fix: <what should change in which file>
```

Where:
- `<type>` is one of: `INTERFACE_MISMATCH`, `SCOPE_GAP`, `SCOPE_OVERLAP`, `OQ_CONFLICT`, `NAMING_VIOLATION`, `DEPENDENCY_VIOLATION`, `SYMBOL_COMPLETENESS`, `DEPENDENCY_GRAPH_INCONSISTENCY`
- `<severity>` is one of: `HIGH` (blocks implementation), `MEDIUM` (causes confusion), `LOW` (cosmetic)

If no inconsistencies are found, output exactly:

```
NO INCONSISTENCIES FOUND
```

List all findings, then provide a summary count:

```
SUMMARY: <N> inconsistencies found (<H> high, <M> medium, <L> low)
```

## Context Exhaustion

On CRITICAL context warning: output all findings so far using the standard format, then append after the SUMMARY: `CONTEXT_EXHAUSTED: checked categories 1-<N> of 8` (where N is the last fully completed category).
