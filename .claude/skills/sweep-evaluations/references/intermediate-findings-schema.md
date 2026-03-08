# Intermediate Findings Schema

Per-tool sweep agents produce two files: a structured `findings.yaml` and a narrative
`findings.md`. The YAML file feeds downstream aggregation; the markdown provides detail
for the findings report writer.

## findings.yaml

```yaml
tool: <tool_name>
source_version: <protocol_version>  # e.g., "v4"
timestamp: <ISO 8601>
evaluation_summary:
  total_tests: <int>
  pass: <int>
  fail: <int>
  qualified_pass: <int>
  informational: <int>

findings:
  - id: <finding_id>            # e.g., "pypsa-F01"
    category: <category>        # see Category Taxonomy below
    severity: low|medium|high
    test_ids: [<test_id>, ...]  # tests where this finding manifests
    title: <one-line summary>
    description: <2-3 sentence explanation>
    evidence:
      - file: <path to result file>
        excerpt: <relevant quote or data point>
    cross_tool_relevance: <none|likely|confirmed>
    # "likely" = the finding pattern probably affects other tools too
    # "confirmed" = the agent found evidence in shared protocol/rubric
    probe_recommended: <boolean>
    probe_type: <null|timing_verification|convergence_check|formulation_audit|claim_verification>
    proposed_action: <null|redesign_test|add_verification|adjust_scoring|remove_test|add_test>

extraordinary_claims:
  - test_id: <test_id>
    claim: <what the result asserts>
    concern: <why this is suspicious>
    evidence_quality: weak|moderate|strong
    probe_recommended: true
    probe_type: <probe type>
```

## Category Taxonomy

| Category | Description |
|----------|-------------|
| `low_signal` | Test produces identical outcomes across most/all tools — low discriminative value |
| `misleading_result` | Result is technically correct but conveys wrong impression (e.g., qualified_pass with 97% failure rate) |
| `extraordinary_claim` | Result asserts something surprising without sufficient verification (e.g., estimated timings, untested convergence) |
| `infrastructure_friction` | Test difficulty stems from test infrastructure (e.g., .m format parsing) rather than tool capability |
| `network_insufficiency` | Test network is too small/simple to exercise the feature being tested |
| `scoring_inconsistency` | Same pattern scored differently across tools or dimensions |
| `missing_verification` | Result accepted without runtime verification that should be feasible |
| `test_design_gap` | Test doesn't adequately assess what the rubric criterion requires |
| `redundant_test` | Test measures substantially the same thing as another test |

## findings.md

The narrative findings file uses this structure:

```markdown
# {{tool_name}} — Sweep Findings ({{source_version}})

## Summary

<3-5 sentences: overall evaluation quality, key issues found, probe recommendations.>

## Finding Details

### {{finding_id}}: {{title}}

**Category:** {{category}} | **Severity:** {{severity}}
**Tests:** {{test_ids}}

<Detailed explanation with evidence excerpts. Include specific quotes from result files,
numerical data, and cross-references to protocol/rubric requirements.>

**Cross-tool relevance:** {{cross_tool_relevance}}
**Proposed action:** {{proposed_action}}

### {{finding_id}}: {{title}}
<...repeat for each finding...>

## Extraordinary Claims

### {{test_id}}: {{claim}}

**Concern:** {{concern}}
**Evidence quality:** {{evidence_quality}}

<Detail on why this claim needs verification and what a probe should check.>

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| A-1 | pass | — | — |
| A-2 | qualified_pass | stable | <brief note> |
| ... | | | |
```
