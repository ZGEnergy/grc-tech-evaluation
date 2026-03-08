# Findings Report Template

The findings report (`sweep-reports/vN-to-vN+1.md`) is the audit trail for every
protocol/rubric change. It preserves rationale without cluttering the working documents.

## Structure

```markdown
# Evaluation Sweep: {{source_version}} → {{target_version}}

**Date:** <ISO 8601>
**Tools evaluated:** <list of tools included in sweep>
**Protocol version:** {{source_version}} (source) → {{target_version}} (target)

## Executive Summary

<5-8 sentences. How many tools were swept, how many findings, how many probes run,
key themes discovered, and the overall trajectory of changes (more rigorous testing,
better differentiation, verification requirements, etc.).>

## Cross-Tool Comparison Matrices

### Test Outcome Matrix

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER |
|---------|-------------|-------|------------|---------|-------------|----------|----------|
| A-1 | DCPF | pass | pass | pass | pass | pass | pass |
| A-2 | ACPF | pass | pass | qp | pass | qp | pass |
| ... | | | | | | | |

Legend: pass = pass, qp = qualified_pass, fail = fail, info = informational, — = not run

### Signal Analysis

| Test ID | Outcome Spread | Signal Level | Action |
|---------|---------------|-------------|--------|
| A-1 | 6/6 pass | Low (unanimous) | Consider: raise bar or merge with A-3 |
| A-8 | 1 pass, 5 fail | Low (infrastructure) | Redesign: test measures .m parsing, not stochastic |
| ... | | | |

### Grade Comparison

| Criterion | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER |
|-----------|-------|------------|---------|-------------|----------|----------|
| Expressiveness | B+ | B | B- | A- | B | A |
| Extensibility | ... | | | | | |
| ... | | | | | | |

## Low-Signal Tests

<For each test identified as low-signal, explain why it's low-signal, the evidence
(e.g., unanimous outcomes, infrastructure friction dominating), and the proposed
replacement or modification.>

### {{test_id}}: {{description}}

**Signal level:** Low — {{reason}}
**Outcome:** {{outcome across tools}}
**Root cause:** {{why this test doesn't differentiate}}
**Proposed action:** {{redesign/remove/merge/raise_bar}}
**{{target_version}} replacement:** {{new test ID if applicable, or "removed"}}

## Spot-Check Probe Results

<If probes were run, present results here. If skipped, note that.>

### Probe Summary

| Probe ID | Tool | Claim | Classification | Impact |
|----------|------|-------|----------------|--------|
| probe-001 | powersim | C-4 timing estimate | claim_debunked | Revise C-4 to require measured timing |
| ... | | | | |

### Probe Details

#### {{probe_id}}: {{claim}}

<Summary of what the probe found. Reference the full probe result file for details.>

**Classification:** {{classification}}
**Impact on {{target_version}}:** {{what changes as a result}}

## Proposed Changes

### Test Redesigns

#### {{test_id}} → {{new_test_id}}: {{description}}

**Rationale:** <Why the original test needed redesign. Reference specific cross-tool
evidence.>
**Evidence:** <Which tools' results demonstrated the problem, with finding IDs.>
**Change summary:** <What's different in the new test.>
**Cross-tool evidence count:** <N tools> (minimum 3 required for protocol changes)

### New Tests

#### {{test_id}}: {{description}}

**Rationale:** <Gap identified by the sweep that no existing test covers.>
**Evidence:** <Cross-tool findings that motivated this addition.>

### Removed Tests

#### {{test_id}}: {{description}}

**Rationale:** <Why this test is being removed. Typically: redundant with another test,
or measuring infrastructure rather than capability.>
**Superseded by:** {{new_test_id}} or "not replaced — capability covered by {{other_test_id}}"

### Scoring Changes

#### {{rubric_section}}: {{change description}}

**Rationale:** <Why the scoring criteria needed adjustment.>
**Before:** <Previous scoring language.>
**After:** <New scoring language.>

### Skill Updates

<Summary of changes to the evaluate-tool skill. Reference specific files modified.>

## Test-ID Mapping Table

This table enables cross-version comparability. Every {{source_version}} test must
appear exactly once.

| {{source_version}} Test | {{target_version}} Test | Relationship | Notes |
|------------------------|------------------------|-------------|-------|
| A-1 | A-1 | unchanged | — |
| A-2 | A-2 | modified | Added convergence verification |
| A-8 | A-8 | redesigned | Graduated stochastic criteria |
| C-8 | C-8a, C-8b | split | Separated SCOPF formulation from scale |
| B-4 | — | removed | Redundant with A-8 redesign |

**Relationship values:**
- `unchanged` — test passes through to new version without modification
- `modified` — same test ID, adjusted parameters/conditions
- `redesigned` — substantially different test under same or new ID
- `split` — one test became multiple
- `merged` — multiple tests became one
- `removed` — test dropped, not replaced
- `new` — no predecessor in {{source_version}}

## Deferred Items

<Items considered but not included in {{target_version}}, with rationale for deferral.>

## Methodology

- **Sweep date:** <date>
- **Tools analyzed:** <count> of 6 (list any excluded with reason)
- **Probes run:** <count> (or "skipped")
- **Evidence threshold:** Changes require cross-tool evidence from 3+ tools
- **Protocol source:** {{source_version}}
```
