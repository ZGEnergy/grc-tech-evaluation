# Consistency Checker (Cross-Phase Structural) — Subagent Prompt Template

Audit the plan's high-level structure for contradictions, gaps, and inconsistencies across phases. This checker reads the executive plan, all phase plans, and all PRD READMEs — but NOT individual PRDs. Interface-level cross-phase checks between individual PRDs are handled by edge checker agents.

## Artifact Files

Read all of the following files using the Read tool:

{{artifact_file_list}}

These files include only: executive-plan.md, all phase-plan.md files, and all prds/README.md files.

## Check Categories

After reading all artifacts, check for these inconsistency types:

### 1. Phase Output/Input Alignment
Each phase's "What This Phase Produces" section must align with what downstream phases expect as inputs.

Look for:
- Phase A's "What This Phase Produces" describes outputs that Phase B (which depends on Phase A) never references
- Phase B's dependencies or introductory text references capabilities that Phase A's "What This Phase Produces" doesn't mention
- Mismatches between output descriptions and downstream consumer expectations

### 2. Scope Gaps at Executive Level
Something promised in the executive plan that no phase plan covers.

Look for:
- Executive plan objectives not addressed by any phase
- Executive plan deliverables not present in any phase plan
- Capabilities implied by the executive plan's vision that fall between phases

### 3. Scope Overlaps at Executive Level
Two phases covering the same or substantially overlapping scope.

Look for:
- Similar deliverables appearing in multiple phase plans
- Overlapping "What This Phase Produces" sections
- Ambiguous ownership of capabilities between phases

### 4. Open Question Conflicts Across Levels
Questions resolved at one level that contradict resolutions or assumptions at another level.

Look for:
- Executive-level OQ resolved differently than a phase-level OQ on the same topic
- Phase plan assumptions that contradict resolved executive-level OQs
- Phase-level OQ resolutions that are inconsistent across different phases

### 5. Naming and Convention Violations at Executive Level
Inconsistencies between the executive plan and phase plans in naming and numbering.

Look for:
- Phase names in executive plan don't match phase plan titles or directory names
- Phase numbers are inconsistent between executive plan and directory structure
- Deliverable counts in executive plan don't match actual deliverable counts in phase plans
- PRD README deliverable counts don't match phase plan deliverable counts

### 6. Phase Dependency Graph Consistency
The executive plan's Phase Dependencies table must be internally consistent and match per-phase metadata.

Look for:
- **Table symmetry**: If Phase B depends on Phase A, Phase A should enable Phase B (and vice versa)
- **Per-phase field match**: Each phase's "Dependencies" field in the executive plan must match the Phase Dependencies table
- **Tier validity**: No phase in Tier N depends on a phase in Tier N or later
- **Completeness**: Every phase appears in the dependency table
- **Phase plan cross-references**: Phase plans' dependency references (in Purpose sections, deliverable dependencies) are consistent with the executive-level dependency table

## Output Format

Report findings in this exact format:

```
INCONSISTENCY [<type>] [<severity>]: <one-line description>
  Files: <file1>, <file2>
  Detail: <2-3 sentences explaining the inconsistency>
  Suggested fix: <what should change in which file>
```

Where:
- `<type>` is one of: `SCOPE_GAP`, `SCOPE_OVERLAP`, `OQ_CONFLICT`, `NAMING_VIOLATION`, `DEPENDENCY_GRAPH_INCONSISTENCY`, `OUTPUT_INPUT_MISALIGNMENT`
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

On CRITICAL context warning: output all findings so far using the standard format, then append after the SUMMARY: `CONTEXT_EXHAUSTED: checked categories 1-<N> of 6` (where N is the last fully completed category).
