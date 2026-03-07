---
test_id: E-4
tool: matpower
dimension: maturity
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-06T14:00:00Z"
---

# E-4: Funding Model

## Historical Funding

### PSERC / Cornell (1996-2024)
- MATPOWER was developed at the Power Systems Engineering Research Center (PSERC),
  an NSF Industry/University Cooperative Research Center hosted at Cornell University.
- Ray Zimmerman was a Senior Research Associate at Cornell, with MATPOWER
  development funded through his position.
- PSERC membership includes utilities and grid operators (historically: AEP, Exelon,
  PJM, EPRI, and others), providing indirect industry funding.

### NSF Grants
- Multiple NSF grants funded MATPOWER development over the years, including:
  - NSF awards for PSERC center operations
  - Specific grants for power systems optimization research
- **NSF funding has ended** — no active grants support MATPOWER development as of 2024.

### MathWorks
- MathWorks (maker of MATLAB) has provided some support for MATPOWER, primarily
  for the three-phase power flow extensions.
- This is a narrow scope of funding, not supporting core MATPOWER maintenance.

## Current Funding (2025-2026)

| Source | Status | Scope |
|--------|--------|-------|
| Cornell PSERC position | **Ended** (Zimmerman left mid-2024) | Was: full-time development |
| NSF grants | **Ended** | Was: research + development |
| MathWorks | **Limited** | Three-phase extensions only |
| Community donations | **None** | No donation mechanism exists |
| Paid support contracts | **None** | No commercial support offered |
| Corporate sponsorship | **None** | No visible sponsors |

## Assessment

**Funding model: Unfunded volunteer work.**

Since Zimmerman's departure from Cornell in mid-2024, MATPOWER development
appears to be unfunded volunteer work by the original author. There is:

- No donation mechanism (no Open Collective, GitHub Sponsors, etc.)
- No commercial entity behind the project
- No government contract funding
- No foundation affiliation (unlike NumFOCUS for many Python projects)

The continued commit activity (129 commits in 2025-2026) suggests personal
dedication rather than funded development.

## Durability Assessment

| Factor | Rating | Notes |
|--------|--------|-------|
| Financial sustainability | LOW | No revenue, no funding |
| Institutional backing | LOW | Former Cornell; no current institution |
| Community funding potential | LOW | Academic user base rarely funds tools |
| Fork viability | MODERATE | BSD license; clean codebase; but MATLAB/Octave ecosystem limits developer pool |

## Risk

The lack of any funding mechanism is a significant long-term risk. The project
depends entirely on Ray Zimmerman's personal motivation and availability. If he
stops contributing, there is no organizational or financial structure to sustain
development. The academic user base (750+ citations/year) has not translated into
financial support.
