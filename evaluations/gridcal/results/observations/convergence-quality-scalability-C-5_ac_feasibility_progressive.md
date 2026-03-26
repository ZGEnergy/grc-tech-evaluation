---
tag: convergence-quality
source_dimension: scalability
source_test: C-5
tool: gridcal
severity: medium
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: DCOPF dispatch convergence varies by network scale

## Finding

On the ACTIVSg 2000-bus (SMALL) network, fixing generator dispatch to the DCOPF solution
and running ACPF results in NR convergence failure across all solver algorithms. On the
ACTIVSg 10000-bus (MEDIUM) network, the same workflow converges successfully in 5 NR
iterations with residual 4.818e-07 p.u. (well below the 1e-4 threshold).

## Context

**SMALL (C-5 SMALL):** Seven convergence strategies failed (flat start, DC warm start,
relaxed tol 1e-4, relaxed tol 1e-3, HELM, Iwamoto, LM) -- all producing an identical
residual of ~1.45e-3. Direct ACPF with base-case generator setpoints converges
excellently in 6 iterations (residual 7.385e-13).

**MEDIUM (C-5 MEDIUM):** Flat start with DCOPF-fixed dispatch converges in 5 NR
iterations with residual 4.818e-07. The progressive relaxation assessment finds the
operating point infeasible at all levels (0%, 10%, 20%) due to 18 persistent thermal
violations and 46-132 voltage violations.

The reversal is counterintuitive -- the larger network produces a more AC-tractable
operating point from DCOPF dispatch. This likely reflects network topology and generation
distribution differences rather than a scaling property.

## Implications

This finding is relevant to the Accessibility dimension: the DCOPF-to-ACPF feasibility
check workflow produces inconsistent results across network scales. Users cannot predict
whether DCOPF dispatch will create an AC-convergent operating point on a new network.
GridCal provides no diagnostic to help users distinguish between "solver failure" and
"operating point is AC-infeasible." This behavior is likely tool-independent but
GridCal's lack of Ipopt integration means no alternative NLP solver approach is available.
