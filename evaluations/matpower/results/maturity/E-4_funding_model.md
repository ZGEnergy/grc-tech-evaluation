---
test_id: E-4
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "f10d978b"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# E-4: Funding Model

## Result: INFORMATIONAL

## Finding

MATPOWER's historical funding model (government grants through Cornell University) has ended. The primary maintainer retired from Cornell in mid-2024. Current funding is limited to a MathWorks Community Toolbox sponsorship for 3-phase features. A commercial venture is in exploratory stages. The funding model is in transition and carries meaningful sustainability risk.

## Evidence

### Historical funding sources

From the MATPOWER acknowledgments page (https://matpower.org/acknowledgments/, accessed 2026-03-14):

1. **PSERC (Power Systems Engineering Research Center)** -- Primary research consortium funding throughout MATPOWER's 25+ year history
2. **U.S. Department of Energy** -- Through CERTS and the Office of Electricity Delivery and Energy Reliability (Cooperative Agreement DE-FC26-09NT43321)
3. **National Science Foundation** -- Grants 0532744, 1642341, and 1931421
4. **ARPA-E** -- GRID DATA program for synthetic power grid data

### Current funding status

From the "Transition for Ray, and the Future of MATPOWER" blog post (https://matpower.org/2024/12/03/transition-for-ray-and-the-future-of-matpower/, published 2024-12-03):

- **NSF funding ended.** Zimmerman states: "Unfortunately, that door is now closed" regarding hoped-for NSF support for distribution systems and hybrid AC/DC grid modeling.
- **Cornell affiliation ended.** Zimmerman retired from Cornell mid-2024, eliminating the institutional home that enabled grant-funded development.
- **MathWorks sponsorship.** The MathWorks MATLAB Community Toolbox program provides current support for 3-phase modeling features. Scope and duration are not publicly disclosed.
- **Commercial venture (exploratory).** Zimmerman is exploring "a commercial venture to offer MATPOWER-related software and services for a fee." This is described as being in early exploratory phases and could potentially serve as a "long-term home for the open-source project."
- **PAS employment.** Zimmerman is now full-time at Power Analytics Software, Inc. (PAS) as lead optimization engineer. It is unclear how much of his PAS time is allocated to open-source MATPOWER work.

### Institutional affiliation

- **Historical:** Cornell University, PSERC consortium
- **Current:** Power Analytics Software, Inc. (PAS) -- a private company, not an academic or government institution

### Grant dependency assessment

MATPOWER was historically ~100% dependent on government/academic grants. All identified funding sources (NSF, DOE, ARPA-E, PSERC) have terminated or are not currently active. The project has no known endowment, foundation, or recurring corporate sponsorship beyond the MathWorks arrangement.

## Implications

The funding transition is the second-largest maturity risk after contributor concentration (E-3). The project moved from a well-funded academic model (multiple government grants, institutional home at Cornell) to an uncertain model dependent on one person's employer goodwill and exploratory commercial plans. For a production dependency, the risk is that MATPOWER development could slow or stop if the commercial venture does not materialize and if PAS does not allocate Zimmerman's time to open-source work. The 8.1 release (July 2025) demonstrates continued investment post-transition, but the long-term sustainability model is unproven.
