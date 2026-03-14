# Validation Report — PyPSA v10

## Completeness

All 59 test IDs from eval-config.yaml have corresponding result files. Zero gaps.

## Status Distribution

| Status | Count |
|--------|-------|
| pass | 38 |
| qualified_pass | 3 |
| fail | 3 |
| skip | 8 |
| informational | 8 |
| **Total** | **60** |

Note: 60 files for 59 test IDs because C-5 has separate SMALL and MEDIUM result files.

## Failures

| Test | Reason |
|------|--------|
| G-FNM-1 | No PSS/E CSV ingestion capability (psse_parse_error) |
| G-FNM-3 | DCPF verification failed — systematic impedance conversion differences via MATPOWER fallback |
| C-4 | SCUC 24hr on SMALL — HiGHS timeout (600s), SCIP not installed |

## Qualified Passes

| Test | Workaround Class | Issue |
|------|-----------------|-------|
| A-6 | stable | No `fix_commitment()` API; manual p_min_pu/p_max_pu injection |
| A-11 | blocking | Distributed slack OPF architecturally impossible (no Bus-v_ang variable) |
| A-12 | fragile | Branch shadow prices empty after optimize(); requires linopy internal extraction |

## Skips

| Test | Blocked By |
|------|-----------|
| G-FNM-2 | G-FNM-1 |
| C-1, C-2, C-3, C-7, C-8, C-9, C-10 | C-SMALL-gate (C-4 failure) |

## Frontmatter Validation

- All 60 result files have required fields: test_id, tool, status, protocol_version, skill_version, test_hash, timestamp
- All status values are valid (pass/fail/qualified_pass/informational/skip)
- Zero violations

## Naming Validation

All files follow `<test_id>_<slug>.md` or `<test_id>_<slug>_<TIER>.md` convention. Zero deviations.

## Observation Files

30 observation files written to `evaluations/pypsa/results/observations/`.
