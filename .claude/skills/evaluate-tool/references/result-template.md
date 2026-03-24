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
protocol_version: <version from eval-config>    # metadata only
skill_version: <version from evaluate-tool SKILL.md frontmatter>
test_hash: <8-char hex from eval-config test entry>  # used for stale detection
status: pass|fail|qualified_pass|partial_pass|constrained_pass|informational
workaround_class: null|stable|fragile|blocking
blocked_by: null|<test_id>          # If this test failed solely because a prerequisite failed
wall_clock_seconds: <float|null>
timing_source: measured|estimated   # "estimated" timings cannot support pass/qualified_pass
peak_memory_mb: <float|null>
convergence_residual: <float|null>  # For AC convergence tests — final mismatch
convergence_iterations: <int|null>  # For iterative solvers — NR iteration count
convergence_evidence_quality: null|residual_reported|iteration_count_reported|binary_convergence_api|proxy_voltage  # AC solve tests only
loc: <int|null>
solver: <solver_name|null>
# Scalability (Suite C) tests only:
cpu_threads_used: <int|null>        # Thread count used by solver (C-suite)
cpu_threads_available: <int|null>   # Total cores available on test machine (C-suite)
# FNM ingestion (Suite G) tests only:
ingestion_path: null|pss_e_v33|matpower_ppc|matpower_raw  # Which input path was used
# SCED tests (A-6, B-6) only:
sced_mode: null|full_sced|ed_only|ed_with_security
# Gate tests only:
test_category: null|gate_minimum_bar  # Gate tests are excluded from pass rate statistics
timestamp: <ISO 8601>
---
```

### Status Values

- **pass** — Test completed successfully, pass condition met
- **fail** — Test did not meet pass condition
- **qualified_pass** — Pass condition met with a stable workaround; full capability
  demonstrated, low friction. Requires explanation in narrative.
- **partial_pass** — Capability partially demonstrated; non-trivial workaround required,
  or some criterion unmet. Maps to `workaround_class: fragile` or `blocking`. Scores
  lower than qualified_pass. Never assign to a `workaround_class: blocking` result.
- **constrained_pass** — Capability demonstrated under constraints that limit
  generalizability (e.g., uncongested network, single-threaded solver, simplified
  formulation). Non-converged SCOPF runs should be constrained_pass. Solver crash on
  the grade network should be fail, not constrained_pass.
- **informational** — Finding recorded for context only; does not affect grades
  (used by audit tests, especially p2_readiness)

### Gate Tests

Result files for G-1, G-2, G-3 must include `test_category: gate_minimum_bar`. These
tests are excluded from cross-tool pass rate numerators and denominators. A pass outcome
is expected and provides no discriminative signal; a fail is disqualifying.

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
- **Timing source:** measured|estimated (estimated timings cannot support pass/qualified_pass)
- **Peak memory:** <MB> (or "not measured" with reason)
- **Solver iterations:** <count> (for iterative solvers)
- **Convergence residual:** <float> (for AC convergence tests — final power mismatch)
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
- [ ] `protocol_version` is present (metadata)
- [ ] `skill_version` is present and matches the `skill_version` in the evaluate-tool SKILL.md frontmatter
- [ ] `test_hash` is present and matches the `test_hash` for this test ID in `eval-config.yaml`
- [ ] Status accurately reflects whether the pass condition was met
- [ ] Status is one of: pass / fail / qualified_pass / partial_pass / constrained_pass / informational
- [ ] `workaround_class: blocking` result never uses status `qualified_pass` — must be `partial_pass` or `fail`
- [ ] Workaround class is correct per `workaround-classification.md`
- [ ] Timing data is recorded (or explicitly noted as unmeasured)
- [ ] `timing_source` is `measured` for any pass/qualified_pass/partial_pass on scalability tests
- [ ] `blocked_by` is set if this test failed due to a prerequisite failure
- [ ] For AC convergence tests: `convergence_residual`, `convergence_iterations`, and `convergence_evidence_quality` are recorded
- [ ] For Suite C tests: `cpu_threads_used` and `cpu_threads_available` are recorded
- [ ] For Suite G tests: `ingestion_path` is recorded (pss_e_v33 / matpower_ppc / matpower_raw)
- [ ] For A-6/B-6 SCED tests: `sced_mode` is recorded (full_sced / ed_only / ed_with_security)
- [ ] For gate tests (G-1/G-2/G-3): `test_category: gate_minimum_bar` is present
- [ ] Deviation metrics use scientific notation (:.6e), not fixed-point (:.6f)
- [ ] Test script path is correct and the script is self-contained
- [ ] Numerical outputs are present (not just "test passed")
- [ ] For qualified passes, the qualification is clearly explained
