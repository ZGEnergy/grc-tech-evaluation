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

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | — | — | 0.3s | 15 |

When tabulating fails, distinguish independent failures from cascaded ones using the
`blocked_by` frontmatter field: "X independent fails + Y blocked."

#### Grade Rationale
2-3 sentences explaining the grade against rubric standards. Must reference specific
rubric language (e.g., "Meets the B+ standard: 'Mostly strong, one meaningful gap
with stable workaround'").

### 3b. FNM Ingestion Findings (Suite G)

If `fnm_ingestion/` results exist, include a dedicated section:

- **Data Model Fidelity:** G-FNM-1 record counts + G-FNM-2 field coverage by criticality tier.
  State whether 100% DCPF-critical coverage was achieved. Map to Expressiveness grade.
- **Power Flow Verification:** G-FNM-3 (DCPF) and G-FNM-4 (ACPF) aggregate metrics and
  outlier breakdown. Attribute failures to Expressiveness or Scalability.
- **Supplemental Data Representability:** G-FNM-5 N/E/X summary and discrepancies from
  analytical predictions. Map to Extensibility grade.

If Suite G was skipped (FNM_PATH not set), state: "Suite G skipped — FNM_PATH not set.
Grades based on synthetic network evidence (Suites A-F) only."

FNM findings are **additive evidence** — they strengthen or weaken grades from Suites A-F
but do not independently determine them. A/B/C boundaries are unchanged.

### 4. Cross-Cutting Observations

Synthesize observation files into thematic sections:
- **API Friction Patterns** — from `api-friction` tags
- **Documentation Gaps** — from `doc-gaps` tags
- **Solver Ecosystem** — from `solver-issues` tags
- **Architecture Quality** — from `arch-quality` tags
- **FNM Data Model** — from `fnm-data-model` tags (if any)

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
- FNM status: "Suite G executed (FNM_PATH set)" or "Suite G skipped (FNM_PATH not set)"
- Tests skipped and reason
- Solver versions used
- Tool version evaluated
- Protocol version(s) used (v5 for Suites A-F, v6 for Suite G — mixed-version is expected)
- Devcontainer environment hash (if available)
