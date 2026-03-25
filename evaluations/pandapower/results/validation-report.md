# Validation Report — pandapower Phase 1 Evaluation

**Protocol version:** v11
**Skill version:** v2
**Validated:** 2026-03-24

## Summary

- **Total tests in config:** 59
- **Result files found:** 59/59
- **Gaps:** 0
- **Frontmatter violations:** 0
- **Naming warnings:** 0

## Test Coverage by Dimension

| Dimension | Tests | Pass | Fail | Partial/Qualified | Informational | Skip |
|-----------|-------|------|------|-------------------|---------------|------|
| gate | 3 | 3 | 0 | 0 | 0 | 0 |
| expressiveness | 10 | 4 | 4 | 2 | 0 | 0 |
| extensibility | 8 | 5 | 0 | 2 | 0 | 0 |
| scalability | 10 | 4 | 5 | 0 | 0 | 0 |
| accessibility | 5 | 0 | 0 | 0 | 5 | 0 |
| maturity | 7 | 0 | 0 | 0 | 7 | 0 |
| supply_chain | 9 | 0 | 0 | 0 | 9 | 0 |
| fnm_ingestion | 5 | 0 | 2 | 0 | 2 | 1 |
| p2_readiness | 3 | 0 | 0 | 0 | 3 | 0 |

## Detailed Status by Test

### Gate (3/3 pass)
- G-1: pass | G-2: pass | G-3: pass

### Expressiveness (4 pass, 4 fail, 2 partial)
- A-1 (DCPF): pass | A-2 (ACPF): pass | A-3 (DCOPF): pass | A-4 (AC feasibility): pass
- A-5 (SCUC): fail [unsupported] | A-10 (lossy DCOPF): fail [unsupported]
- A-11 (distributed slack OPF): fail [unsupported] | A-12 (multi-period DCOPF): fail [unsupported]
- A-6 (SCED): partial_pass [ed_only] | A-9 (SCOPF): partial_pass [manual construction]

### Extensibility (5 pass, 2 partial/qualified)
- B-2: pass | B-3: pass | B-4: pass | B-5: pass | B-9: pass
- B-1 (custom constraints): partial_pass [fragile workaround]
- B-6 (architecture): pass | B-8 (reference bus): qualified_pass [stable workaround]

### Scalability (4 pass, 5 fail, 1 informational)
- C-1 (DCPF MEDIUM): pass | C-2 (ACPF MEDIUM): pass | C-3 (DCOPF MEDIUM): pass
- C-5 (AC feasibility SMALL): pass | C-5 (AC feasibility MEDIUM): pass
- C-9 (PTDF MEDIUM): pass
- C-4 (SCUC SMALL): fail [blocked_by: A-5] | C-7 (solver swap): fail [no swap mechanism]
- C-8 (SCOPF MEDIUM): fail [OOM] | C-10 (distributed slack MEDIUM): fail [blocked_by: A-11]

### FNM Ingestion (2 fail, 2 informational, 1 skip)
- G-FNM-1: fail [no PSS/E parser] | G-FNM-2: skip [blocked_by: G-FNM-1]
- G-FNM-3: fail [hard-fail on branch deviation] | G-FNM-4: informational [infeasible]
- G-FNM-5: informational

## Validation Checks

All 59 result files pass:
- Required frontmatter fields present
- test_hash matches eval-config.yaml
- protocol_version = v11, skill_version = v2
- Valid status and workaround_class values
