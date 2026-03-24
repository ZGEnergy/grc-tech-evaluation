# Phase 1 Tool Selection Report
## Contract FA714626C0006 | Grid Research Company LLC

**Date:** {{date}}

---

## Methodology

<3 sentences: lexicographic ranking, priority order, gate criterion. Reproducible.>

## Grade Comparison

| Rank | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|------|---------------|---------------|-------------|---------------|----------|--------------|
| 1    | ...  | ...           | ...           | ...         | ...           | ...      | ...          |
| ...  | ...  | ...           | ...           | ...         | ...           | ...      | ...          |

<Per-tool footnotes for caveats (e.g., MATPOWER: customer requires inspectable source code)>

## Sensitivity Analysis

<1-3 alternative scenarios with results table. Which scenarios change the pick, which don't.>
<Emphasize ranking stability: tools that hold position across all scenarios.>
<Flag tools that top one scenario but can't meet Phase 2 requirements.>
<Note: scenarios proposed by evaluator, confirmed by GRC principal.>

---

## Recommendation

### Selected Tool: {{tool_name}}

<1 paragraph: why this tool won. Reference the 2-3 criteria that drove the ranking.>

### Head-to-Head: Critical Phase 2 Capabilities

| Capability | {{winner}} | {{runner_up}} | {{others...}} |
|------------|-----------|--------------|---------------|
| SCOPF | ... | ... | ... |
| Distributed Slack | ... | ... | ... |
| PWL Cost Curves | ... | ... | ... |
| PSS/E RAW Parsing | ... | ... | ... |
| Custom Constraints | ... | ... | ... |
| UC/ED Pipeline | ... | ... | ... |

### Runner-Up: {{runner_up_name}}

<1 paragraph: why not chosen, under what circumstances reconsidered.>

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| ... | HIGH/MED/LOW | ... |

---

## Phase 2 Development Scope

### Tool-Intrinsic Gaps

| Gap | Effort | Notes |
|-----|--------|-------|
| ... | days/weeks/months | ... |

### Tool-Adjacent Engineering

| Work Item | Effort | Notes |
|-----------|--------|-------|
| ... | ... | ... |

### Operational Workflow

| Work Item | Effort | Notes |
|-----------|--------|-------|
| ... | ... | ... |

---

## Provenance

- **Synthesis files:** <list with git SHAs>
- **Generated:** {{timestamp}}
- **Ranking algorithm:** Lexicographic on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with Supply Chain gate (<=C+ disqualifies)

<!-- CONTENT RULE: Never name specific ISOs, RTOs, utilities, or real grid regions.
     Use generic terms: "the target ISO", "the customer's network", "the full network
     model (FNM)". -->
<!-- CONTENT RULE: No em-dashes. Use commas, semicolons, hyphens, or parentheses. -->
<!-- CONTENT RULE: No protocol version numbers, sweep findings, or probe results. -->
