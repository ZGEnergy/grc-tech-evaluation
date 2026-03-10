# Criterion Sub-Page Template

> **This file is a reference template, not a rendered page.**
> The underscore prefix (`_`) excludes it from Docusaurus routing.
> Copy the MDX pattern below when creating a new criterion page.

---

## Annotated Template

```mdx
---
sidebar_position: <N>          {/* Position within results/ sidebar group */}
title: "<Criterion Name>"      {/* Displayed in sidebar and browser tab */}
---

import Placeholder from '@site/src/components/Placeholder';

# <Criterion Name>

## Overview

{/* 1-2 paragraphs explaining:
    - What this criterion measures
    - Which test suites (e.g. A-1 through A-11) map to it
    - Its priority weight in the rubric (highest / high / moderate / low)
    - Any cross-criterion dependencies or interactions */}

{/* Chart embed slot — replace Placeholder with a real chart component when ready */}
<Placeholder title="<Criterion Name> Grade Comparison" />

## Tool Results

{/* Tools appear in rank order: best-performing first, MATPOWER last (reference).
    The top-ranked tool uses `open` so its card is expanded by default.
    All others are collapsed. */}

{/* ── Tool Card (ranked candidate) ────────────────────────────────── */}
<details className="eval-details" open>
<summary>

### <Tool Name> — <span className="grade-<x>"><Grade></span> (#<rank>)

</summary>

{/* 1-2 paragraphs of narrative rationale:
    - Key strengths that earned the grade
    - Specific weaknesses or gaps
    - Any probe findings that adjusted the grade
    - Comparison context vs. other tools if useful */}

| Test ID | TINY | SMALL | MEDIUM | Notes |
|---------|------|-------|--------|-------|
| A-1     | pass | pass  | pass   | Short note on behavior |
| A-2     | pass | pass  | q_pass | probe-NNN: brief explanation |
| A-3     | fail | —     | —      | Reason for failure |

{/* Result values:
    - pass      — test passes acceptance criteria
    - fail      — test fails acceptance criteria
    - q_pass    — qualified pass (passes with caveats, see Notes)
    - skip      — test not applicable or tool lacks capability
    - —         — test not run at this scale */}

**Related Probes:** [probe-NNN](./probe-results#probe-NNN)

{/* Optional: link to themes from sweep-findings */}
**Related Themes:** [theme-name](./sweep-findings#theme-name)

</details>

{/* ── Repeat for each ranked candidate tool ───────────────────────── */}
{/* Order: PyPSA (#1), PowerModels (#2), pandapower (#3),
          GridCal (#4), PowerSimulations (#5) */}

{/* ── Reduced-confidence footnote (GridCal, PowerSimulations) ─────── */}
{/* For tools where primary synthesis was not conducted, add this
    admonition inside the <details> block, immediately after <summary>: */}

> **Note:** <Tool> grades were reconstructed from sweep findings and
> secondary test evidence. Primary synthesis was not conducted for this tool.

{/* ── MATPOWER reference card (always last) ────────────────────────── */}
<details className="eval-details">
<summary>

### MATPOWER — <span className="grade-<x>"><Grade></span> (Reference Only)

</summary>

:::note[Reference Implementation]
MATPOWER served as the reference implementation for validating test protocols
and network data. It is not a candidate for Phase 2 selection. Grades reflect
protocol validation performance only.
:::

{/* Brief narrative about MATPOWER's reference-role performance */}

| Test ID | TINY | SMALL | MEDIUM | Notes |
|---------|------|-------|--------|-------|
| ...     | ...  | ...   | ...    | ...   |

</details>

{/* ── Navigation footer ───────────────────────────────────────────── */}
---

**Previous:** [<Previous Page>](./<previous>) | **Next:** [<Next Page>](./<next>)
```

---

## CSS Classes Reference

Grade badge classes (defined in `src/css/evaluation.css`):

| Class | Grade |
|-------|-------|
| `grade-a` | A |
| `grade-a-minus` | A- |
| `grade-b-plus` | B+ |
| `grade-b` | B |
| `grade-b-minus` | B- |
| `grade-c-plus` | C+ |
| `grade-c` | C |
| `grade-d` | D |
| `grade-f` | F |

Detail card class: `eval-details` (provides border, padding, open/close styling).

## Evidence Table Conventions

- **Columns:** Test ID, TINY (5-bus), SMALL (IEEE 118-bus), MEDIUM (ACTIVSg10k), Notes
- **Result values:** `pass`, `fail`, `q_pass` (qualified pass), `skip` (not applicable), `—` (not run)
- **Notes column:** brief explanation; reference probe IDs for non-obvious results
- Rows should cover all test IDs relevant to the criterion, even if skipped

## Card Ordering

1. PyPSA (highest-ranked candidate)
2. PowerModels
3. pandapower
4. GridCal (reduced confidence)
5. PowerSimulations (reduced confidence)
6. MATPOWER (reference only — always last)
