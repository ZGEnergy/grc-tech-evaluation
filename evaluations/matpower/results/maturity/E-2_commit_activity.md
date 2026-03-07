---
test_id: E-2
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-2: Commit Activity (Last 12 Months)

## Data Source

GitHub Commits API: `gh api repos/MATPOWER/matpower/commits --paginate`
Period: March 2025 - March 2026

## Summary

| Metric | Value |
|--------|-------|
| Total commits (2025-2026) | ~129 |
| Unique committers | 4 |
| Most recent commit | 2026-02-17 (Ray Zimmerman) |

## Committer Breakdown

| Author | Activity |
|--------|----------|
| Ray Zimmerman | ~120 commits (93%) — core development, bug fixes, new features |
| Wilson Gonzalez Vanegas | ~6 commits — three-phase extensions, buslink elements |
| Muhammad Yasirroni | ~2 commits — uninstall fix, cpf_example path |
| roruiz | ~1 commit — external contribution |

## Activity Pattern

- **Heavy burst around v8.1 release (July 2025):** ~50 commits in July 2025 alone,
  concentrated in the first two weeks before the 8.1 release.
- **Steady post-release activity (Aug-Dec 2025):** ~30 commits for bug fixes,
  test updates, and incremental improvements.
- **Continued development (Jan-Feb 2026):** ~10 commits including test fixes,
  issue triage, and PR merges.

## Substantive vs Maintenance

| Category | Approx % | Examples |
|----------|----------|---------|
| Feature development | 40% | MP-Core framework, three-phase extensions, HiGHS solver |
| Bug fixes | 25% | DC OPF test fix for R2025b, loadxgendata path handling |
| Test/CI updates | 20% | Test matrix updates, solver availability checks |
| Documentation | 10% | Pretty-printing, release notes |
| Merge/admin | 5% | PR merges, issue cleanup |

## Assessment

The project is actively developed with consistent commits. However, the activity
is almost entirely from a single developer (Ray Zimmerman, 93%). The project
shows no signs of abandonment but is heavily dependent on one person's continued
involvement.
