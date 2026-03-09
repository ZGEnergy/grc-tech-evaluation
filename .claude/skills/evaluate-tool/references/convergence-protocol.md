# Convergence Protocol

Standard procedure for handling convergence in AC power flow and AC OPF problems.
Ensures consistent treatment across all tools under evaluation.

## Flat Start Protocol

**Default for all AC problems (any test with `converges_ac: true` in the eval-config):**

1. **Flat start:** Initialize all bus voltage magnitudes to 1.0 pu, all angles to 0.0 rad.
   This is the standard "cold start" that tests the solver's robustness.

2. **Record convergence:** Document whether the flat start converges, including:
   - Number of iterations (must be nonzero for valid convergence)
   - Final mismatch / convergence residual (must be below solver tolerance)
   - Wall-clock time

3. **Verify convergence quality:** Even if the solver reports "converged", check:
   - Iteration count > 0 (zero iterations means the solver did not run)
   - Voltage magnitudes differ from 1.0 pu on >95% of buses (flat-start values
     persisting indicate no actual solution was computed)
   - If the tool cannot report iteration count or residual, document this as a
     diagnostic quality finding (not a convergence failure, but a limitation)

4. **If flat start fails:** Proceed to the DC warm start fallback.

## DC Warm Start Fallback

If flat start does not converge:

1. **Solve DCPF first** on the same network.
2. **Use DC solution as initialization:**
   - Set voltage angles from DCPF solution
   - Keep voltage magnitudes at 1.0 pu (DCPF doesn't produce voltage magnitudes)
3. **Re-attempt ACPF** with the warm start.
4. **Record:** That a DC warm start was needed. This is a finding — not a failure,
   but it affects the Expressiveness grade for A-2 (tool should handle flat start
   gracefully on standard test networks).

## Solver Tolerance Adjustments

If the DC warm start also fails:

1. **Relax tolerance** to `acceptable_tol` (1e-4 for Ipopt).
2. **Increase iteration limit** to 2x default.
3. **Record:** All tolerance adjustments. If relaxed tolerance is needed on the TINY
   network, this is a significant finding. On MEDIUM, it may be expected.

## What Convergence Failure Means

| Network | Flat Start Fails | DC Warm Start Fails | Both Fail |
|---------|-----------------|--------------------|-----------|
| TINY | Minor finding (tool-specific) | Significant finding | A-2 fails |
| SMALL | Expected for some tools | Notable finding | Record, may cap grade |
| MEDIUM | Common | Notable finding | Record, may cap grade |

## AC Feasibility Check Protocol

For tests that run ACPF on a DC OPF dispatch (e.g., AC feasibility checks):

1. **Solve DC OPF** — obtain generator dispatch
2. **Fix generator active power** to DC OPF dispatch values
3. **Run ACPF** with generators as PV buses (voltage magnitude specified, active power fixed)
4. **Record violations:**
   - Voltage magnitude violations (outside [0.95, 1.05] pu)
   - Line flow limit violations (MVA rating exceeded)
   - Reactive power limit violations

The key test is whether step 2-3 can happen **within the same model context** — no
exporting results to a file and reimporting. The tool must support modifying
generator dispatch and re-solving without reconstructing the network model.

## Contingency Convergence

For contingency sweeps involving ACPF:
- Use the base case solution as warm start for each contingency
- If a contingency case doesn't converge, mark it as "non-convergent" and continue
  (don't halt the sweep)
- Record the fraction of non-convergent cases
- Non-convergent cases should still report which component was removed

For DCPF contingencies, convergence is always guaranteed (linear system), so this
protocol doesn't apply.
