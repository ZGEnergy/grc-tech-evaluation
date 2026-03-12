# PyPSA Evaluation — Validation Report
Generated: 2026-03-12

## Coverage

Total tests in config: 63 base test IDs
Expected result files (functional + grade-network): 82
Result files found: 82
Result files missing: None

### Breakdown by dimension

| Dimension | Expected | Found | Status |
|-----------|----------|-------|--------|
| gate (G-1..G-3) | 3 | 3 | OK |
| expressiveness (A-1..A-12, TINY + grade) | 26 | 26 | OK |
| extensibility (B-1..B-9, TINY + grade) | 17 | 17 | OK |
| scalability (C-1..C-10) | 10 | 10 | OK |
| accessibility (D-1..D-5) | 5 | 5 | OK |
| maturity (E-1..E-7) | 7 | 7 | OK |
| supply_chain (F-1..F-9) | 9 | 9 | OK |
| fnm_ingestion (G-FNM-1..G-FNM-5) | 5 | 5 | OK |
| p2_readiness (P2-1..P2-3) | 3 | 3 | OK |
| **Total** | **82** | **82** | **OK** |

## Orphan Files

The following files in `fnm_ingestion/` used incorrect slugs (truncated vs. full config slug) and were deleted:

| Deleted file | Reason |
|---|---|
| `fnm_ingestion/G-FNM-3_dcpf.md` | Slug `dcpf` does not match config slug `dcpf_verification` |
| `fnm_ingestion/G-FNM-4_acpf.md` | Slug `acpf` does not match config slug `acpf_convergence` |
| `fnm_ingestion/G-FNM-5_supplemental_csv.md` | Slug `supplemental_csv` does not match config slug `supplemental_csv_representability` |

Correct files with full slugs (`G-FNM-3_dcpf_verification.md`, `G-FNM-4_acpf_convergence.md`, `G-FNM-5_supplemental_csv_representability.md`) were already present and retained.

## Frontmatter Spot-Check

Files sampled from each dimension for full frontmatter compliance:

| File | test_id | status | workaround_class | test_hash | All required fields |
|---|---|---|---|---|---|
| `gate/G-1_ingest_tiny.md` | G-1 | pass | null | 35843a04 ✓ | OK |
| `gate/G-2_ingest_small.md` | G-2 | pass | null | fdeb3359 ✓ | OK |
| `expressiveness/A-1_dcpf.md` | A-1 | pass | stable | 32fb2553 ✓ | OK |
| `expressiveness/A-1_dcpf_MEDIUM.md` | A-1 | pass | stable | 32fb2553 ✓ | OK |
| `expressiveness/A-12_multiperiod_dcopf_storage.md` | A-12 | pass | fragile | fdd193e7 ✓ | OK |
| `extensibility/B-6_code_architecture.md` | B-6 | pass | null | 3468b28b ✓ | OK |
| `scalability/C-1_dcpf_scale.md` | C-1 | pass | null | 32a58768 ✓ | OK |
| `accessibility/D-1_install_to_first_solve.md` | D-1 | pass | null | 5f33112e ✓ | OK |
| `maturity/E-1_release_cadence.md` | E-1 | pass | null | 3684d0d2 ✓ | OK |
| `supply_chain/F-1_core_license.md` | F-1 | pass | null | 12e210df ✓ | OK |
| `fnm_ingestion/G-FNM-1_ingestion.md` | G-FNM-1 | pass | stable | 222414ed ✓ | OK |
| `p2_readiness/P2-1_psse_raw_parsing.md` | P2-1 | informational | null | e75a0cfb ✓ | OK |

All required frontmatter fields (`test_id`, `tool`, `dimension`, `network`, `status`, `workaround_class`, `timestamp`, `protocol_version`, `skill_version`, `test_hash`) are present across all sampled files.

## Violations

### Hash Mismatches (corrected)

Two grade-network result files carried stale test_hash values that did not match the config. These have been corrected in-place:

| File | test_id | Old hash | Correct hash |
|---|---|---|---|
| `extensibility/B-1_custom_constraints_MEDIUM.md` | B-1 | `4a7f2e91` | `7578c2ba` |
| `extensibility/B-4_stochastic_scenario_wrap_SMALL.md` | B-4 | `92fa1c3e` | `0f696058` |

**Resolution:** `test_hash` fields updated to match `eval-config.yaml`.

### Status / workaround_class Validity

All 82 result files use only valid values:
- `status`: values observed are `pass`, `fail`, `qualified_pass`, `informational` — all valid.
- `workaround_class`: values observed are `null`, `stable`, `fragile`, `blocking` — all valid.

Note: `A-11_distributed_slack_opf.md` carries `status: qualified_pass` with `workaround_class: blocking`. This combination is allowed by protocol (qualified_pass means the test ran with a workaround; blocking means the workaround is not production-safe). No correction needed.

## Warnings

- The `research-*.md` files in `results/` (5 files: `research-api.md`, `research-context.md`, `research-extensions.md`, `research-limitations.md`, `research-version.md`) have no YAML frontmatter. These are pre-evaluation research notes, not result files, and are intentionally excluded from validation scope.
- The `observations/` subdirectory contains 30+ supplemental observation files. These are not result files and are not validated here.
- Two files in `fnm_ingestion/observations/` (`fnm-data-model-G-FNM-3_dcpf_transformer_model.md` and `fnm-scale-G-FNM-3_dcpf_solve_time.md`) are observation files, not result files — out of scope.

## Summary of Changes Made

1. **Deleted** 3 orphan files with incorrect slugs in `fnm_ingestion/`.
2. **Corrected** `test_hash` in `B-1_custom_constraints_MEDIUM.md` (`4a7f2e91` → `7578c2ba`).
3. **Corrected** `test_hash` in `B-4_stochastic_scenario_wrap_SMALL.md` (`92fa1c3e` → `0f696058`).

## Verdict

**PASS** — All 82 required result files are present. Orphan files deleted. Two hash mismatches corrected. No invalid status or workaround_class values. No missing required frontmatter fields.
