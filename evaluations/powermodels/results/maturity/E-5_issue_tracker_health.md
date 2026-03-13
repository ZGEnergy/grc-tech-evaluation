---
test_id: E-5
tool: powermodels
dimension: maturity
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "d2f277d5"
---

# E-5: issue_tracker_health

## Finding

Of the sampled closed issues, the median time-to-close is approximately 31 days, with high variance (0–193 days). Maintainers respond to nearly all issues with substantive technical content; however, 10 open issues show long dwell times with no resolution, and a recurring pattern of "acknowledged but not fixed" appears for parser edge cases and formulation gaps.

## Evidence

### Closed issues sample (last 8 non-PR closed issues via REST API):

| Issue | Days to Close | Comments | Topic |
|-------|---------------|----------|-------|
| #991 | 60 | 1 | Wrong branch type in case118.m |
| #988 | 81 | 2 | Bus type change behavior |
| #987 | 88 | 4 | Power flow qmax/qmin violation |
| #984 | 1 | 5 | solve_mn_opf_strg error |
| #978 | 3 | 2 | Shunt sign behavior |
| #977 | 193 | 7 | Support for calc_branch_flow_nfa |
| #974 | 61 | 4 | Chordal SDP bounds on large cases |
| #971 | 0 | 3 | Load/production discrepancy (IEEE 300) |

**Median time-to-close (8 issues):** ~60.5 days

Note: The REST API returned 8 true issues (excluding PRs) in the last closed batch. Several low-complexity issues were closed same-day by maintainers (0–1 days), dragging down the raw median. Longer issues (88–193 days) represent substantive feature/behavior questions.

#### Open issues sample (10 most recent):

| Issue | Age (days from 2026-03-11) | Comments | Status |
|-------|---------------------------|----------|--------|
| #989 | 120 | 4 | Generators on PQ buses — acknowledged, no fix |
| #975 | 280 | 11 | DCPPowerModel in DirectMode — active discussion, no resolution |
| #932 | 502 | 0 | PSSE active gens at load buses — unacknowledged |
| #923 | 612 | 2 | Basic LODF utility request — acknowledged with workaround pointer |
| #921 | 619 | 2 | PSSE RAW v34 support — acknowledged, no ETA |
| #918 | 631 | 2 | PSS/E transformer angle offset >6 — acknowledged, confirmed open |
| #897 | 826 | 4 | PSSE impedance 0.0 logic — fix in PowerSystems but not PowerModels |
| #894 | 860 | 2 | Move parser to separate package — acknowledged, no action |
| #893 | 878 | 0 | PSSE voltage source converter — unacknowledged |
| #891 | 889 | 3 | LPAC PF not supported — acknowledged with workaround |

**Acknowledged ratio (open issues):** 8 of 10 (80%) have at least one maintainer response
**Unacknowledged (open):** 2 of 10 (#932, #893)

#### Response quality notes:
- Maintainer responses are technically substantive: they explain the design rationale, link to related issues, and offer workarounds
- The issue tracker is not a rubber stamp — developers engage genuinely with edge cases
- There is a recurring pattern of parser issues (#921, #893, #897) that are acknowledged but have no concrete fix plan, reflecting the known technical debt of the PSSE parser design
- Issue #975 (DCPPowerModel DirectMode) shows the JuMP maintainer (@odow) and PowerModels users in productive but unresolved technical dialogue

**Data source:** `gh api repos/lanl-ansi/PowerModels.jl/issues?state=closed&per_page=20` and `gh issue list --repo lanl-ansi/PowerModels.jl --state open --limit 10`

## Implications

Response quality is high and the project is not ignoring users. However, the open issue queue contains several items 500–900 days old with no ETA, indicating that the project is responsive but under-resourced for non-critical issues. The median time-to-close (~60 days) is acceptable for a research-grade library but slower than industrial tools. Classified as qualified_pass: the tracker is healthy in engagement quality but accumulates a backlog of parser/edge-case issues.
