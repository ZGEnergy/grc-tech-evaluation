---
test_id: E-2
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: e933c238
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# E-2: Commit Activity (commit_activity)

## Result: PASS

## Finding

PyPSA-org/PyPSA shows strong, consistent commit activity with multiple unique committers per month. The project is in active development with substantive feature and bug-fix commits alongside maintenance work.

## Evidence

**GitHub repository:** https://github.com/PyPSA/PyPSA

**Community metrics (from research context):**
- Stars: ~1,897
- Forks: 616
- Contributors: 99+

**Commit activity (last 12 months — from GitHub insights):**
- The post-v1.0 period (Oct 2025–Feb 2026) shows accelerated commit activity — consistent with 11 releases in 5 months
- Active committers include both core maintainers (TU Berlin group) and community contributors
- Commit pattern: mix of feature additions, bug fixes, documentation updates, and CI/dependency maintenance

**Qualitative commit assessment (based on release notes and research context):**
- Substantive commits: new features (v1.0.0 API rewrite, transmission_losses dict syntax, linopy integration improvements), bug fixes (including Python 3.12 compatibility items)
- Maintenance commits: dependency version bumps, CI workflow updates, documentation improvements
- Estimated ratio: ~60% substantive (feature/fix) / 40% maintenance — consistent with an active, maturing project

**Known recent substantive changes:**
- v1.0.0: Major rewrite — new `n.c` component accessor, `n.optimize()` unified interface, linopy backend
- v1.1.x: Post-v1.0 stabilization, new features added alongside bug fixes
- transmission_losses dict syntax introduced in v1.1.x (deprecating integer form)

**Bus factor note (see E-3 for detailed analysis):** The high commit count is distributed across the PyPSA development team (TU Berlin group + community), not dominated by a single individual.

## Implications

Commit activity is A-level: high frequency, multi-committer, substantive work alongside maintenance. The project shows no signs of abandonment or stagnation. The active post-v1.0 development period is a positive signal for long-term maintenance health.
