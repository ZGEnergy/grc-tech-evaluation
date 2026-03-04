# Consistency Checker (Cross-Phase Edge) — Subagent Prompt Template

Audit the dependency edge between Phase {{upstream_phase_number}} ({{upstream_phase_name}}) and Phase {{downstream_phase_number}} ({{downstream_phase_name}}) for interface mismatches, naming inconsistencies, and dependency declaration errors at the PRD level.

This checker focuses on the boundary between two specific phases. Intra-phase issues are handled by separate agents.

## Artifact Files

Read all of the following files using the Read tool:

{{artifact_file_list}}

These files include both phase plans and all PRDs from both Phase {{upstream_phase_number}} and Phase {{downstream_phase_number}}.

## Check Categories

After reading all artifacts, check for these cross-boundary inconsistency types:

### 1. Interface Mismatches
Data structures, types, or function signatures produced by upstream PRDs that don't match what downstream PRDs expect.

Look for:
- Upstream PRD produces `TypeX` but downstream PRD expects `TypeY` as input from that upstream PRD
- Function return types in upstream PRDs that don't match parameter types in downstream PRDs that call them
- Data structure field names, types, or shapes that differ between upstream producer and downstream consumer
- Enum values defined in upstream PRDs that downstream PRDs reference with different names or missing entries
- Serialization format assumptions that differ (e.g., upstream writes Parquet, downstream expects JSON)

### 2. Naming Consistency
Function names, class names, module paths, and identifiers referenced across the phase boundary must match.

Look for:
- Downstream PRD references a class or function from an upstream PRD by a different name than the upstream PRD defines
- Module paths (file locations) referenced in downstream PRD imports that don't match the upstream PRD's `## File Location`
- Package or module names that differ between producer and consumer

### 3. Dependency Declarations
Downstream PRDs must correctly reference their upstream dependencies.

Look for:
- Downstream PRD uses types or functions from an upstream PRD but doesn't list it in `## Dependencies > Internal Dependencies`
- Downstream PRD references an upstream PRD by wrong number or title
- Downstream PRD lists a dependency on an upstream PRD that doesn't actually produce what the downstream PRD claims to consume
- Phase plan dependency fields that don't match the actual PRD-level dependencies

### 4. Scope Alignment
What the downstream phase expects from the upstream phase must match what the upstream phase actually produces.

Look for:
- Downstream phase plan's stated dependencies on the upstream phase reference capabilities not found in any upstream PRD
- Upstream phase plan's "What This Phase Produces" section doesn't cover what downstream PRDs actually consume
- Downstream PRDs assume upstream functionality that falls in a gap between upstream PRDs

## Output Format

Report findings in this exact format:

```
INCONSISTENCY [<type>] [<severity>]: <one-line description>
  Files: <file1>, <file2>
  Detail: <2-3 sentences explaining the inconsistency>
  Suggested fix: <what should change in which file>
```

Where:
- `<type>` is one of: `INTERFACE_MISMATCH`, `NAMING_VIOLATION`, `DEPENDENCY_VIOLATION`, `SCOPE_ALIGNMENT`
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

On CRITICAL context warning: output all findings so far using the standard format, then append after the SUMMARY: `CONTEXT_EXHAUSTED: checked categories 1-<N> of 4` (where N is the last fully completed category).
