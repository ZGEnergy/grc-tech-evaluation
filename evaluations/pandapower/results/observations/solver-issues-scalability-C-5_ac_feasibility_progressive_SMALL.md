---
tag: solver-issues
dimension: scalability
test_id: C-5
tool: pandapower
network: SMALL
timestamp: "2026-03-13T00:00:00Z"
---

# Solver Observation: C-5 ACPF on SMALL converges easily

pandapower's internal Newton-Raphson solver converged on the ACTIVSg2000 (2000-bus) network in 4 iterations at 0% thermal relaxation using a DC warm start. No progressive relaxation was needed.

Key findings:
- **No external NLP solver required** -- pandapower uses its own NR implementation, not Ipopt
- **Convergence residual not extractable** -- the final power mismatch is not exposed through a public API attribute; only the `tolerance_mva` threshold and `net.converged` flag are available
- **NR iteration count available** only via private attribute `net._ppc["iterations"]`
- **All voltages within [0.95, 1.05] pu** -- no relaxation needed for voltage feasibility
- **Max line loading 82.7%** -- well below thermal limits

The ACTIVSg2000 network is a well-conditioned test case that converges readily. This bodes well for MEDIUM tier testing but provides limited diagnostic signal about solver robustness under stress.
