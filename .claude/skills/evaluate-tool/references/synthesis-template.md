# Synthesis Report Template

The synthesis report compiles all evaluation results into per-criterion test result
summaries with traceability to evidence. It does NOT assign tiers — tier assignment
happens downstream in sweep-evaluations where cross-tool visibility enables calibrated tiering.

## File Location

```
evaluations/<tool>/results/synthesis.md
```

## Required Sections

### 1. Executive Summary

3-5 sentences covering:
- Overall tool characterization (strengths + positioning)
- Gate status (supply chain pass/fail based on evidence)
- Most notable strengths and weaknesses
- Scale cap applied (if any)

Do NOT include tier assignments. Describe capabilities and limitations factually.

### 2. Test Results Summary

| Criterion | Tests Passed | Tests Failed | Qualified Pass | Confidence | Key Evidence |
|-----------|-------------|-------------|----------------|------------|--------------|
| Problem Expressiveness | X/Y | Z/Y | W | High/Medium/Low | 1-line |
| Extensibility | ... | ... | ... | ... | ... |
| Scalability | ... | ... | ... | ... | ... |
| Workforce Accessibility | ... | ... | ... | ... | ... |
| Maturity & Sustainability | ... | ... | ... | ... | ... |
| Supply Chain (Gate) | ... | ... | ... | ... | ... |

**Confidence levels:**
- **High** — Clear, unambiguous evidence from multiple tests
- **Medium** — Evidence supports the conclusions but some judgment involved
- **Low** — Limited or ambiguous evidence; needs human spot-check

### 3. Per-Criterion Detail

For each criterion, include:

#### Strengths
Bulleted list, each item linked to a specific test ID:
- "Native DC OPF with LMP extraction ([A-3](expressiveness/A-3_dcopf.md))"

#### Weaknesses
Same format with test ID links. Each weakness must be tagged:
- `[tool-specific]` — inherent to the tool's architecture
- `[solver-specific]` — caused by the solver, likely shared across tools

Example:
- "SCUC times out at SMALL scale [solver-specific: HiGHS single-threaded MILP]
  ([C-4](scalability/C-4_scuc_SMALL.md))"
- "No API for custom constraint injection [tool-specific]
  ([B-1](extensibility/B-1_custom_constraints.md))"

#### Workarounds Required
List with durability class:
- "Custom constraint addition requires internal API ([B-1](extensibility/B-1_custom_constraints.md)) — **fragile**"

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | — | — | 0.3s | 15 |

When tabulating fails, distinguish independent failures from cascaded ones using the
`blocked_by` frontmatter field: "X independent fails + Y blocked."

#### Findings Summary
2-3 sentences summarizing what the evidence shows for this criterion. Identify blocking
limitations vs minor gaps. Tag key findings as solver-specific or tool-specific.

Do NOT recommend a tier. The purpose of this section is to present evidence
clearly so the downstream tiering process can assign calibrated tiers with cross-tool
context.

### 3b. FNM Ingestion Findings (Suite G)

If `fnm_ingestion/` results exist, include a dedicated section:

- **Data Model Fidelity:** G-FNM-1 record counts + G-FNM-2 field coverage by criticality tier.
  State whether 100% DCPF-critical coverage was achieved. Relate to Expressiveness.
- **Power Flow Verification:** G-FNM-3 (DCPF) and G-FNM-4 (ACPF) aggregate metrics and
  outlier breakdown. Attribute failures to Expressiveness or Scalability.
- **Supplemental Data Representability:** G-FNM-5 N/E/X summary and discrepancies from
  analytical predictions. Relate to Extensibility.

If Suite G was skipped (FNM_PATH not set), state: "Suite G skipped — FNM_PATH not set.
Findings based on synthetic network evidence (Suites A-F) only."

FNM findings are **additive evidence** — they strengthen or weaken conclusions from
Suites A-F but do not independently determine them.

### 4. Cross-Cutting Observations

Synthesize observation files into thematic sections:
- **API Friction Patterns** — from `api-friction` tags
- **Documentation Gaps** — from `doc-gaps` tags
- **Solver Ecosystem** — from `solver-issues` tags. Tag each finding as solver-specific
  or tool-specific.
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
- Any `Low` confidence findings
- Supply chain findings near the gate threshold
- Findings where solver-vs-tool attribution is ambiguous

### 6. Methodology Notes

- Scale cap applied and reason
- FNM status: "Suite G executed (FNM_PATH set)" or "Suite G skipped (FNM_PATH not set)"
- Tests skipped and reason
- Solver versions used
- Tool version evaluated
- Devcontainer environment hash (if available)
