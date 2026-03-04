# Handoff Schema

Handoff files enable session continuity when context limits are reached or when
passing state between evaluation tiers.

## File Format

Handoff files use YAML frontmatter followed by structured markdown sections.

### YAML Frontmatter

```yaml
---
type: handoff
tool: <tool_name>
dimension: <dimension>
source_tier: <TINY|SMALL|MEDIUM>
target_tier: <SMALL|MEDIUM>
timestamp: <ISO 8601>
status: <complete|partial>
---
```

### Required Sections

```markdown
# Handoff: {{dimension}} — {{source_tier}} → {{target_tier}}

## Completed Work

<What was accomplished in the source tier. List test IDs and their results.>

## Artifacts Produced

- `<path>` — <description>
- `<path>` — <description>

## Key Findings for Next Tier

<Findings from the source tier that affect how the target tier should be approached.
E.g., "Solver convergence required non-default tolerance on SMALL, expect same on MEDIUM.">

## State to Carry Forward

<Any variables, solver settings, or configuration that the next tier agent needs.>

## Next Steps

<Specific instructions for what the target tier agent should do first.>
```

## Tier Handoff vs Session Handoff

**Tier handoff** (`<dimension>-handoff-<tier>.md`): Passes findings between network
tiers within the same dimension. Written by code-evaluator agents after completing
all tests on a tier.

**Session handoff** (`.session-handoff.md`): Written by the orchestrator when hitting
context limits. Contains the full state machine position and is read on resume.

## Session Handoff Schema

```yaml
---
type: session-handoff
tool: <tool_name>
state: <CONFIGURE|RESEARCH|GATE|EVALUATE|SYNTHESIZE>
completed_states: [<list>]
completed_dag_steps: [<list>]
scale_cap: <TINY|SMALL|MEDIUM>
timestamp: <ISO 8601>
---
```

```markdown
# Session Handoff

## Current Position

State: {{state}}, Step: {{current_dag_step}}

## Completed Artifacts

- `eval-config.yaml` — <exists|missing>
- `research-context.md` — <exists|missing>
- Gate results: <summary>
- Completed dimensions/tiers: <list>

## In-Flight Work

<Any agents that were running when the session ended.
Include their dimension, tier, and test IDs so they can be re-dispatched.>

## Next Action

<Exact next step to take on resume.>
```
