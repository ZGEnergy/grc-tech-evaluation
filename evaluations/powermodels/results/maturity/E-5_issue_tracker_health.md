---
test_id: E-5
tool: powermodels
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: d2f277d5
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: QUALIFIED PASS

## Finding

The issue tracker shows substantive maintainer engagement with high response quality, but a significant backlog of unresolved issues. Of 20 sampled closed issues, median time-to-close is 28 days with 80% receiving a maintainer response. Of 10 sampled open issues, 6 have maintainer acknowledgment, but several are 500-900+ days old with no resolution path.

## Evidence

### Closed Issues Sample (20 most recently closed)

Data via `gh api repos/lanl-ansi/PowerModels.jl/issues?state=closed&per_page=20` (accessed 2026-03-24):

| Issue | Days to Close | Maintainer Response | Topic |
|-------|---------------|---------------------|-------|
| #971 | 0 | No (community only) | Load/production discrepancy IEEE 300 |
| #984 | 1 | Yes | solve_mn_opf_strg error |
| #925 | 1 | Yes | LPAC infeasibility PEGASE 89 |
| #924 | 1 | Yes | Switch issue |
| #978 | 3 | Yes | Shunt sign behavior |
| #926 | 3 | Yes | Storage variables in build_opf |
| #927 | 5 | Yes | Unconstrained reference bus in OPF |
| #929 | 10 | Yes | Gen count mismatch in result |
| #954 | 27 | No | resolve_switches connectivity |
| #913 | 27 | Yes | make_basic_network performance |
| #930 | 29 | Yes | Test PowerModel failed |
| #991 | 60 | Yes (@ccoffrin) | Wrong branch type in case118.m |
| #974 | 61 | Yes | Chordal SDP bounds on large cases |
| #988 | 81 | Yes (@ccoffrin) | Bus type change PQ->PV |
| #987 | 88 | Yes | PF qmax/qmin not respected |
| #938 | 89 | Yes | Integer values InexactError |
| #936 | 138 | No | Spelling fix (no discussion needed) |
| #977 | 193 | Yes | calc_branch_flow_nfa support |
| #953 | 199 | No | European network format offer |
| #935 | 429 | Yes | AC PF breaks with switches |

**Median time-to-close:** 28 days
**Min/Max:** 0 / 429 days
**Maintainer acknowledged (closed):** 16 of 20 (80%)
**Same-day or next-day closures:** 4 of 20 (quick triage for clear-cut issues)

### Open Issues Sample (10 most recent)

| Issue | Age (days) | Maintainer Response | Status |
|-------|-----------|---------------------|--------|
| #989 | 133 | No (community contributors only) | Generators on PQ buses -- active community discussion |
| #975 | 293 | Yes (@odow, @ccoffrin) | DCPPowerModel DirectMode -- 12 comments, nuanced technical debate |
| #932 | 515 | No | PSSE active gens at load buses -- 0 comments |
| #923 | 625 | Yes (@ccoffrin) | LODF utility request -- acknowledged, pointed to PowerNetworkMatrices.jl |
| #921 | 632 | No (community only) | PSSE RAW v34 support -- community discussion |
| #918 | 647 | Yes (@ccoffrin) | PSS/E transformer angle >60 -- confirmed open |
| #897 | 826 | Yes (@odow) | PSSE impedance 0.0 logic -- fix in PowerSystems.jl not in PowerModels |
| #894 | 874 | Yes (@ccoffrin) | Move parser to separate package -- acknowledged, no action |
| #893 | 890 | No | PSSE VSC data reading -- 0 comments |
| #891 | 901 | Yes (@ccoffrin) | LPAC PF not supported -- workaround provided |

**Acknowledged by maintainer (open):** 6 of 10 (60%)
**Unacknowledged (open):** 4 of 10 (#989, #932, #921, #893)
**Issues open >1 year:** 7 of 10

### Response Quality Assessment

Maintainer responses are technically substantive:
- @ccoffrin provides power-systems domain explanations (e.g., #991 explains branch/transformer classification by BaseKV; #891 offers OPF-as-PF workaround)
- @odow engages on JuMP/solver integration issues with deep technical nuance (e.g., #975 discusses MOI interval constraint bridging for Gurobi DirectMode)
- Workarounds are offered where fixes are not planned (#891, #923)
- Design rationale is explained when feature requests are declined

**Recurring patterns:**
- PSS/E parser issues (#921, #918, #897, #893) form a cluster of acknowledged-but-unfixed technical debt
- Community contributors (@jbarberia, @LKuhrmann) actively participate in discussions, partially compensating for limited maintainer bandwidth
- @ccoffrin re-engaged in Feb 2026 to close several long-standing issues (#991, #988) -- a positive signal after extended inactivity

## Implications

Response quality is high when maintainers engage -- issues receive substantive technical answers, not perfunctory acknowledgments. However, the open issue queue contains 7 items older than 1 year, including unacknowledged issues, indicating the project is responsive but under-resourced for non-critical maintenance. The 28-day median time-to-close is acceptable for a research-grade library. The qualification is the growing backlog of parser-related issues and the 4/10 unacknowledged open issues. Classified as qualified_pass: the tracker is healthy in engagement quality but accumulates backlog.
