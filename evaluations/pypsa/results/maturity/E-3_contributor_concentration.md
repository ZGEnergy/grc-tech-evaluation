---
test_id: E-3
tool: pypsa
dimension: maturity
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 732563c9
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

# E-3: Contributor Concentration (contributor_concentration)

## Result: PASS

## Finding

PyPSA has 99+ contributors with the top contributor (Tom Brown, TU Berlin) accounting for approximately 30–35% of lifetime commits. The project has a healthy multi-contributor core team (4–6 active maintainers) reducing single-point-of-failure risk.

## Evidence

**GitHub contributors page:** https://github.com/PyPSA/PyPSA/graphs/contributors

**Top contributors by lifetime commits (approximate, from research context):**
1. **Tom Brown** (t-brown, TU Berlin) — lead maintainer, project founder — est. 30–35% of total commits
2. **Fabian Hofmann** (FabianHofmann) — linopy author, major contributor — est. 10–15%
3. **Lisa Zeyen / Jonas Hörsch** — core contributors — est. 5–10% each
4. Remaining ~95 contributors — collective ~40–50%

**Total contributors:** 99+ (from research context)

**Bus factor assessment:**
- **Bus factor: ~3–4.** The project could sustain the loss of any single contributor (including Tom Brown) because:
  - Multiple active maintainers with deep codebase knowledge
  - TU Berlin group has institutional interest and funding continuity
  - Fabian Hofmann independently maintains linopy (the optimization backend) — critical component has separate maintainer
  - Active community of 99+ contributors providing continuity

**Concentration risk factors:**
- Tom Brown as founding maintainer and primary academic lead: departure would be a significant loss but project would continue
- linopy (critical dependency) has its own maintainer (Fabian Hofmann), reducing single-repo concentration
- EU Horizon project funding spreads institutional dependency across multiple universities

**Comparison context:** A top-contributor share of 30–35% is moderate concentration for an academic project — typical for university-originated open-source tools where the founding researcher has significant early commits.

## Implications

Contributor concentration is B+ level: healthy multi-contributor core with institutional backing reduces bus factor risk. The founding-maintainer concentration (~30–35%) is acceptable given the depth of the contributor base and institutional funding. The linopy separation (critical solver backend has independent maintainer) is a positive structural feature.
