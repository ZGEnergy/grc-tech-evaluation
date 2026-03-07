---
test_id: E-6
tool: gridcal
dimension: maturity
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# E-6: Issue Responsiveness

## Criteria

Assess how quickly and thoroughly the maintainers respond to bug reports and feature
requests on the issue tracker.

## Result: QUALIFIED PASS

The maintainer (SanPen) is responsive to most issues but triage patterns are uneven.

### Evidence

- **Open issues**: 29 at time of evaluation
- **Response pattern**: SanPen personally responds to the majority of filed issues,
  often within days
- **Resolution quality**: Bug reports with reproducible cases tend to get fixed quickly.
  Feature requests and architectural issues may remain open indefinitely.

### Notable Open Issues

| Issue | Topic | Status |
|-------|-------|--------|
| #397 | OPF constraints not working correctly | Open, acknowledged |
| #430 | ACOPF crash on certain networks | Open |
| #364 | SCOPF roadmap / feature request | Open, long-standing |

### Patterns

- **Batch-close behavior**: Some issues are closed in batches, suggesting periodic
  triage rather than continuous attention
- **Single responder**: Nearly all issue responses come from SanPen. No other
  maintainer regularly triages or responds.
- **No SLA or formal triage**: No labels, milestones, or priority classification
  system visible on the tracker

### Qualification Reason

Response times are generally acceptable and the maintainer is engaged, but the
single-responder pattern and periodic batch-close behavior mean response quality is
inconsistent. Critical bugs (like #430, ACOPF crash) remaining open without clear
timeline is a concern for production users.
