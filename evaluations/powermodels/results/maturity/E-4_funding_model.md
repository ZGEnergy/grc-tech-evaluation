---
test_id: E-4
tool: powermodels
dimension: maturity
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "d33b1613"
---

# E-4: funding_model

## Finding

PowerModels.jl is developed at Los Alamos National Laboratory (LANL) under the Advanced Network Science Initiative (ANSI), a program of the U.S. Department of Energy (DOE). This constitutes stable, long-term federal institutional backing. The project is not dependent on a single grant cycle.

## Evidence

### README acknowledgment (verbatim):
> "This code has been developed as part of the Advanced Network Science Initiative at Los Alamos National Laboratory. The primary developer is Carleton Coffrin (@ccoffrin)..."

#### Institutional details:
- **LANL:** Los Alamos National Laboratory — a DOE national laboratory operated by Triad National Security, LLC. Annual budget ~$4B. Core mission includes energy and national security research.
- **ANSI (Advanced Network Science Initiative):** LANL research program focused on complex networks, including power grid analysis. Not a single-year grant but an ongoing research initiative.
- **Primary developer:** Carleton Coffrin, staff scientist at LANL. Employment continuity is institutional, not grant-dependent.

#### Secondary institutional connections noted in contributor list:
- Russell Bent (@rb004f) — LANL (multiple LANL staff contributors)
- Kaarthik Sundar (@kaarthiksundar) — LANL
- David Fobes (@pseudocubic) — LANL

**External collaborators (academic institutions):** KU Leuven, MIT, UC Berkeley, Georgia Tech, CSIRO — contributors but not funders.

**Co-authoring organization:** The NREL-Sienna ecosystem (PowerSystems.jl, PowerSimulations.jl) is a related DOE-NREL project that leverages and cross-contributes to PowerModels.jl.

**DOE adoption signals:** PowerModels.jl is listed as infrastructure for multiple DOE grid modernization projects. The tool is used in publications by national lab researchers at LANL, NREL, Argonne, and Pacific Northwest National Laboratory.

**Grant dependency:** Low. LANL/DOE national labs maintain multi-year baseline funding. Even if specific grant projects end, the institution supports continued maintenance.

**Durability assessment:** High — federal national laboratory backing provides multi-decade institutional stability. The primary risk is not funding discontinuation but rather reduced prioritization if LANL's power grid research focus shifts.

## Implications

LANL/DOE institutional backing is among the strongest possible funding models for an open-source scientific tool. The project is not at risk of sudden abandonment due to a grant expiration. The durability concern is long-term organizational alignment rather than near-term funding gaps. This is a strong positive maturity signal.
