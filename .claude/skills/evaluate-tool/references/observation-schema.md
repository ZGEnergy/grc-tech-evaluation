# Observation Schema

Observations are cross-cutting findings emitted by one dimension and consumed by another.
They enable information flow between evaluation agents without hard-coded wiring.

## File Naming

```
observations/<tag>-<source_dimension>-<test_id>_<slug>.md
```

Examples:
- `observations/api-friction-expressiveness-A-1_dcpf.md`
- `observations/doc-gaps-extensibility-B-2_graph_access.md`
- `observations/solver-issues-scalability-C-3_dcopf.md`

## File Format

```yaml
---
tag: <observation_tag>
source_dimension: <dimension that emitted this>
source_test: <test_id>
tool: <tool_name>
severity: low|medium|high
timestamp: <ISO 8601>
---
```

```markdown
# Observation: <brief title>

## Finding

<1-2 sentence description of the cross-cutting finding.>

## Context

<What was being tested when this was discovered. Enough detail for a consuming
agent to understand the finding without reading the full test result.>

## Implications

<What this means for consuming dimensions. E.g., "The lack of error message for
invalid bus types should be noted in the Accessibility audit (D-4).">
```

## Tag Taxonomy

| Tag | Description | Typical Emitters | Typical Consumers |
|-----|-------------|-----------------|-------------------|
| `api-friction` | Unintuitive API, excessive boilerplate, undocumented steps | expressiveness, extensibility, scalability | accessibility |
| `doc-gaps` | Had to read source code or issues instead of documentation | expressiveness, extensibility | accessibility, maturity |
| `workaround-needed` | Test required a workaround to pass | expressiveness, extensibility, scalability | extensibility |
| `solver-issues` | Solver convergence, performance, or compatibility problems | expressiveness, scalability | scalability |
| `license-flags` | Licensing or supply chain concerns encountered during testing | supply_chain | supply_chain |
| `arch-quality` | Software architecture observations (positive or negative) | extensibility | maturity |

## Severity Levels

- **low** — Minor friction, no grade impact on its own
- **medium** — Meaningful finding, likely affects grade
- **high** — Significant issue, strong grade impact

## When to Emit

Emit an observation when you encounter a finding that:
1. Is relevant to a dimension other than the one you're currently evaluating
2. Would not be discoverable by the consuming dimension's normal audit process
3. Has concrete evidence (not speculation)

Do NOT emit observations for:
- Findings already captured in the test result file
- Speculation about what another dimension might find
- Findings that are obvious from the tool's documentation
