---
test_id: E-4
tool: pandapower
dimension: maturity
network: N/A
status: informational
workaround_class: null
timestamp: "2026-03-13T00:00:00Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "98f18435"
---

# E-4: Funding Model — pandapower

## Sub-criterion
5b (Sustainability Risk)

## Method
Researched pandapower's institutional backing, affiliations of core contributors, and funding
sources through the project's documentation, GitHub organization, and published papers.

## Institutional Backing

pandapower is developed and maintained by the **Department of Energy Management and Power System
Operation (e2n)** at the **University of Kassel**, Germany, in collaboration with the
**Fraunhofer Institute for Energy Economics and Energy System Technology (Fraunhofer IEE)**,
also located in Kassel.

- **GitHub organization:** e2nIEE (combining e2n + IEE)
- **Primary institutional affiliations of core contributors:**
  - rbolgaryn (top contributor, 1,808 commits): Fraunhofer IEE / University of Kassel
  - lthurner (2nd contributor, 1,532 commits): University of Kassel / Fraunhofer IEE
  - vogt31337 (3rd contributor, 518 commits): Fraunhofer IEE
  - KS-HTK (4th contributor, 403 commits): affiliated with the same research group
  - heckstrahler, hilbrich, mrifraunhofer: Fraunhofer IEE affiliations evident from usernames

## Funding Structure

### Primary funding: German public research institutions

1. **University of Kassel** — German public university. Funding comes from the state of Hesse
   and federal German research grants (DFG, BMBF). Academic positions provide baseline
   funding for software maintenance as part of research activities.

2. **Fraunhofer IEE** — Part of the Fraunhofer-Gesellschaft, Europe's largest application-oriented
   research organization. Fraunhofer institutes operate on a mixed-funding model: approximately
   one-third base funding from German federal and state governments, two-thirds from contract
   research and industry projects. This gives Fraunhofer IEE a more durable and diversified
   funding base than a purely grant-funded academic project.

### Secondary funding: EU and German research projects

pandapower has been developed within and funded by multiple EU and German research projects,
including projects related to grid planning, distribution network automation, and energy
system simulation. These grants typically run 2-4 years each and provide targeted funding
for feature development.

### Community and industry adoption

- **1,118 GitHub stars**, **556 forks** as of March 2026
- Used in research and industry across Europe
- Part of a broader ecosystem including pandapipes (fluid networks) and simbench
  (benchmark grids)
- The breadth of adoption creates institutional incentive to maintain the project

## Funding Durability Assessment

| Factor | Assessment |
|--------|-----------|
| Institutional anchor | Strong — dual-anchored in a public university and a Fraunhofer institute |
| Funding diversity | Moderate-to-strong — base funding + contract research + EU grants |
| Single-funder risk | Low — multiple funding sources across different mechanisms |
| Succession risk | Moderate — core knowledge concentrated in Kassel-based team |
| Commercial backing | None — no commercial entity monetizing pandapower directly |
| Community sustainability | Moderate — 183 lifetime contributors, but most are not funded to maintain it |

## Analysis

pandapower benefits from one of the stronger funding models among academic open-source power
system tools. The Fraunhofer model (base + contract + industry funding) is more resilient
than pure grant-funded academic projects because it does not depend on any single grant cycle.
The University of Kassel provides additional stability through PhD and postdoc positions whose
research involves pandapower development.

The primary risk is not funding cessation but rather **institutional priority shift**: if the
e2n department or Fraunhofer IEE pivots away from distribution-level power system simulation,
maintenance could decline even with funding available. The 2.x-to-3.0 major version transition
in 2025 suggests the project is actively investing in long-term viability, not just
maintenance-mode patching.

The absence of commercial backing (no company selling pandapower support or hosting) is a
double-edged factor: it means no risk of commercial capture or license changes, but also no
revenue-driven incentive to maintain the software beyond research needs.

## Assessment

Strong institutional backing with diversified funding through the Fraunhofer/University of
Kassel partnership. Funding durability is above average for academic open-source tools. Primary
sustainability risk is institutional priority shift rather than funding cessation.
