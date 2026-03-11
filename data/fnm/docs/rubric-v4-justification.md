# Rubric v4 Amendment Justification

Rubric v3 explicitly excludes the Full Network Model (FNM) from Phase 1 testing, stating: "The Full Network Model (FNM) is not used in Phase 1 testing." Rubric v4 amends this exclusion to incorporate FNM ingestion results as additive evidence for Expressiveness and Extensibility grades. The amendment creates no new grading criteria, introduces no new grade boundaries, and changes no A/B/C threshold definitions; FNM results inform grade narratives through grading notes appended to the existing Expressiveness and Extensibility criteria. All FNM-dependent tests are gated by the `FNM_PATH` environment variable, ensuring tools receive complete Phase 1 grades on all six criteria without FNM data. This amendment follows the precedent established by rubric v2, which added SCOPF, lossy DC OPF, and distributed slack OPF as supplementary sub-questions (Expressiveness 9--11) with an identical grading mechanism: informing the grade narrative without automatically overriding primary sub-question results.

## Why Data Model Fidelity Belongs in Phase 1

Phase 1 evaluates tool capability, not deployment readiness. The rubric's two highest-priority criteria -- Expressiveness and Extensibility -- ask "can the tool represent the problems we need to solve?" and "can an analyst extend the tool beyond built-in problems?" Data model fidelity -- whether a tool's internal data model can represent the full parameter space of a production transmission network -- is a direct measurement of both. A tool whose data model cannot hold 3-winding transformers or switched shunt discrete steps has an expressiveness limitation. A tool that requires analyst-built workarounds to represent area interchange data has an extensibility cost. These are capability questions that belong in Phase 1.

FNM ingestion is a data model test, not a scenario test. The question it answers is: "given a production network's full parameter space, can the tool's data model hold it without loss?" This is structurally identical to Phase 1's existing tests, which ask: "given a synthetic MATPOWER case, can the tool ingest and solve it?" The FNM simply provides a harder, more realistic input that exercises data model dimensions the synthetic cases cannot reach. No scenario analysis, congestion reproduction, or market clearing simulation is involved -- the test is purely about data model fidelity.

The distinction between Phase 1 and Phase 2 is not synthetic-versus-production data. It is capability-assessment versus operational-workflow. Phase 1 asks whether the tool *can* represent, ingest, and solve. Phase 2 asks whether the tool *should be used* for specific operational tasks such as congestion pattern reproduction and market clearing simulation. FNM ingestion testing -- "can the tool hold this network?" -- is firmly on the Phase 1 side of this boundary.

Deferring data model fidelity testing entirely to Phase 2 creates a systematic gap in Phase 1 evaluation. Phase 1 grades would assess expressiveness only against synthetic cases that lack critical record types and fields, producing artificially similar grades across tools that have very different production-network capabilities. This is analogous to evaluating a programming language only against trivial programs -- the tools appear equivalent until confronted with real-world complexity. Incorporating FNM evidence in Phase 1 closes this gap without converting Phase 1 into a deployment assessment.

## Evidence: FNM vs. Synthetic Case Coverage

The synthetic MATPOWER test cases (ACTIVSg 2k and 10k) use the MATPOWER .m format, a simplified representation of an AC transmission network. The .m format represents buses, branches (AC lines), generators, generator cost curves, and basic transformer data as branch-table rows. It does not natively represent many PSS/E v31 record types that exist in production ISO network models like the FNM. This structural limitation means that Phase 1 testing on synthetic cases alone produces no evidence -- positive or negative -- about a tool's ability to handle record types absent from the .m format.

### Table 1: Record Types Present in FNM but Absent or Degraded in Synthetic Cases

The following table identifies PSS/E v31 record types that are non-empty in the FNM but cannot be faithfully represented in MATPOWER .m format. Tier classifications are from the Record-Type Mapping Guide (`mapping-guide.md`).

