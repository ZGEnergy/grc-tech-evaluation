---
test_id: C-2
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 2.516
peak_memory_mb: 346.6
loc: 149
solver: "Newton-Raphson (internal)"
timestamp: 2026-03-06T00:00:00Z
---

# C-2: ACPF at scale

## Result: PASS

## Approach

Loaded the ACTIVSg10k (~10,000-bus) MEDIUM network. Applied the convergence protocol: attempted flat start first (all voltages 1.0 pu, all angles 0.0 rad), then fell back to DC warm start when flat start did not converge within 100 iterations.

**Solver deviation:** The eval-config specifies "Ipopt" but pandapower uses its own internal Newton-Raphson implementation for AC power flow. There is no option to swap to Ipopt for `pp.runpp()`. This is inherent to the tool's architecture.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Flat start converged | No (100 iterations exhausted) |
| DC warm start converged | Yes |
| Vm max | 1.0814 pu |
| Vm min | 0.8682 pu |
| Va max | 15.69 deg |
| Va min | -92.41 deg |
| Total P loss (lines) | 2,446.3 MW |
| Total P loss (trafos) | 152.4 MW |

## Workarounds

- **What:** DC warm start required for convergence
- **Why:** Flat start (standard initialization) did not converge within 100 NR iterations on the 10,000-bus network
- **Durability:** stable -- DC warm start is a well-documented, standard fallback
- **Grade impact:** Minor finding. Flat start failure on MEDIUM networks is common and expected for many tools.

## Timing

- **Wall-clock:** 2.516 s (total including load and flat start attempt)
- **Flat start attempt:** 2.084 s (did not converge)
- **DC warm start solve:** 0.105 s
- **Network load time:** 0.285 s
- **Peak memory:** 346.6 MB
- **CPU user time:** 6.08 s

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c2_acpf_scale.py`
