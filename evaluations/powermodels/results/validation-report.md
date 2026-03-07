# Validation Report — PowerModels.jl Phase 1 Evaluation

**Generated:** 2026-03-07
**Protocol version:** v4

## Coverage

- **Config test IDs:** 57
- **Result files produced:** 76 (tests with both functional and grade tiers produce 2 files)
- **Gaps:** 0 — all test IDs have corresponding result files

## Frontmatter Validation

- **Files checked:** 76
- **Errors found:** 5 (all corrected)
  - `C-3_dcopf_scale_MEDIUM.md`: `workaround_class: data_workaround` → fixed to `stable`
  - `A-3_dcopf_MEDIUM.md`: `workaround_class: data_workaround` → fixed to `stable`
  - `C-5_contingency_sweep_scale_MEDIUM.md`: `status: not_attempted` → fixed to `fail`
  - `C-8_scopf_scale_MEDIUM.md`: `status: not_attempted` → fixed to `fail`
  - `A-7_contingency_sweep_MEDIUM.md`: `status: not_attempted` → fixed to `fail`
- **Errors after fixes:** 0
- **Warnings:** 0

## Naming Convention

All 76 files follow the `<test_id>_<slug>[_<TIER>].md` convention. No deviations.

## Status Summary

| Status | Count |
|--------|-------|
| pass | 37 |
| qualified_pass | 21 |
| fail | 12 |
| informational | 6 |
| **Total** | **76** |

## Result Matrix