| Record Type | PSS/E Section | Tier | FNM Status | Synthetic Case Status |
|-------------|---------------|------|------------|-----------------------|
| 3-Winding Transformer | Section 6 (K!=0) | 1 | Non-empty | MATPOWER .m branch table has no K field for 3-winding topology; `psse2mpc` decomposes 3-winding transformers to star-bus 2-winding equivalents, so tool support for native 3-winding representation is untestable |
| Switched Shunt | Section 17 | 2 | Non-empty | MATPOWER .m represents shunts via the bus-table BS column as continuous min/max susceptance bounds; discrete step structure (N1/B1 through N8/B8), voltage regulation targets (VSWHI/VSWLO), and control mode (MODSW) are collapsed and lost |
| Area | Section 7 | 2 | Non-empty | MATPOWER .m `mpc.areas` matrix stores only area number and slack bus (ISW); desired interchange (PDES) and interchange tolerance (PTOL) are present but area interchange control semantics are not exercised in synthetic test suites |
| Fixed Shunt | Section 3 | 2 | Non-empty | MATPOWER .m folds fixed shunts into bus-table GS/BS columns; multiple shunts at the same bus are summed into a single pair of values, losing individual shunt identity, per-shunt status control, and shunt identifiers |
| Owner | Section 15 | 3 | Non-empty | No representation in the MATPOWER .m `mpc` struct; ownership data on generators, branches, and transformers is silently discarded by `psse2mpc` conversion |
| Zone | Section 13 | 3 | Non-empty | MATPOWER .m bus matrix includes a ZONE column for bus-to-zone assignment, but the zone name table has no .m counterpart; zone semantics are reduced to integer labels |

For any record type absent from synthetic cases, Phase 1 produces no evidence of tool capability. The tool receives neither credit for supporting it nor penalty for lacking it. This blind spot is most consequential for Tier 1 and Tier 2 record types that directly affect power flow accuracy. For example, 3-winding transformers are a Tier 1 record type -- essential for correct network topology -- yet no synthetic MATPOWER case can test whether a tool supports them natively or requires star-bus decomposition.

### Table 2: Field Coverage Gap Summary

The following table quantifies the field-level coverage gap between the FNM intermediate format (which represents all PSS/E v31 fields across all non-empty record types) and what MATPOWER .m cases can exercise. Counts are derived from the Field Criticality Matrix (`field-criticality-matrix.md`) summary table, which classifies all 350 fields across 17 record types.

The 10 non-empty record types in the FNM (Bus, Load, Fixed Shunt, Generator, Branch, Transformer, Area, Zone, Owner, Switched Shunt) account for 201 of the 350 total fields. Of these 201 fields, only a subset can be exercised through MATPOWER .m synthetic cases, because the .m format either lacks the record type entirely (Owner), collapses the record type into bus-level aggregates (Fixed Shunt, Switched Shunt), or omits fields that the PSS/E format carries (e.g., transformer control mode codes, switched shunt discrete step blocks).

| Metric | FNM Intermediate Format | MATPOWER .m Cases | Gap |
|--------|------------------------|-------------------|-----|
| Total fields across non-empty record types | 201 | ~120 | ~81 |
| DCPF-critical fields | 26 | 26 | 0 |
| ACPF-critical fields | 93 | ~25 | ~68 |
| Record types with non-empty FNM representation | 10 | 8 (with fidelity loss) | 2 fully absent |

The DCPF-critical field gap is zero because all 26 DCPF-critical fields fall within Bus, Load, Generator, Branch, and Transformer record types that MATPOWER .m can represent at the topology level. The ACPF-critical field gap is substantial: 93 ACPF-critical fields exist across the non-empty FNM record types, but only approximately 25 are exercisable through .m cases. The remaining ~68 ACPF-critical fields reside in record types that .m either omits (Switched Shunt discrete steps, Area interchange parameters) or represents with fidelity loss (transformer control modes, fixed shunt aggregation). This gap distinguishes between "field exists in FNM but not in .m" (a format limitation preventing any test coverage) and "field exists in both but .m representation is lossy" (a fidelity limitation that may mask tool-level differences).

Beyond record type and field coverage, the FNM's approximately 30,000 buses and approximately 39,000 transformers create a parameter-space breadth that cannot be tested on a 10,000-bus synthetic case. Parameter interactions that only surface at production scale -- switched shunt hunting between discrete steps, transformer tap oscillation near control mode boundaries, area interchange convergence sensitivity with dozens of interconnected areas -- are invisible in smaller cases. The FNM exercises these interactions simultaneously across the full network, providing evidence of data model robustness that no synthetic case can replicate.

