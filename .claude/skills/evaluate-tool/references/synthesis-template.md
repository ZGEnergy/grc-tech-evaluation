# Synthesis Report Template

The synthesis report compiles all evaluation results into per-criterion summaries
with traceability to test evidence.

## File Location

```
evaluations/<tool>/results/synthesis.md
```

## Required Sections

### 1. Executive Summary

3-5 sentences covering:
- Overall tool characterization (strengths + positioning)
- Gate status (supply chain pass/fail)
- Most notable strengths and weaknesses
- Scale cap applied (if any)

### 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | A/A-/B+/B/B-/C+/C/C-/F | High/Medium/Low | 1-line |
| Extensibility | ... | ... | ... |
| Scalability | ... | ... | ... |
| Workforce Accessibility | ... | ... | ... |
| Maturity & Sustainability | ... | ... | ... |
| Supply Chain (Gate) | ... | ... | ... |

**Confidence levels:**
- **High** — Clear, unambiguous evidence from multiple tests
- **Medium** — Evidence supports the grade but some judgment involved
- **Low** — Limited or ambiguous evidence; needs human spot-check

### 3. Per-Criterion Detail

For each criterion, include:

#### Strengths
Bulleted list, each item linked to a specific test ID:
- "Native DC OPF with LMP extraction ([A-3](expressiveness/A-3_dcopf.md))"

#### Weaknesses
Same format with test ID links.

#### Workarounds Required
List with durability class:
- "Custom constraint addition requires internal API ([B-1](extensibility/B-1_custom_constraints.md)) — **fragile**"

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 | TINY | pass | — | 0.3s | 15 |

#### Grade Rationale
2-3 sentences explaining the grade against rubric standards. Must reference specific
rubric language (e.g., "Meets the B+ standard: 'Mostly strong, one meaningful gap
with stable workaround'").

### 4. Cross-Cutting Observations

Synthesize observation files into thematic sections:
- **API Friction Patterns** — from `api-friction` tags
- **Documentation Gaps** — from `doc-gaps` tags
- **Solver Ecosystem** — from `solver-issues` tags
- **Architecture Quality** — from `arch-quality` tags

### 5. Items Requiring Human Spot-Check

Checklist of items needing manual verification:

```markdown
- [ ] <Test with complex judgment call> — <reason, e.g., "native vs loop distinction">
- [ ] <Qualified pass test> — <what qualified it>
- [ ] <Borderline workaround classification> — <stable vs fragile rationale>
```

Always flag (derive from actual results, not a hardcoded list):
- Tests involving subjective classification (native vs wrapper, pruning correctness, etc.)
- Any `qualified_pass` results
- Any `fragile` workaround classifications
- Any `Low` confidence grades
- Supply chain findings near the C+/B- gate threshold

### 6. Methodology Notes

- Scale cap applied and reason
- Tests skipped and reason
- Solver versions used
- Tool version evaluated
- Devcontainer environment hash (if available)
