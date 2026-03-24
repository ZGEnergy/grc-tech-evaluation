# Report Site Structure

The report is a Docusaurus site at `report/`. This document describes every page and
data file that report-builder manages.

## Directory Layout

```
report/
├── docs/
│   ├── index.mdx                      # Selection report homepage
│   ├── grid-primer.mdx                # Background: power systems primer
│   ├── use-cases-criteria.mdx         # Criteria descriptions and use cases
│   ├── tools-evaluated.mdx            # Per-tool profiles and summaries
│   ├── contract-traceability.mdx      # SOW requirement mapping
│   └── results/
│       ├── index.mdx                  # Results overview: grade table, ranking, sensitivity
│       ├── expressiveness.mdx         # Per-criterion detail
│       ├── extensibility.mdx
│       ├── scalability.mdx
│       ├── accessibility.mdx
│       ├── maturity.mdx
│       ├── supply-chain.mdx
│       └── head-to-head.mdx           # Phase 2 capability comparison
├── data/
│   ├── grades.json                    # Grade table with numeric scale
│   ├── sensitivity.json               # Scenario definitions and rankings
│   ├── risk-register.json             # Risks with severity and mitigation
│   ├── head-to-head.json              # Phase 2 capabilities per tool
│   ├── tool-profiles.json             # Per-tool strengths/weaknesses/workarounds
│   └── test-results.json              # Detailed test results (generated separately)
├── static/img/                        # Generated SVG charts
├── scripts/
│   ├── generate_charts.py             # Chart generation pipeline
│   ├── validate_content.py            # Post-build content validation
│   ├── validate_charts.py             # Chart validation
│   └── ...                            # Other validation scripts
├── sidebars.js                        # Sidebar navigation config
├── docusaurus.config.js               # Site configuration
└── selection-report-v{N}.md           # Standalone selection report markdown
```

## Pages to Generate

### Group A: Data-Driven Pages (rebuild every run)

These pages are generated from evaluation data and must be rebuilt from scratch.

#### `docs/index.mdx` — Selection Report Homepage
- **sidebar_position:** 1
- **Content:** Executive summary, recommendation, why-selected-tool, runner-up,
  risk register (collapsible), Phase 2 development scope (collapsible), link to
  results overview
- **Data sources:** grades.json, risk-register.json, ranking results, sensitivity
  results, per-tool details

#### `docs/tools-evaluated.mdx` — Tool Profiles
- **sidebar_position:** 4
- **Content:** For each tool: description, grade profile, strengths/weaknesses,
  notable workarounds, Phase 2 viability. MATPOWER section marked as reference-only.
- **Data sources:** grades.json, tool-profiles.json, synthesis files

#### `docs/results/index.mdx` — Results Overview
- **sidebar_position:** 1
- **Content:** Grade comparison table, ranking methodology, sensitivity analysis
  with narrative, links to per-criterion pages
- **Data sources:** grades.json, sensitivity.json, ranking results

#### `docs/results/{criterion}.mdx` — Per-Criterion Detail Pages
- **sidebar_position:** 2-7 (expressiveness=2, extensibility=3, scalability=4,
  accessibility=5, maturity=6, supply-chain=7)
- **Content:** What the criterion measures, cross-tool comparison, per-tool analysis
  with test ID references, workarounds, summary
- **Data sources:** grades.json, per-tool synthesis files, test result files

#### `docs/results/head-to-head.mdx` — Phase 2 Capabilities
- **sidebar_position:** 8
- **Content:** Capability comparison table (selected tool vs runner-up vs others),
  capability detail sections
- **Data sources:** head-to-head.json, synthesis files

### Group B: Reference Pages (update only if needed)

#### `docs/grid-primer.mdx` — Power Systems Background
- **sidebar_position:** 2
- **Content:** Educational primer on power system modeling concepts
- Generally stable; only update if evaluation revealed new context

#### `docs/use-cases-criteria.mdx` — Criteria Descriptions
- **sidebar_position:** 3
- **Content:** What each criterion measures, why it matters, how it was tested
- Update if rubric changed; otherwise stable

#### `docs/contract-traceability.mdx` — SOW Mapping
- **sidebar_position:** 5
- **Content:** Maps SOW requirements to report sections. Update MATPOWER exclusion
  rationale if needed (must say customer requires inspectable source code).
- Update to reflect current report structure

### Group C: Pages to Remove

These are internal process artifacts that must not appear in the customer report:

- `docs/results/sweep-findings.mdx` — DELETE
- `docs/results/probe-results.mdx` — DELETE

Also remove their entries from `sidebars.js`.

## Data Files

### `data/grades.json`
```json
{
    "_provenance": { "source": "...", "extracted": "YYYY-MM-DD" },
    "scale": { "A+": 4.3, "A": 4.0, ... "F": 0.0 },
    "tools": ["pypsa", "pandapower", ...],
    "criteria": ["expressiveness", "extensibility", ...],
    "grades": [
        { "tool": "pypsa", "criterion": "expressiveness", "letter": "B+", "numeric": 3.3 },
        ...
    ]
}
```

### `data/sensitivity.json`
```json
{
    "scenarios": [
        {
            "id": 1,
            "name": "Scenario name",
            "description": "What changed",
            "rankings": [
                { "rank": 1, "tool": "pypsa", "notes": "..." },
                ...
            ],
            "top_changed": false
        },
        ...
    ]
}
```

### `data/risk-register.json`
```json
{
    "risks": [
        {
            "id": "R1",
            "title": "Short title",
            "description": "Detailed description",
            "severity": "HIGH",
            "mitigation": "Concrete mitigation strategy"
        },
        ...
    ]
}
```

### `data/head-to-head.json`
```json
{
    "capabilities": [
        {
            "name": "SCOPF",
            "tools": {
                "pypsa": { "status": "Native", "notes": "..." },
                "powermodels": { "status": "Extension", "notes": "..." },
                ...
            }
        },
        ...
    ]
}
```

### `data/tool-profiles.json`
```json
{
    "tools": [
        {
            "name": "pypsa",
            "display_name": "PyPSA",
            "strengths": ["...", "..."],
            "weaknesses": ["...", "..."],
            "workarounds": [
                { "test_id": "...", "description": "...", "durability": "stable" }
            ]
        },
        ...
    ]
}
```

### Files to Remove
- `data/sweep-themes.json` — Internal artifact. DELETE.
- `data/probe-results.json` — Internal artifact. DELETE.

## Sidebar Configuration

After removing sweep-findings and probe-results, `sidebars.js` should be:

```js
const sidebars = {
  reportSidebar: [
    'index',
    'grid-primer',
    'use-cases-criteria',
    'tools-evaluated',
    'contract-traceability',
    {
      type: 'category',
      label: 'Evaluation Results',
      collapsed: false,
      items: [
        'results/index',
        'results/expressiveness',
        'results/extensibility',
        'results/scalability',
        'results/accessibility',
        'results/maturity',
        'results/supply-chain',
        'results/head-to-head',
      ],
    },
  ],
};

module.exports = sidebars;
```

## Chart Generation

Charts are generated by `scripts/generate_charts.py` from JSON data files:
- `heatmap_grades.svg` — Grade comparison heatmap
- `radar_overlay.svg` — Grade radar overlay for all tools
- Scalability timing plots
- Test result matrix
- Bar charts for various comparisons

Run inside devcontainer: `.devcontainer/dc-exec -C /workspace/report python scripts/generate_charts.py`