As concrete examples of tool differentiation that FNM testing reveals: pandapower has native 3-winding transformer support via `create_transformer3w()` while PyPSA requires star-bus decomposition into multiple 2-winding `Transformer` components -- this distinction is untestable without a network that contains 3-winding transformer records (K!=0). Similarly, GridCal has a `ControllableShunt` object with discrete step modeling and voltage regulation targets while MATPOWER collapses discrete steps to continuous susceptance bounds -- this distinction is untestable without a network carrying switched shunt discrete step data (N1/B1 through N8/B8 fields). These are not edge cases; they are fundamental data model design differences that determine whether an analyst can work with production network data or must first transform it into a simplified representation.

## Precedent: Rubric v2 Scope Expansion

Rubric v2 expanded Phase 1's scope by adding supplementary sub-questions to the Expressiveness and Extensibility criteria. Specifically, v2 added Expressiveness sub-questions 9 (Security-Constrained OPF), 10 (Lossy DC OPF and LMP Decomposition), and 11 (Distributed Slack OPF), plus Extensibility sub-questions 8 (Reference Bus Control) and 9 (PTDF Matrix Extraction). These additions were motivated by research into ISO market clearing engines, which revealed that the original rubric's coverage of analytical primitives was insufficient for Phase 2 congestion pattern reproduction. A "Phase 2 Context" section was added to the rubric explaining this motivation.

The grading mechanism v2 established is directly relevant. The grading note after Expressiveness sub-question 11 states: "These sub-questions are supplementary Phase 2 readiness indicators. The original sub-questions (1--8) remain the primary drivers of the Expressiveness grade. Sub-questions 9--11 inform whether the tool is ready for ISO congestion pattern reproduction. A tool that scores well on 1--8 but poorly on 9--11 receives a grade note, not an automatic downgrade." This precedent establishes the pattern: scope expansion is permissible when it adds evidence that the original scope could not provide, as long as the new evidence informs rather than overrides existing grade boundaries.

The FNM amendment follows the identical pattern. FNM test results (Suite G) are supplementary production-network fidelity indicators. The original test suites (Suites A--F on synthetic cases) remain the primary drivers of Expressiveness and Extensibility grades. Suite G results inform whether the tool can handle production-scale data model complexity. A tool that passes Suites A--F but fails Suite G receives a grade note, not an automatic downgrade.

The v2 amendment was itself a scope expansion that could have been deferred to Phase 2: SCOPF and lossy DC OPF are directly relevant to ISO congestion reproduction, which is Phase 2's operational domain. The v2 amendment argued that *capability to express* SCOPF is a Phase 1 question, while *using* SCOPF for congestion reproduction is Phase 2. The same logic applies here: *capability to ingest* a production network is a Phase 1 data model fidelity question; *using* that network for market simulation is Phase 2.

## Grading Impact

FNM ingestion results inform the Expressiveness grade via a grading note under the existing Expressiveness criterion. The note documents a tool's ability to represent all PSS/E record types from a production network as evidence of expressiveness beyond what synthetic cases can test. Specifically, record-type coverage from Suite G gate tests demonstrates whether the tool's data model can hold the full complexity of a production network. Tools that ingest all Tier 1 and Tier 2 record types present in the FNM receive a positive grading note acknowledging production-network data model fidelity. Tools that fail to ingest Tier 1 record types present in the FNM -- for example, tools that cannot represent 3-winding transformers at all -- receive a negative grading note under Expressiveness documenting the gap and its tier classification. Neither note changes the A/B/C threshold definitions.

Supplemental CSV representability results inform the Extensibility grade via a grading note under the existing Extensibility criterion. The proportion of supplemental data that requires tool-external handling -- from the Phase 4 D2 representability summary -- directly indicates how much post-ingestion extension work an analyst faces when working with production data. This is a concrete, production-data-derived measurement of extensibility that complements the synthetic-case extension tests in Suite B.

FNM results do not inform Scalability (Suite G is not a performance benchmark), Accessibility (FNM ingestion difficulty is an Expressiveness question, not a usability question), Maturity, or Supply Chain grades. The FNM is tested only through the intermediate format, so raw PSS/E parsing capability is not graded.

