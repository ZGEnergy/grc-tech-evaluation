---
test_id: E-4
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 39349d2d
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# E-4: Funding Model (funding_model)

## Result: PASS

## Finding

PyPSA has robust, multi-source institutional funding from TU Berlin, the Reiner Lemoine Institut (RLI), EU Horizon projects, and KIT. The energy transition policy relevance of the tool ensures continued funding interest from European research and government bodies.

## Evidence

**Known institutional backers (from research context):**

| Funder | Type | Role |
|--------|------|------|
| TU Berlin (Chair of Digital Transformation in Energy Systems) | University | Primary host institution; Tom Brown's group |
| Reiner Lemoine Institut (RLI) | Non-profit research | Active development and use |
| EU Horizon Projects | EU research funding | Multiple grants (e.g., PyPSA-Eur, sector-coupling studies) |
| KIT (Karlsruhe Institute of Technology) | University | Research contributions |

**PyPSA-Eur (companion project):**
PyPSA-Eur (https://github.com/PyPSA/pypsa-eur) is an EU-scale power system optimization model built on PyPSA. It has received dedicated EU Horizon funding and has 300+ users. This creates a strong pull for continued PyPSA core development — PyPSA-Eur's users depend on PyPSA being maintained.

**Funding durability assessment:**
- EU energy transition policy (Green Deal, REPowerEU) drives continued demand for PyPSA-style tools
- Multiple independent funding sources reduce single-funder dependency
- Academic group continuity: TU Berlin Chair is a stable institutional base (professorial position)
- Industry users (TenneT, Fraunhofer ISI) provide demand signal even without direct funding

**Open questions:**
- No GITHUB SPONSORS or OpenCollective page found — primary funding is through grants, not community donations
- Dependency on EU Horizon grants means funding is project-cycle (typically 3–5 year grants) — gaps between grants are possible but manageable with multi-funder model

**Commercial interest:**
- TenneT (major European TSO) uses PyPSA for operational planning — creates industry adoption momentum
- Fraunhofer ISI uses PyPSA for scenario studies — research institute adoption provides stable user base

## Implications

Funding model is A-level for an academic open-source tool. Multi-source institutional backing, direct policy relevance to European energy transition, and a companion application project (PyPSA-Eur) that depends on PyPSA core provide strong durability signals. The grant-based funding model introduces some multi-year cycle risk, but this is mitigated by the breadth of funders and industry adopters.