| Test ID | Network | Status | Workaround | File |
|---------|---------|--------|------------|------|
| G-1 | TINY | pass | - | G-1_ingest_tiny.md |
| G-2 | SMALL | pass | - | G-2_ingest_small.md |
| G-3 | MEDIUM | pass | - | G-3_ingest_medium.md |
| A-1 | TINY | pass | - | A-1_dcpf_TINY.md |
| A-1 | MEDIUM | pass | - | A-1_dcpf_MEDIUM.md |
| A-2 | TINY | pass | - | A-2_acpf_TINY.md |
| A-2 | MEDIUM | fail | - | A-2_acpf_MEDIUM.md |
| A-3 | TINY | pass | - | A-3_dcopf_TINY.md |
| A-3 | MEDIUM | pass | stable | A-3_dcopf_MEDIUM.md |
| A-4 | TINY | pass | - | A-4_ac_feasibility_TINY.md |
| A-4 | MEDIUM | qualified_pass | stable | A-4_ac_feasibility_MEDIUM.md |
| A-5 | TINY | qualified_pass | stable | A-5_scuc_TINY.md |
| A-5 | SMALL | fail | stable | A-5_scuc_SMALL.md |
| A-6 | TINY | qualified_pass | stable | A-6_sced_TINY.md |
| A-6 | SMALL | fail | stable | A-6_sced_SMALL.md |
| A-7 | TINY | qualified_pass | stable | A-7_contingency_sweep_TINY.md |
| A-7 | MEDIUM | fail | stable | A-7_contingency_sweep_MEDIUM.md |
| A-8 | TINY | fail | blocking | A-8_stochastic_timeseries_TINY.md |
| A-8 | SMALL | fail | blocking | A-8_stochastic_timeseries_SMALL.md |
| A-9 | TINY | qualified_pass | stable | A-9_scopf_TINY.md |
| A-9 | SMALL | qualified_pass | stable | A-9_scopf_SMALL.md |
| A-10 | TINY | qualified_pass | stable | A-10_lossy_dcopf_lmp_TINY.md |
| A-10 | SMALL | qualified_pass | stable | A-10_lossy_dcopf_lmp_SMALL.md |
| A-11 | TINY | qualified_pass | stable | A-11_distributed_slack_opf_TINY.md |
| A-11 | SMALL | qualified_pass | stable | A-11_distributed_slack_opf_SMALL.md |
| B-1 | TINY | pass | - | B-1_custom_constraints_TINY.md |
| B-1 | MEDIUM | pass | - | B-1_custom_constraints_MEDIUM.md |
| B-2 | TINY | qualified_pass | stable | B-2_graph_access_TINY.md |
| B-2 | MEDIUM | qualified_pass | stable | B-2_graph_access_MEDIUM.md |
| B-3 | TINY | pass | - | B-3_contingency_loop_TINY.md |
| B-3 | MEDIUM | pass | - | B-3_contingency_loop_MEDIUM.md |
| B-4 | TINY | pass | - | B-4_stochastic_wrapping_TINY.md |
| B-4 | SMALL | pass | - | B-4_stochastic_wrapping_SMALL.md |
| B-5 | TINY | pass | - | B-5_interoperability_TINY.md |
| B-5 | MEDIUM | pass | - | B-5_interoperability_MEDIUM.md |
| B-6 | N/A | pass | - | B-6_code_architecture.md |
| B-7 | TINY | pass | - | B-7_ac_feasibility_extension_TINY.md |
| B-7 | MEDIUM | pass | - | B-7_ac_feasibility_extension_MEDIUM.md |
| B-8 | TINY | pass | stable | B-8_reference_bus_config_TINY.md |
| B-8 | SMALL | pass | stable | B-8_reference_bus_config_SMALL.md |
| B-9 | TINY | pass | - | B-9_ptdf_extraction_TINY.md |
| B-9 | MEDIUM | pass | - | B-9_ptdf_extraction_MEDIUM.md |
| C-1 | MEDIUM | pass | - | C-1_dcpf_scale_MEDIUM.md |
| C-2 | MEDIUM | fail | - | C-2_acpf_scale_MEDIUM.md |
| C-3 | MEDIUM | pass | stable | C-3_dcopf_scale_MEDIUM.md |
| C-4 | SMALL | fail | stable | C-4_scuc_scale_SMALL.md |
| C-5 | MEDIUM | fail | stable | C-5_contingency_sweep_scale_MEDIUM.md |
| C-6 | SMALL | pass | - | C-6_stochastic_scale_SMALL.md |
| C-7 | MEDIUM | qualified_pass | stable | C-7_solver_swap_MEDIUM.md |
| C-8 | MEDIUM | fail | stable | C-8_scopf_scale_MEDIUM.md |
| C-9 | MEDIUM | pass | - | C-9_ptdf_scale_MEDIUM.md |
| C-10 | MEDIUM | qualified_pass | stable | C-10_distributed_slack_scale_MEDIUM.md |
| D-1 | N/A | qualified_pass | - | D-1_install_to_first_solve.md |
| D-2 | N/A | qualified_pass | - | D-2_documentation_audit.md |
| D-3 | N/A | qualified_pass | - | D-3_example_verification.md |
| D-4 | N/A | qualified_pass | - | D-4_error_quality.md |
| D-5 | N/A | informational | - | D-5_code_volume.md |
| E-1 | N/A | pass | - | E-1_release_cadence.md |
| E-2 | N/A | qualified_pass | - | E-2_commit_activity.md |
| E-3 | N/A | fail | - | E-3_contributor_concentration.md |
| E-4 | N/A | informational | - | E-4_funding_model.md |
| E-5 | N/A | qualified_pass | - | E-5_issue_tracker_health.md |
| E-6 | N/A | pass | - | E-6_ci_test_coverage.md |
| E-7 | N/A | fail | - | E-7_operational_adoption.md |
| F-1 | N/A | pass | - | F-1_core_license.md |
| F-2 | N/A | informational | - | F-2_dependency_tree.md |
| F-3 | N/A | qualified_pass | - | F-3_dependency_license_audit.md |
| F-4 | N/A | pass | - | F-4_compiled_extension_audit.md |
| F-5 | N/A | pass | - | F-5_code_inspectability_trace.md |
| F-6 | N/A | pass | - | F-6_distribution_integrity.md |
| F-7 | N/A | pass | - | F-7_airgap_installability.md |
| F-8 | N/A | pass | - | F-8_solver_dependency_assessment.md |
| F-9 | N/A | pass | - | F-9_getting_started_integrity.md |
| P2-1 | N/A | informational | - | P2-1_psse_raw_parsing.md |
| P2-2 | TINY | informational | - | P2-2_piecewise_linear_cost.md |
| P2-3 | TINY | informational | - | P2-3_commitment_injection.md |

## Conclusion

All 57 test IDs from `eval-config.yaml` have corresponding result files (76 total across tiers). All frontmatter is valid after corrections. No gaps block synthesis.
