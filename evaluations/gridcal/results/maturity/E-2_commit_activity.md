---
test_id: E-2
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# E-2: Commit Activity

## Criteria

Evaluate commit volume, frequency, and substantiveness over the past 12 months.

## Result: PASS

GridCal shows very high commit activity with ~2,434 commits in the past 12 months,
predominantly substantive changes.

### Evidence

- **Total commits (12 months)**: ~2,434
- **Average**: ~200 commits per month, ~6-7 per day
- **Commit types**: Predominantly feature additions, bug fixes, and refactoring.
  Low ratio of trivial commits (typo fixes, whitespace changes).
- **Active months**: Every month in the 12-month window shows significant activity
  with no dormant periods.

### Commit Quality

Commits are generally substantive, covering:
- New analysis capabilities (SCOPF improvements, contingency analysis)
- Numerical solver enhancements
- CIM/CGMES import/export improvements
- GUI enhancements
- Bug fixes for reported issues

### Caveat

The overwhelming majority of commits come from a single developer (SanPen / Santiago
Penate Vera). While this demonstrates dedication, it is assessed separately under
E-4 (Bus Factor). For the purpose of commit activity alone, the volume and substance
clearly pass.
