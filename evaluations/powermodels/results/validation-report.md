# PowerModels.jl Evaluation — Validation Report

Generated: 2026-03-12

## Summary

- **Total test IDs in config**: 63
- **Result files found**: 93 (covering all 63 test IDs)
- **Gaps (missing files)**: 0
- **Frontmatter violations**: 0
- **Warnings**: 5

## Coverage

| Test ID | Expected Files | Found | Status |
|---------|---------------|-------|--------|
| G-1 | G-1_ingest_tiny.md | ✓ | OK (naming deviation — see Warnings) |
| G-2 | G-2_ingest_small.md | ✓ | OK (naming deviation — see Warnings) |
| G-3 | G-3_ingest_medium.md | ✓ | OK (naming deviation — see Warnings) |
| A-1 | A-1_dcpf_TINY.md, A-1_dcpf_MEDIUM.md | ✓ | OK |
| A-2 | A-2_acpf_TINY.md, A-2_acpf_MEDIUM.md | ✓ | OK |
| A-3 | A-3_dcopf_TINY.md, A-3_dcopf_MEDIUM.md | ✓ | OK |
| A-4 | A-4_ac_feasibility_check_TINY.md, A-4_ac_feasibility_check_MEDIUM.md | ✓ | OK |
| A-5 | A-5_scuc_TINY.md, A-5_scuc_SMALL.md | ✓ | OK |
| A-6 | A-6_sced_TINY.md, A-6_sced_SMALL.md | ✓ | OK |
| A-7 | A-7_contingency_sweep_TINY.md, A-7_contingency_sweep_MEDIUM.md | ✓ | OK |
| A-8 | A-8_stochastic_timeseries_TINY.md, A-8_stochastic_timeseries_SMALL.md | ✓ | OK |
| A-9 | A-9_scopf_TINY.md, A-9_scopf_SMALL.md | ✓ | OK |
| A-10 | A-10_lossy_dcopf_lmp_decomposition_TINY.md, A-10_lossy_dcopf_lmp_decomposition_SMALL.md | ✓ | OK |
| A-11 | A-11_distributed_slack_opf_TINY.md, A-11_distributed_slack_opf_SMALL.md | ✓ | OK |
| A-12 | A-12_multiperiod_dcopf_storage_TINY.md | ✓ | OK |
| B-1 | B-1_custom_constraints_TINY.md, B-1_custom_constraints_MEDIUM.md | ✓ | OK |
| B-2 | B-2_graph_access_TINY.md, B-2_graph_access_MEDIUM.md | ✓ | OK |
| B-3 | B-3_contingency_loop_TINY.md, B-3_contingency_loop_MEDIUM.md | ✓ | OK |
| B-4 | B-4_stochastic_scenario_wrapping_TINY.md, B-4_stochastic_scenario_wrapping_SMALL.md | ✓ | OK |
| B-5 | B-5_interoperability_TINY.md, B-5_interoperability_MEDIUM.md | ✓ | OK |
| B-6 | B-6_code_architecture.md | ✓ | OK |
| B-7 | B-7_ac_feasibility_extension_TINY.md, B-7_ac_feasibility_extension_MEDIUM.md | ✓ | OK |
| B-8 | B-8_reference_bus_configuration_TINY.md, B-8_reference_bus_configuration_SMALL.md | ✓ | OK |
| B-9 | B-9_ptdf_extraction_TINY.md, B-9_ptdf_extraction_MEDIUM.md | ✓ | OK |
| C-1 | C-1_dcpf_scale_MEDIUM.md | ✓ | OK |
| C-2 | C-2_acpf_scale_MEDIUM.md | ✓ | OK |
| C-3 | C-3_dcopf_scale_MEDIUM.md | ✓ | OK |
| C-4 | C-4_scuc_scale_SMALL.md | ✓ | OK |
| C-5 | C-5_contingency_sweep_scale_MEDIUM.md | ✓ | OK |
| C-6 | C-6_stochastic_dcopf_scale_SMALL.md | ✓ | OK |
| C-7 | C-7_solver_swap_MEDIUM.md | ✓ | OK |
| C-8 | C-8_scopf_scale_MEDIUM.md | ✓ | OK |
| C-9 | C-9_ptdf_matrix_computation_MEDIUM.md | ✓ | OK |
| C-10 | C-10_distributed_slack_dcopf_scale_MEDIUM.md | ✓ | OK |
| D-1 | D-1_install_to_first_solve.md | ✓ | OK |
| D-2 | D-2_documentation_audit.md | ✓ | OK |
| D-3 | D-3_example_verification.md | ✓ | OK |
| D-4 | D-4_error_quality.md | ✓ | OK |
| D-5 | D-5_code_volume.md | ✓ | OK |
| E-1 | E-1_release_cadence.md | ✓ | OK |
| E-2 | E-2_commit_activity.md | ✓ | OK |
| E-3 | E-3_contributor_concentration.md | ✓ | OK |
| E-4 | E-4_funding_model.md | ✓ | OK |
| E-5 | E-5_issue_tracker_health.md | ✓ | OK |
| E-6 | E-6_ci_test_coverage.md | ✓ | OK |
| E-7 | E-7_operational_adoption.md | ✓ | OK |
| F-1 | F-1_core_license.md | ✓ | OK |
| F-2 | F-2_dependency_tree.md | ✓ | OK |
| F-3 | F-3_dependency_license_audit.md | ✓ | OK |
| F-4 | F-4_compiled_extension_audit.md | ✓ | OK |
| F-5 | F-5_code_inspectability.md | ✓ | OK |
| F-6 | F-6_distribution_integrity.md | ✓ | OK |
| F-7 | F-7_air_gap_installability.md | ✓ | OK |
| F-8 | F-8_solver_dependency_assessment.md | ✓ | OK |
| F-9 | F-9_getting_started_artifact_integrity.md | ✓ | OK |
| G-FNM-1 | G-FNM-1_intermediate_ingestion.md | ✓ | OK (slug deviation — see Warnings) |
| G-FNM-2 | G-FNM-2_field_coverage_audit.md | ✓ | OK (slug deviation — see Warnings) |
| G-FNM-3 | G-FNM-3_dcpf_verification.md | ✓ | OK (slug deviation — see Warnings) |
| G-FNM-4 | G-FNM-4_acpf_convergence.md | ✓ | OK (slug deviation — see Warnings) |
| G-FNM-5 | G-FNM-5_supplemental_csv_representability.md | ✓ | OK (slug deviation — see Warnings) |
| P2-1 | P2-1_psse_raw_parsing.md | ✓ | OK |
| P2-2 | P2-2_piecewise_linear_costs.md | ✓ | OK |
| P2-3 | P2-3_commitment_injection_workflow.md | ✓ | OK |

