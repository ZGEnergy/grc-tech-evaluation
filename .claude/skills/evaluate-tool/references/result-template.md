# Result File Template

Every test produces a result file in the dimension's results directory. This template
defines the required format.

## File Location

Every artifact filename includes both the test ID and a human-readable slug from
the eval-config. The slug is a short snake_case suffix derived from the test description.

```
evaluations/<tool>/results/<dimension>/<test_id>_<slug>.md
```

For tests run on multiple tiers, append the tier:

```
evaluations/<tool>/results/<dimension>/<test_id>_<slug>_<tier>.md
```

Examples:
- `evaluations/pypsa/results/expressiveness/A-1_dcpf.md` (grade assessment on MEDIUM)
- `evaluations/pypsa/results/expressiveness/A-1_dcpf_TINY.md` (functional verification)
- `evaluations/pypsa/results/expressiveness/A-8_stochastic_timeseries.md`
- `evaluations/pypsa/results/extensibility/B-9_ptdf_extraction.md`

## Required YAML Frontmatter

```yaml
---
test_id: <test_id>
tool: <tool_name>
dimension: <dimension>
network: <TINY|SMALL|MEDIUM|N/A>
status: pass|fail|qualified_pass
workaround_class: null|stable|fragile|blocking
wall_clock_seconds: <float|null>
peak_memory_mb: <float|null>
loc: <int|null>
solver: <solver_name|null>
timestamp: <ISO 8601>
---
```

### Status Values

- **pass** — Test completed successfully, pass condition met
- **fail** — Test did not meet pass condition
- **qualified_pass** — Pass condition met but with caveats (e.g., workaround needed,
  non-standard configuration). Requires explanation in narrative.

## Required Markdown Sections

### For Code Tests (Suites A, B, C)

```markdown
# <test_id>: <description>

## Result: PASS|FAIL|QUALIFIED PASS

## Approach

<How the test was implemented. API calls used. Solver settings. Any deviations
from the standard approach.>

## Output

<Key outputs from the test. Use tables or code blocks for numerical results.
Include enough detail to verify correctness.>

## Workarounds

<If status is qualified_pass or workaround_class is non-null:>

- **What:** <description of workaround>
- **Why:** <what limitation necessitated it>
- **Durability:** <stable|fragile|blocking> — <rationale for classification>
- **Grade impact:** <how this affects scoring>

<If no workarounds: "None required.">

## Timing

- **Wall-clock:** <seconds>
- **Peak memory:** <MB> (or "not measured" with reason)
- **Solver iterations:** <count> (for iterative solvers)
- **CPU cores used:** <count> (if parallelism observed)

## Test Script

**Path:** `<relative path to test script>`

<Optionally include key code snippets inline, especially if they illustrate
the tool's API or a workaround.>
```

### For Audit Tests (Suites D, E, F)

```markdown
# <test_id>: <description>

## Result: PASS|FAIL|QUALIFIED PASS|INFORMATIONAL

## Finding

<Concise summary — 1-2 sentences.>

## Evidence

<Detailed evidence. Include:>
- URLs with access dates
- File paths and line numbers
- Command output excerpts
- Quantitative data (counts, dates, percentages)

## Implications

<What this finding means for the criterion grade. Reference rubric standards.>
```

## Cross-Linking

- Link to test scripts: `[test script](../../../tests/<dimension>/test_<id_lower>_<slug>.py)`
- Link to observations: `[observation](../observations/<tag>-<dim>-<id>_<slug>.md)`
- Link to handoffs: `[handoff](./<dim>-handoff-<tier>.md)`

## Quality Checklist

Before finalizing a result file, verify:
- [ ] YAML frontmatter is valid and all required fields are present
- [ ] Status accurately reflects whether the pass condition was met
- [ ] Workaround class is correct per `workaround-classification.md`
- [ ] Timing data is recorded (or explicitly noted as unmeasured)
- [ ] Test script path is correct and the script is self-contained
- [ ] Numerical outputs are present (not just "test passed")
- [ ] For qualified passes, the qualification is clearly explained
