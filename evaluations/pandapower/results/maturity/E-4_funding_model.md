---
test_id: E-4
tool: pandapower
dimension: maturity
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 98f18435
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# E-4: Funding Model

## Result: INFORMATIONAL

## Finding

pandapower is dual-anchored in a German public university (University of Kassel) and a
Fraunhofer institute (Fraunhofer IEE), providing diversified funding through base
institutional support, contract research, and EU grants. No commercial entity monetizes
pandapower directly. Primary sustainability risk is institutional priority shift rather
than funding cessation.

## Evidence

### Institutional Backing

pandapower is developed by the **Department of Energy Management and Power System Operation
(e2n)** at the **University of Kassel**, Germany, in collaboration with **Fraunhofer IEE**
(Institute for Energy Economics and Energy System Technology), also in Kassel.

- **GitHub organization:** e2nIEE (combining e2n + IEE)
- **Core contributor affiliations (verified via GitHub profiles and publications):**
  - rbolgaryn (top lifetime contributor, 1,808 commits): Fraunhofer IEE / Uni Kassel
  - lthurner (2nd, 1,533 commits): Uni Kassel / Fraunhofer IEE
  - vogt31337 (3rd, 519 commits): Fraunhofer IEE
  - KS-HTK, heckstrahler, hilbrich, mrifraunhofer: Fraunhofer IEE affiliations

### Funding Structure

**Primary: German public research institutions**

1. **University of Kassel** — German public university funded by the state of Hesse and
   federal research grants (DFG, BMBF). Academic positions provide baseline funding for
   software maintenance as part of research activities.

2. **Fraunhofer IEE** — Part of Fraunhofer-Gesellschaft, Europe's largest application-oriented
   research organization. Operates on a mixed model: ~1/3 base government funding, ~2/3
   contract research and industry projects. This diversified model is more resilient than
   purely grant-funded academic projects.

**Secondary: EU and German research projects**

pandapower has been developed within multiple EU and German research projects related to
grid planning, distribution network automation, and energy system simulation. These grants
run 2-4 years each and provide targeted feature development funding.

### Funding Durability Assessment

| Factor | Assessment |
|--------|-----------|
| Institutional anchor | Strong — dual-anchored (university + Fraunhofer) |
| Funding diversity | Moderate-to-strong — base + contract + EU grants |
| Single-funder risk | Low — multiple funding mechanisms |
| Succession risk | Moderate — core knowledge concentrated in Kassel team |
| Commercial backing | None — no entity monetizing pandapower directly |
| Community sustainability | Moderate — 136 lifetime contributors, most unfunded |
| Ecosystem breadth | Strong — part of pandapipes, simbench, PandaModels ecosystem |

### Project Health Indicators

- 1,118+ GitHub stars, 556+ forks
- Used in research and industry across Europe
- The 2.x-to-3.0 major version transition (2025) demonstrates active long-term investment
- Multi-branch maintenance (backport releases) indicates production-grade project management

## Implications

pandapower benefits from one of the stronger funding models among academic open-source power
system tools. The Fraunhofer model is more resilient than pure grant-funded projects because
it does not depend on any single grant cycle. The primary risk is not funding cessation but
institutional priority shift: if e2n/Fraunhofer IEE pivots away from distribution-level power
system simulation, maintenance could decline. The absence of commercial backing means no risk
of license changes or commercial capture, but also no revenue-driven maintenance incentive
beyond research needs.
