---
test_id: F-1
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-1: Core License

## Criteria

Identify the license of the core library and assess compatibility with government and
enterprise deployment.

## Result: QUALIFIED PASS

GridCal (VeraGridEngine) is licensed under **MPL-2.0** as of v5.2.0 (November 2024). Prior
versions used LGPL-3.0. The license change was made in commit history and reflected in
`LICENSE.txt` and `pyproject.toml`.

### Evidence

- `LICENSE.txt` in repository root: Mozilla Public License Version 2.0
- `pyproject.toml` classifier: `License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)`
- PyPI package `veragridengine` metadata confirms MPL-2.0
- LGPL-to-MPL transition occurred at v5.2.0 (November 2024)

### Analysis

MPL-2.0 is a file-level copyleft license. It permits combining MPL-licensed files with
proprietary code in a "Larger Work" without the proprietary portions being subject to
copyleft, provided modifications to MPL-licensed files themselves remain open. This is
materially more permissive than LGPL for integration purposes.

MPL-2.0 is generally government-friendly and appears on approved lists for many agencies.
However, the recent license change (less than 18 months old) means some procurement
processes may still reference the old LGPL classification.

### Qualification Reason

Qualified rather than full pass because:
1. The license changed recently; legal review should confirm the transition is clean
2. One transitive dependency (chardet) is LGPL-licensed, which may require separate review
3. MPL file-level copyleft still requires tracking which files are modified