Grade boundaries remain unchanged. The A/B/C threshold definitions for all six criteria remain exactly as written in rubric v3. No threshold is tightened, loosened, or conditioned on FNM results. The FNM grading notes operate within the existing evaluator judgment latitude that the rubric's +/- modifier system already provides. A grade of B+ versus B, for example, may be influenced by FNM evidence, but the boundary between B-range and C-range grades is not moved.

## FNM_PATH Gating

All Suite G (FNM Ingestion) tests are gated by the `FNM_PATH` environment variable. When `FNM_PATH` is unset, all Suite G tests skip with a clear message: "FNM data not available -- Suite G skipped." This is the same gating pattern used throughout the FNM expansion infrastructure established in Phase 1 D2.

A tool can receive complete Phase 1 grades on all six criteria based solely on Suites A--F results. FNM evidence is additive: its presence strengthens or weakens the grade narrative, but its absence does not create a gap, an incomplete grade, or a lower default score. An evaluation run without FNM data produces grades that are valid and complete on their own terms.

This means two evaluation runs of the same tool -- one with `FNM_PATH` set and one without -- may produce the same letter grade but different grade narratives. The run with FNM data has a richer evidence base that provides more granular insight into the tool's production-network capabilities. The run without FNM data is not penalized for the missing evidence; it simply has fewer data points informing the narrative.

The gating design also means that this rubric amendment has zero impact on evaluation runs that do not have access to FNM data. The amendment is forward-compatible: it adds capability for enriched evaluation when FNM data is available, without degrading evaluations that proceed without it. Organizations or analysts who do not have access to NDA-restricted FNM data can use the rubric v4 without any change to their evaluation workflow.

## Handling Synthetic-Pass / FNM-Fail Results

The scenario where a tool passes all synthetic-case tests (Suites A--F) but fails FNM ingestion (Suite G) is expected and informative, not anomalous. Synthetic cases use a simplified data format (MATPOWER .m) with a subset of record types. A tool optimized for .m ingestion may demonstrate strong synthetic performance but lack data model support for PSS/E-derived record types like 3-winding transformers or switched shunt discrete steps. This outcome reveals a real capability boundary that synthetic testing alone cannot expose.

The grade response depends on the failure mode. **Missing record type support** -- where the tool cannot represent a record type present in the FNM -- is an Expressiveness finding. The grade note documents which record types the tool cannot represent and their tier classification. A Tier 1 gap (e.g., cannot represent 3-winding transformers at all) is a stronger negative signal than a Tier 3 gap (e.g., cannot represent owner data). **Scale limitation** -- where the tool crashes or fails to converge on a ~30,000-bus network but handles the record types correctly on smaller subsets -- is a Scalability finding, not an Expressiveness finding. It is documented under Scalability, not Expressiveness. **Field coverage gap** -- where the tool ingests the record type but drops critical fields -- is a nuanced Expressiveness finding. The grade note references the field criticality tier of the dropped fields, distinguishing between DCPF-critical field loss (a severe finding) and Informational field loss (a minor finding).

In no case does a Suite G failure automatically downgrade a tool below the grade it would have received from Suites A--F alone. The Suite G results add resolution to the grade narrative -- they explain *why* a tool might struggle at production scale and *where* its data model has gaps -- but the A/B/C grade boundary is still determined by the synthetic-case evidence plus evaluator judgment. Suite G provides the evidence; the evaluator applies it within the existing grading framework.

## Cross-References

- **Phase 2 D2: Record-Type Mapping Guide** (`mapping-guide.md`) -- source for record type tier classifications (Tier 1/2/3) and tool support matrix (Y/P/N per tool per record type)
- **Phase 2 D5: Field Criticality Matrix** (`field-criticality-matrix.md`) -- source for field-level coverage gap analysis and DCPF-critical / ACPF-critical field counts
- **Rubric v4 Amendment** (`../../evaluation_guides/Phase1_Evaluation_Rubric.md`) -- the rubric that references this justification document
- **Rubric v2 grading note** -- Expressiveness sub-question 11 grading note in the current rubric (the precedent for supplementary Phase 2 readiness indicators)
- **Executive plan** (`../../plans/fnm-ingestion-expansion/executive-plan.md`) -- the plan that mandated this rubric amendment as part of the FNM ingestion expansion