## Gaps

None. All 63 test IDs have result files present.

## Frontmatter Violations

None. All required fields (`test_id`, `tool`, `dimension`, `network`, `status`, `workaround_class`, `timestamp`, `protocol_version`, `skill_version`, `test_hash`) are present in every result file. All `status` values are from the allowed set (`pass`, `fail`, `qualified_pass`, `informational`). All `workaround_class` values are from the allowed set (`null`, `stable`, `fragile`, `blocking`). All `test_hash` values match the config.

## Warnings

### W-1: Gate file naming — no tier suffix in filename

Files `G-1_ingest_tiny.md`, `G-2_ingest_small.md`, `G-3_ingest_medium.md` embed the tier in the slug portion of the name rather than as a `_TINY` / `_SMALL` / `_MEDIUM` suffix. The `network` field in the frontmatter correctly records TINY, SMALL, MEDIUM. This is a cosmetic deviation with no correctness impact; synthesis can rely on the frontmatter `network` field.

### W-2: FNM ingestion file slugs differ from config slugs

Config slugs for G-FNM-* are `fnm_ingestion_gate`, `fnm_field_coverage`, `fnm_dcpf_verification`, `fnm_acpf_convergence`, `fnm_supplemental_csv_representability`. Actual filenames use abbreviated slugs: `intermediate_ingestion`, `field_coverage_audit`, `dcpf_verification`, `acpf_convergence`, `supplemental_csv_representability`. Frontmatter `test_id` fields are correct. No correctness impact.

### W-3: Fail results present — for documentation, not blocking synthesis

The following tests have `status: fail`. These are expected outcomes and do not block synthesis.

| File | Failure reason |
|------|---------------|
| A-2_acpf_MEDIUM.md | NLsolve convergence failure at 10k-bus scale |
| A-4_ac_feasibility_check_MEDIUM.md | ACPF failure cascaded from A-2; Ipopt diverges |
| A-5_scuc_TINY.md | SCUC unsupported in PowerModels.jl |
| A-5_scuc_SMALL.md | Blocked by A-5 functional failure |
| A-6_sced_SMALL.md | Blocked by A-5 (no SCUC base for SCED) |
| A-8_stochastic_timeseries_TINY.md | No native stochastic API in PowerModels.jl |
| A-8_stochastic_timeseries_SMALL.md | Blocked by A-8 TINY failure |
| A-11_distributed_slack_opf_TINY.md | Distributed slack unsupported in installed version |
| A-11_distributed_slack_opf_SMALL.md | Blocked by A-11 TINY failure |
| B-7_ac_feasibility_extension_MEDIUM.md | No viable ACPF workaround at MEDIUM scale |
| C-2_acpf_scale_MEDIUM.md | Blocked by A-2 MEDIUM failure |
| C-4_scuc_scale_SMALL.md | Blocked by A-5 |
| C-10_distributed_slack_dcopf_scale_MEDIUM.md | Blocked by A-11 |
| E-3_contributor_concentration.md | High contributor concentration (informational risk flag) |
| G-FNM-1_intermediate_ingestion.md | PSS/E v31 header incompatibility; ingestion blocked |
| G-FNM-2_field_coverage_audit.md | Blocked by G-FNM-1 |
| G-FNM-3_dcpf_verification.md | Blocked by G-FNM-1 |
| G-FNM-4_acpf_convergence.md | Blocked by G-FNM-1 |
| G-FNM-5_supplemental_csv_representability.md | Blocked by G-FNM-1 |

### W-4: A-12 workaround_class is `stable` with status `pass`

`A-12_multiperiod_dcopf_storage_TINY.md` has `status: pass` but `workaround_class: stable`. This is technically allowed (a workaround was used but is considered stable enough to record as a pass). Synthesis should note this when grading — it is a pass with a dependency on SCIP for MIQP.

### W-5: P2-2 and P2-3 use `network: TINY` instead of `N/A`

`P2-2_piecewise_linear_costs.md` and `P2-3_commitment_injection_workflow.md` have `network: TINY` in their frontmatter. The config specifies `functional_network: N/A` for P2-2 and `functional_network: TINY` for P2-3. P2-3 recording TINY is consistent with the config. P2-2 recording TINY rather than N/A is a minor inconsistency but does not affect test identity or correctness.
