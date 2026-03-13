---
test_id: A-2
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 97f53d76
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.149
timing_source: measured
peak_memory_mb: null
convergence_residual: 3.317e-09
convergence_iterations: 4
loc: 185
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-2: AC Power Flow (acpf)

## Result: PASS

## Approach

Loaded IEEE 39-bus case39.m (same pipeline as A-1). Ran Newton-Raphson AC power flow via `n.pf()` from flat start (default — all buses initialized at 1.0 pu, 0 angle). `n.pf()` returns a `pypsa.definitions.structures.Dict` with keys `n_iter`, `error`, `converged` — each value is a DataFrame of shape (1 snapshot × 1 subnetwork). Convergence data extracted via `pf_result["n_iter"].values[0, 0]` and `pf_result["error"].values[0, 0]`.

Flat start converged in 4 Newton-Raphson iterations with final mismatch of 3.32×10⁻⁹ (well below the default tolerance of 1×10⁻⁶). No DC warm start fallback was needed.

## Output

**Convergence:**
- Converged: True (flat start)
- NR iterations: 4
- Final mismatch (error): 3.32 × 10⁻⁹ (tolerance: 1 × 10⁻⁶)

**Voltage Magnitudes (pu, first 5 buses):**

| Bus | V_mag (pu) |
|-----|------------|
| 1 | 1.0394 |
| 2 | 1.0485 |
| 3 | 1.0307 |
| 4 | 1.0045 |
| 5 | 1.0060 |

Voltage range: [0.982, 1.064] pu across all 39 buses.

**Voltage Angles (degrees, first 5 buses):**

| Bus | V_ang (deg) |
|-----|-------------|
| 1 | -13.537 |
| 2 | -9.785 |
| 3 | -12.276 |
| 4 | -12.627 |
| 5 | -11.192 |

**Line P flows (MW, first 5 lines):**

| Line | P (MW) |
|------|--------|
| L0 | -173.700 |
| L1 | 76.100 |
| L2 | 319.915 |
| L3 | -244.592 |
| L4 | 37.340 |

**Line Q flows (MVAr, first 5 lines):**

| Line | Q (MVAr) |
|------|----------|
| L0 | -40.307 |
| L1 | -3.893 |
| L2 | 88.587 |
| L3 | 82.974 |
| L4 | 113.065 |

**Voltage spread check (convergence protocol):**
- 38 of 39 buses (97.4%) have voltage magnitudes differing from 1.0 pu by > 0.001 (slack bus fixed at rated voltage as expected)
- All outputs confirmed as pandas DataFrames

**Losses:**
- Total losses: 31.06 MW
- Loss fraction: 0.497% of total load (6,254 MW)

## Workarounds

None required. The pf_result dict has a non-obvious structure (`pf_result["n_iter"].values[0, 0]` to access scalar) but this is accessible without undocumented internals.

## Timing

- **Wall-clock:** 1.149 s
- **Timing source:** measured
- **Solve time (pf only):** 0.095 s
- **Solver iterations:** 4 (NR)
- **Convergence residual:** 3.317 × 10⁻⁹

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a2_acpf_tiny.py`

Key API sequence:
```python
pf_result = n.pf()
# pf_result is a Dict with keys n_iter, error, converged
converged = bool(pf_result["converged"].values[0, 0])
nr_iters = int(pf_result["n_iter"].values[0, 0])
residual = float(pf_result["error"].values[0, 0])
v_mag_pu = n.buses_t.v_mag_pu
v_ang    = n.buses_t.v_ang
p0       = n.lines_t.p0
q0       = n.lines_t.q0
```
