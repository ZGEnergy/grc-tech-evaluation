---
tag: api-friction
dimension: scalability
test_id: C-5
tool: pandapower
network: SMALL
timestamp: "2026-03-13T00:00:00Z"
---

# API Friction: Convergence diagnostics require private attributes

pandapower's ACPF solver (`runpp`) reports convergence via the public `net.converged` boolean flag, but detailed diagnostics require accessing private internal state:

- **NR iteration count:** accessible only via `net._ppc["iterations"]` (underscore-prefixed private attribute)
- **Convergence residual:** not stored anywhere after solve completes; the solver checks against `tolerance_mva` internally but does not record the final mismatch value

This is consistent with the A-2 (ACPF on TINY) finding. The diagnostic quality limitation does not affect pass conditions but reduces observability for scalability analysis. For comparison, tools like MATPOWER expose both iteration count and final mismatch as standard output fields.
