---
test_id: E-3
tool: pandapower
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 7c6517db
status: informational
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
timestamp: "2026-03-24T00:00:00Z"
---

# E-3: Contributor Concentration

## Result: INFORMATIONAL

## Finding

Bus factor of 3. Top 3 lifetime contributors hold 50.1% of commits. Reviewer concentration
is notable: top reviewer (heckstrahler) at 43.8% of reviewed PRs, and all reviews are
performed by 3 individuals (heckstrahler, vogt31337, KS-HTK). No single reviewer exceeds
the 60% threshold.

## Evidence

### Method

Two analyses:
1. **Commit concentration:** Lifetime contributor statistics from GitHub contributor API.
2. **Reviewer concentration:** Last 50 merged PRs, reviews fetched via `gh api repos/e2nIEE/pandapower/pulls/{n}/reviews`, bots excluded.

Data collected 2026-03-24.

### Part 1: Commit Concentration (Lifetime)

| Contributor | Commits | % of Total |
|-------------|---------|-----------|
| rbolgaryn | 1,808 | 23.5% |
| lthurner | 1,533 | 19.9% |
| vogt31337 | 519 | 6.7% |
| KS-HTK | 407 | 5.3% |
| wangzhenassd | 357 | 4.6% |
| pawellytaev | 239 | 3.1% |
| dlohmeier | 193 | 2.5% |
| hilbrich | 187 | 2.4% |
| shankhoghosh | 184 | 2.4% |
| ZhengLiu1119 | 179 | 2.3% |

- **Total lifetime contributors:** 136
- **Total commits (all contributors):** 7,696
- **Top 1 contributor (rbolgaryn):** 23.5%
- **Top 3 contributors (rbolgaryn + lthurner + vogt31337):** 50.1%
- **Bus factor:** 3

### Part 2: Reviewer Concentration (Last 50 Merged PRs)

Of 50 sampled merged PRs (numbers 2844-2928), 48 had at least one human review (96%).

| Reviewer | PRs Reviewed | % of Reviewed PRs |
|----------|-------------|-------------------|
| heckstrahler | 21 | 43.8% |
| vogt31337 | 16 | 33.3% |
| KS-HTK | 11 | 22.9% |
| mrifraunhofer | 4 | 8.3% |
| furqan463 | 3 | 6.2% |
| lthurner | 1 | 2.1% |
| marcopau | 1 | 2.1% |
| MMatthiessen | 1 | 2.1% |
| hilbrich | 1 | 2.1% |

- **Total unique reviewers:** 9
- **Top reviewer (heckstrahler):** 43.8% — below 60% threshold
- **Top 3 reviewers cover:** effectively 100% of reviewed PRs
- **PRs without any review:** 2 of 50 (4%)

### Reviewer Concentration Assessment

The top reviewer (heckstrahler) is at 43.8%, below the 60% single-reviewer concentration
flag threshold. However, the top 3 reviewers (heckstrahler, vogt31337, KS-HTK) perform
all reviews. If these three individuals were simultaneously unavailable, no code review
would occur. This is a moderate concentration risk.

Notable shift from lifetime commit data: the top two lifetime committers (rbolgaryn,
lthurner) are not among the top current reviewers, suggesting a generational transition
in project leadership.

### Cross-Reference with Observations

- The undocumented PYPOWER userfcn mechanism (see [doc-gaps observation](../observations/doc-gaps-extensibility-B-1_custom_constraints.md)) is an example of institutional knowledge concentrated in original developers that would be hard for new contributors to discover.
- The clean 6-layer architecture (see [arch-quality observation](../observations/arch-quality-extensibility-B-6_code_architecture.md)) mitigates bus-factor risk through code readability.

## Implications

Moderate concentration risk. Bus factor of 3 is adequate for an academic project. The
reviewer pool of 3 active individuals is the primary concentration concern — all code
quality gates depend on a small group. The 136 lifetime contributors and 45 active in the
last year indicate a broad but loosely engaged contributor base with a concentrated core
team. The apparent leadership transition from rbolgaryn/lthurner to vogt31337/heckstrahler/KS-HTK
is worth monitoring for continuity.
