# Test-ID Mapping Schema

The test-ID mapping table tracks how tests evolve across protocol versions. It lives
in the findings report and enables cross-version comparability of evaluation results.

## Schema

```yaml
mapping:
  - source_id: <test_id>           # vN test ID (e.g., "A-8")
    target_id: <test_id|null>      # vN+1 test ID, null if removed
    relationship: <relationship>   # see values below
    notes: <string|null>           # brief explanation of changes
```

## Relationship Values

| Value | Meaning | source_id | target_id |
|-------|---------|-----------|-----------|
| `unchanged` | Test passes through without modification | single | same as source |
| `modified` | Same test ID, adjusted parameters or pass conditions | single | same as source |
| `redesigned` | Substantially different test, may have new ID | single | single (may differ) |
| `split` | One source test became multiple target tests | single | comma-separated list |
| `merged` | Multiple source tests became one target test | single* | single |
| `removed` | Test dropped, not replaced | single | null |
| `new` | No predecessor in source version | null | single |

*For `merged`, each source test has its own row pointing to the same target.

## Completeness Rules

1. Every source version test ID must appear exactly once as `source_id`.
2. Every target version test ID must appear at least once as `target_id`.
3. No orphans: a target_id that doesn't exist in the new protocol is an error.
4. No ghosts: a new protocol test ID not in the mapping is an error.

## Example

```yaml
mapping:
  - source_id: A-1
    target_id: A-1
    relationship: unchanged
    notes: null

  - source_id: A-8
    target_id: A-8
    relationship: redesigned
    notes: "Graduated stochastic criteria replacing binary pass/fail"

  - source_id: B-4
    target_id: null
    relationship: removed
    notes: "Redundant with redesigned A-8; loop ergonomics covered by B-3"

  - source_id: C-8
    target_id: "C-8a, C-8b"
    relationship: split
    notes: "Separated SCOPF formulation verification from scale testing"

  - source_id: null
    target_id: C-11
    relationship: new
    notes: "AC OPF convergence verification on congested network"
```
