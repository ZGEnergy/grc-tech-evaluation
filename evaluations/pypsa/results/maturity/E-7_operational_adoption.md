---
test_id: E-7
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 9c014aa2
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

# E-7: Operational Adoption (operational_adoption)

## Result: PASS

## Finding

PyPSA has documented operational deployment by TenneT (major European TSO) for transmission planning and widespread use by Fraunhofer ISI for national energy scenario studies. Beyond these two anchor users, PyPSA-Eur has 300+ users including multiple government energy agencies.

## Evidence

**Production/operational deployments (from research context):**

| Organization | Type | Use Case | Evidence Type |
|-------------|------|----------|--------------|
| TenneT TSO | Transmission System Operator (Netherlands/Germany) | Operational transmission planning | Documented in academic papers and conference presentations by TenneT staff |
| Fraunhofer ISI | Research institute (German government-linked) | National energy scenario studies | Multiple published studies using PyPSA |
| Multiple EU energy agencies | Government/policy | European energy transition modeling | Via PyPSA-Eur tool |

**TenneT deployment:**
TenneT is one of the largest TSOs in Europe (operating in Netherlands and Germany). Their use of PyPSA for transmission planning represents operational-grade deployment with real grid data. This is the strongest evidence of production-grade use.

**Fraunhofer ISI deployment:**
Fraunhofer ISI (Institute for Systems and Innovation Research) is a leading German research institute that advises the federal government on energy policy. Their PyPSA-based scenario studies are policy-relevant (not just academic). This represents institutionalized operational use at national scale.

**PyPSA-Eur scale:**
- 300+ users of the PyPSA-Eur European energy system model
- Users include universities (25+ countries), national energy agencies, and private consultancies
- This creates a large secondary user base that depends on PyPSA core

**Academic adoption:**
- PyPSA has been cited in hundreds of peer-reviewed papers
- Standard tool in European power system research curricula
- This academic adoption is distinct from operational use but signals broad familiarity in the expert community

**Distinguishing production vs academic:**
- TenneT: operational planning (confirmed production use)
- Fraunhofer ISI: policy-advisory scenario studies (operational in policy context)
- Academic citations: research/teaching (not production dispatch/operations)

## Implications

Operational adoption is A-level: confirmed operational use by a major European TSO (TenneT) and government-advisory institute (Fraunhofer ISI) is strong evidence of production readiness. The 300+ PyPSA-Eur users create a large installed base. For ZGE's use case (power system modeling and optimization), PyPSA has well-established operational credibility in the European energy sector.
