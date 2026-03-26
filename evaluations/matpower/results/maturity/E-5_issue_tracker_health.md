---
test_id: E-5
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "1cc758ab"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-5: Issue Tracker Health

## Result: INFORMATIONAL

## Finding

MATPOWER's issue tracker shows a batched response pattern: many issues are acknowledged and resolved in periodic triage sessions rather than continuously. Median time-to-close is 37 days, but this masks a bimodal distribution -- some issues are closed within hours (genuine bugs with quick fixes) while others wait months until a batch triage. Response quality is high when responses occur.

## Evidence

### Closed issues sample (last 20)

Via `gh issue list --repo MATPOWER/matpower --state closed --limit 20`, accessed 2026-03-14:

| # | Title (abbreviated) | Created | Closed | Days |
|---|---------------------|---------|--------|------|
| 258 | Slack bus no generator | 2025-02-11 | 2025-02-11 | 0.1 |
| 251 | PTDF full zero rows | 2024-11-12 | 2024-11-13 | 0.2 |
| 257 | Debug dm_converter_class | 2025-02-10 | 2025-02-10 | 0.5 |
| 249 | runopf violates PMAX | 2024-10-18 | 2024-10-19 | 0.7 |
| 274 | DC OPF test failure linprog | 2025-09-25 | 2025-09-26 | 0.8 |
| 255 | OPF voltage vs PF mismatch | 2025-01-22 | 2025-01-30 | 8.0 |
| 256 | opf.use_vg PQ bus issue | 2025-02-08 | 2025-02-18 | 9.7 |
| 270 | test_matpower optimstatus | 2025-08-05 | 2025-08-15 | 10.8 |
| 280 | Kundur system convergence | 2025-12-18 | 2026-01-05 | 17.8 |
| 282 | loadxgendata abs paths | 2026-01-15 | 2026-02-16 | 32.0 |
| 281 | Kundur convergence (dup) | 2026-01-05 | 2026-02-16 | 42.3 |
| 260 | Bij accuracy suggestion | 2025-02-14 | 2025-05-07 | 82.0 |
| 278 | EV bus >533 error | 2025-11-25 | 2026-02-16 | 83.6 |
| 276 | Jacobian computation Q | 2025-10-28 | 2026-02-16 | 111.2 |
| 254 | IEEE 34 convergence | 2025-01-11 | 2025-05-31 | 140.0 |
| 273 | t_qcqps_masters test | 2025-09-25 | 2026-02-16 | 144.8 |
| 253 | Dual variable sign | 2024-12-06 | 2025-05-07 | 151.8 |
| 252 | DCOPF vs GAMS diff | 2024-11-22 | 2025-05-07 | 166.5 |
| 271 | Uninstall examples | 2025-08-15 | 2026-02-16 | 185.5 |
| 250 | Relax branch only | 2024-10-31 | 2025-05-07 | 187.9 |

**Median time-to-close:** 37.2 days
**Mean time-to-close:** 68.8 days
**Min:** 0.1 days (2.4 hours), **Max:** 187.9 days (6.3 months)

**Batch triage pattern:** Multiple issues were closed on 2026-02-16 (issues #271, #273, #276, #278, #281, #282) and on 2025-05-07 (issues #250, #252, #253, #260). This indicates periodic triage sessions rather than continuous issue management.

### Open issues sample (oldest 10 open)

Via `gh issue list --repo MATPOWER/matpower --state open --limit 10`, accessed 2026-03-14:

| # | Title (abbreviated) | Created | Age (days) |
|---|---------------------|---------|------------|
| 104 | Extend zonal reserves | 2020-06-16 | ~2,098 |
| 127 | makePTDF ext2int error | 2021-09-24 | ~1,633 |
| 136 | Distributed slack PF | 2022-01-07 | ~1,528 |
| 178 | Overloaded branches alert | 2023-04-25 | ~1,055 |
| 233 | Multiple/distributed slacks | 2024-05-30 | ~654 |
| 246 | AC sensitivity analysis | 2024-09-11 | ~550 |
| 262 | Bus hop distance | 2025-03-12 | ~367 |
| 263 | Schema | 2025-04-27 | ~322 |
| 269 | Update to mp.opt_model | 2025-06-16 | ~272 |
| 279 | CPF adaptive stepping stuck | 2025-12-01 | ~104 |

**Total open issues:** 16 (per repo stats)
**Oldest open issue:** #104 (June 2020, ~5.7 years)

Several open issues are feature requests or questions rather than bugs (e.g., #233 "distributed slacks", #262 "bus hop distance"). True bugs like #279 (CPF stuck in loop) remain open at 104 days.

### Response quality

When the maintainer responds, answers are typically substantive and technically detailed. Issue #256 received a code fix with PR #261. Issue #274 received a same-day fix. However, many issues (especially user questions or non-critical bugs) receive no comment and are batch-closed months later, sometimes without explanation.

**Acknowledged ratio:** Approximately 50% of sampled closed issues received an explicit comment or linked PR before closure. The remainder were closed in batch triage, sometimes without visible resolution narrative.

## Implications

The batched response pattern is consistent with a single-maintainer project where the maintainer allocates periodic blocks of time to community management. For production use, this means bug reports may not receive timely acknowledgment, but genuine bugs with test failures tend to be fixed quickly (same-day for #274, #258). Feature requests and user questions have much longer response times. The 16 total open issues is a manageable backlog, indicating the maintainer does eventually address most reports.
