# PowSyBl Phase 1 Inclusion Assessment

_Research date: 2026-03-30_
_Purpose: Determine whether PowSyBl should be added to the Phase 1 tool evaluation_

## Executive Summary

PowSyBl is the most production-deployed open-source power systems framework in Europe,
backed by RTE (French TSO), hosted under LF Energy, and operationally serving 30+ TSOs
via the European Merging Function. It excels at load flow, security analysis, sensitivity
analysis, and remedial action optimization at continental scale (120k+ buses).

**Recommendation: Do not include PowSyBl in Phase 1.**

Despite its maturity and scale, PowSyBl has critical gaps in the problem types central
to this evaluation's rubric. It cannot express SCUC, general-purpose DCOPF with LMP
extraction, stochastic optimization, multi-period OPF with storage, lossy DCOPF, or
LMP decomposition. These are not peripheral sub-questions -- they are the core of
Criterion 1 (Problem Expressiveness), which is the highest-weighted criterion after the
gate. PowSyBl would receive a **Weak** or **Failing** Expressiveness grade under the
current rubric, which would disqualify it from Phase 2 consideration regardless of its
strengths elsewhere.

PowSyBl is an excellent tool for a different evaluation question ("which tool best
supports European TSO operational security workflows?"). It is not the right tool for
this evaluation's question ("which tool best supports US ISO market clearing and
congestion pattern reproduction?").

---

## Criterion-by-Criterion Assessment

### Criterion 6 — Supply Chain, Inspectability & Licensing (Gate)

**Projected tier: Strong**

| Factor | Assessment |
|--------|-----------|
| License | MPL-2.0 (weak copyleft, OSI-approved). Compatible with classified deployment. |
| Source availability | Fully open. ~50 repos under github.com/powsybl/. |
| Build reproducibility | Maven wrapper, CI on 3 platforms, standard Java tooling. |
| Artifact signing | Published to Maven Central (PGP-signed). pypowsybl on PyPI. |
| Solver dependencies | Default stack is fully open-source (Open Load Flow + KLU). Knitro and AMPL are optional, not required. |
| Native dependencies | KLU sparse solver (LGPL-2.1+). pypowsybl bundles GraalVM native image (no JVM needed at runtime). |
| Inspectability | Entire execution stack is source-available. Legacy proprietary solver (Hades2) archived April 2024; replaced by Open Load Flow. |
| Governance | LF Energy (Linux Foundation Europe). Formal TSC, release manager. |

The one nuance: GraalVM native image compilation for pypowsybl produces a binary blob
that is not directly inspectable at the Java source level. Users must trust the build
pipeline or rebuild from source. This is analogous to compiled C extensions in Python
packages and would not be disqualifying.

**Gate: PASS**

---

### Criterion 1 — Problem Expressiveness (Priority 1)

**Projected tier: Weak**

| Sub-question | Support | Evidence |
|---|---|---|
| 1. DC Power Flow | **Yes** | `powsybl-open-loadflow` DC solver. Bus angles, branch flows, slack mismatch exposed. |
| 2. AC Power Flow | **Yes** | Full Newton-Raphson with KLU. Convergence status, iteration count, slack info returned. Three NR update methods. |
| 3. DC OPF | **Partial** | `powsybl-metrix` does SC-DCOPF for _redispatching cost minimization_, not general-purpose DCOPF with LMP extraction. No standalone "minimize generation cost, return LMPs" API. |
| 4. AC PF on DC OPF result | **Yes** | Composable via shared IIDM model (run Metrix, then run Open LoadFlow AC). Manual two-step. |
| 5. SCUC | **No** | No unit commitment formulation anywhere in the ecosystem. No MILP with min up/down, startup costs, ramp rates, reserves. Metrix assumes fixed commitment. |
| 6. SCED | **Partial** | Metrix redispatching is functionally similar but framed as European remedial action, not US-style SCED with warm-started dispatch from commitment schedule. |
| 7. N-M Contingency Sweep | **Yes** | One of PowSyBl's strongest capabilities. AC/DC security analysis with parallel contingency processing. Contingency DSL (Groovy). Remedial action support. |
| 8. Stochastic Optimization | **No** | Metrix runs deterministic scenarios in a loop. No two-stage stochastic programs, scenario trees, or chance-constrained formulations. |
| 9. SCOPF | **Partial** | Metrix SC-DCOPF enforces N-k security constraints inside the optimization (genuine preventive SCOPF in DC). Open RAO adds curative RA optimization. No AC SCOPF. |
| 10. Lossy DCOPF + LMP Decomposition | **No** | No loss approximation in DC OPF. No LMP decomposition (energy/congestion/loss). PTDF sensitivity factors exist but no automated LMP workflow. |
| 11. Distributed Slack OPF | **Partial** | Distributed slack in PF (proportional to gen/load). Not exposed as OPF parameter. |
| 12. Multi-period DCOPF with Storage | **No** | No inter-temporal optimization. Metrix processes each timestep independently. IIDM has battery elements but no SoC optimization. |

**5 of 12 sub-questions are No. 3 are Partial (in the wrong direction for US market workflows).**

The tool would fail sub-questions 5, 8, 10, and 12 outright. Sub-questions 3, 6, 9,
and 11 would be partial_pass at best -- the Metrix SC-DCOPF is designed for European TSO
remedial action optimization, not US ISO market clearing with LMP extraction.

Under the rubric's assessment standards, "multiple target problem types require significant
manual effort or are partially outside the tool's design scope" maps to **Weak**. The
complete absence of SCUC, stochastic optimization, and LMP decomposition arguably
approaches **Failing** ("a target problem type is outside the tool's design scope entirely").

**This is the disqualifying finding.** PowSyBl was designed for European TSO operational
security, not US ISO market simulation. The rubric's Expressiveness criterion is built
around the US market clearing workflow (SCUC -> SCED -> LMP decomposition -> SCOPF),
which is fundamentally outside PowSyBl's scope.

---

### Criterion 2 — Extensibility (Priority 2)

**Projected tier: Strong**

Despite the Expressiveness gaps, PowSyBl's architecture is genuinely excellent:

| Factor | Assessment |
|--------|-----------|
| Plugin system | Formal Java SPI throughout. 50+ Maven modules with clean API/impl separation. |
| Custom constraints | OpenReac (AMPL-editable OPF), custom outer loops via SPI, Open RAO configurable search-tree. |
| Network graph access | Three topology views (node-breaker, bus-breaker, bus-branch). `traverse()` for DFS. |
| Data model flexibility | Key-value properties + typed extensions on all Identifiable elements. |
| Interoperability | Broadest format coverage: CIM-CGMES, PSS/E RAW v33/v35, MATPOWER, UCTE, IEEE CDF, PowerFactory. |
| Result extraction | In-place network update + typed result objects. Pandas DataFrames in Python. |
| Scripting | Java (primary), Python (pypowsybl), Groovy DSL, REST, CLI. |

An analyst _could_ theoretically build SCUC, LMP decomposition, and stochastic
optimization on top of PowSyBl's primitives. But this is the "heroics" the rubric
explicitly excludes: "hybrid stacks assembled by the evaluator from independently
maintained tools are not evaluated."

---

### Criterion 3 — Scalability (Priority 3)

**Projected tier: Strong**

| Factor | Assessment |
|--------|-----------|
| Max tested scale | 120,000+ buses. Production-deployed on full European transmission model. |
| PF performance | IEEE 300: 3.5ms, RTE 6515: 118ms (single-core). Competitive with all tools in evaluation. |
| Security analysis | 5-29ms per contingency on 6515-bus network. |
| Metrix throughput | RTS-GMLC annual scenario (8,760 hours) in 35 seconds. |
| Parallelism | Multi-threaded contingency processing. HPC module (Slurm, MPI). Tested on 10,000-core cluster. |
| Memory | JVM-managed. Handles 120k+ bus networks. |

PowSyBl's scalability is in a different league from the academic tools. However, the
scalability advantage is irrelevant if the tool cannot express the problem types we need.

---

### Criterion 4 — Workforce Accessibility (Priority 4)

**Projected tier: Adequate**

| Factor | Assessment |
|--------|-----------|
| Python access | pypowsybl v1.14.0, `pip install pypowsybl`, no JVM needed. Production/Stable on PyPI. |
| pypowsybl coverage | Load flow, security, sensitivity, short-circuit, RAO, dynamic sim, flow decomposition. OPF and HPC are Java-only. |
| DataFrame integration | Network elements returned as Pandas DataFrames. Idiomatic Python. |
| Documentation | ReadTheDocs site, Jupyter notebooks, tutorials repo. Assumes domain knowledge. |
| Error messages | Java stack traces through GraalVM can be opaque. |
| Community | Small, European-TSO-centric. Slack workspace. ~440k PyPI downloads total. |
| Learning curve | Moderate. IIDM conceptual model has its own learning curve. European TSO framing may confuse US-market analysts. |

The Java barrier is real but pypowsybl mitigates it for standard workflows. The
bigger accessibility concern for this project is conceptual: PowSyBl's vocabulary
(remedial actions, flow-based capacity calculation, GLSK, CRAC files) is European TSO
terminology that doesn't map to US ISO concepts.

---

### Criterion 5 — Maturity & Sustainability (Priority 5)

**Projected tier: Strong**

| Factor | Assessment |
|--------|-----------|
| Project age | ~8 years (2017 iTesla origins, 2018 first open-source release). |
| Release cadence | Quarterly minor releases, patch releases as needed. Currently v7.2.0. 134 tags. |
| Contributors | 112 on powsybl-core. Multi-org but RTE-dominated. |
| Governance | LF Energy TSC, 9 voting members. Formal release manager. |
| CI/CD | GitHub Actions on Ubuntu/Windows/macOS. JaCoCo + SonarCloud. |
| Security | OpenSSF Best Practices silver badge. Security audit completed 2024. |
| Production users | RTE, Elia, CORESO, TSCNET, Baltic RCC, SeleneCC (30+ TSOs indirectly). |
| Funding | RTE-funded development. LF Energy governance. Artelys contributes under contract. |

**Risk factor:** RTE concentration. All TSC seats are RTE employees. If RTE deprioritizes
PowSyBl, the project loses its primary developer base. The LF Energy governance provides
structural protection but not development capacity.

---

## Solver Compatibility

| Solver | PowSyBl Support | Phase 1 Required |
|--------|----------------|-----------------|
| HiGHS | **No** | Yes (primary LP/MILP) |
| SCIP | **No** | Yes (secondary MILP) |
| Ipopt | **Indirect** (via AMPL in OpenReac) | Yes (NLP) |
| GLPK | **No** | Yes (baseline) |
| KLU | **Yes** (default sparse solver) | N/A (not in solver stack) |
| Sirius | **Yes** (Metrix LP/MIP) | N/A (not in solver stack) |
| Knitro | **Optional** (commercial) | N/A (commercial, excluded) |

PowSyBl cannot interface with any of the four open-source solvers required by the Phase 1
protocol. This would be recorded as a finding under both Supply Chain (solver lock-in)
and Scalability (solver flexibility). The Sirius solver used by Metrix is open-source
(Apache 2.0) but is RTE's own implementation, not a standard solver in the evaluation's
solver stack.

---

## Format Compatibility

| Format | PowSyBl | Phase 1 Required |
|--------|---------|-----------------|
| MATPOWER .m | **No** (.mat binary only) | Yes (primary reference format) |
| MATPOWER .mat | **Yes** | Requires Octave/MATLAB conversion step |
| PSS/E RAW | **Yes** (v33, v35) | Useful for Phase 2 FNM |
| CIM-CGMES | **Yes** (strongest in ecosystem) | Not required |
| IEEE CDF | **Yes** | Not required |

PowSyBl cannot directly ingest the `.m` case files used in Phase 1 testing. The MATPOWER
importer reads `.mat` (binary MATLAB) format, requiring a conversion step via Octave.
This is a friction point but not disqualifying.

---

## Comparison with Current Phase 1 Tools

| Capability | PowSyBl | PyPSA | pandapower | PowerModels | PowerSims | GridCal | MATPOWER |
|-----------|---------|-------|------------|-------------|-----------|---------|---------|
| DCPF | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| ACPF | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| DCOPF + LMPs | Partial | Yes | Yes | Yes | Yes | Yes | Yes |
| SCUC | **No** | Yes | No | Yes* | Yes | No | No |
| SCED | Partial | Yes | No | Yes* | Yes | No | No |
| SCOPF | Partial | No | No | Yes | No | No | Yes |
| Stochastic | **No** | Yes | No | No | Yes | No | No |
| Lossy DCOPF | **No** | No | No | Yes | No | No | Yes |
| LMP Decomposition | **No** | No | No | Yes | No | No | Yes |
| Contingency sweep | **Strong** | Weak | Yes | Yes | Yes | Yes | Yes |
| Scale (max buses) | **120k+** | ~10k | ~10k | ~10k | ~10k | ~10k | ~30k |
| PSS/E RAW import | **Yes** | No | No | No | No | No | No |

PowSyBl's unique strengths (scale, PSS/E import, contingency analysis, CIM-CGMES) are
precisely the capabilities needed for Phase 2 FNM work but are not the capabilities
tested by the Phase 1 rubric's weighted criteria.

---

## Phase 2 Relevance

While PowSyBl is not appropriate for Phase 1, several capabilities make it potentially
valuable for Phase 2 work:

1. **PSS/E RAW v33/v35 import** — Native parsing of the FNM's source format. No other
   tool in the evaluation can do this.
2. **CIM-CGMES** — If ISO data becomes available in CIM format, PowSyBl is the
   strongest open-source importer.
3. **Security analysis at scale** — Parallel N-k contingency processing on 120k+ bus
   networks, with remedial action optimization.
4. **European TSO validation** — The production deployment across 30+ TSOs provides
   confidence in correctness at scale.

A Phase 2 architecture could use PowSyBl for network import, topology management,
and security analysis while using a different tool (PowerModels, PyPSA) for market
clearing and LMP computation. This is explicitly a "hybrid stack" that the Phase 1
rubric excludes, but Phase 2 has different rules.

---

## Conclusion

PowSyBl is a mature, well-engineered, production-grade power systems framework. It
passes the supply chain gate easily and would score Strong on extensibility, scalability,
and maturity. However, it would receive Weak or Failing on Problem Expressiveness --
the highest-weighted criterion -- because its design scope (European TSO operational
security) does not overlap with the Phase 1 rubric's core problem types (US ISO market
clearing workflow: SCUC, SCED, LMP decomposition, stochastic optimization).

Including PowSyBl in Phase 1 would:
- Consume evaluation resources on a tool that cannot compete on the primary criterion
- Produce a misleadingly low overall grade for a genuinely excellent tool
- Not change the Phase 1 recommendation (the tool would rank last on Expressiveness)

The right action is to **note PowSyBl as a Phase 2 resource** for PSS/E import,
security analysis, and scale validation, while excluding it from the Phase 1 comparative
evaluation.
