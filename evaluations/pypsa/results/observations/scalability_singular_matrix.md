# Observation: Singular Matrix on ACTIVSg10k Network

- **Source:** C-1, C-2, C-5, C-8, C-9 (scalability)
- **Severity:** Medium (affects ACPF, PTDF, SCOPF on specific networks)

## Finding

The ACTIVSg10k (10,000-bus) test case contains 3 transformers with zero reactance (T132, T2929, T2930) and 4 transformers with zero resistance (T18, T132, T2929, T2930). These cause the B-matrix (susceptance matrix) used in DC power flow and PTDF computations to be exactly singular.

## Impact by Test

| Test | Impact | Workaround |
|------|--------|------------|
| C-1 (DCPF) | Warning only; produces valid results | Set `x=0.0001` on zero-x branches |
| C-2 (ACPF) | Newton-Raphson fails at iteration 0 | Fix impedance; may still not converge |
| C-5 (Contingency) | NaN flows if fix not applied | Fix impedance before DCPF |
| C-8 (SCOPF) | PTDF coefficients overflow to inf | Fix impedance; but 1/0.0001 still large |
| C-9 (PTDF) | `Factor is exactly singular` error | Fix impedance; resolves completely |

## Root Cause

PyPSA imports MATPOWER cases via `import_from_pypower_ppc()`, which preserves the original impedance values. MATPOWER itself may treat zero-impedance branches as ideal transformers or closed switches, but PyPSA's DC formulation requires non-zero reactance for all branches in the susceptance matrix.

## Fix

```python
n.transformers.loc[n.transformers.x == 0, "x"] = 0.0001
n.lines.loc[n.lines.x == 0, "x"] = 0.0001
```

This is a reasonable workaround (0.0001 p.u. reactance ~ very low impedance) but creates numerical conditioning issues for SCOPF (1/x ~ 10,000).

## Recommendation

PyPSA should either:
1. Warn users about zero-impedance branches during import (currently warns about zero `s_nom` but not zero `x`)
2. Provide an `overwrite_zero_x` parameter similar to `overwrite_zero_s_nom`
3. Handle zero-impedance branches as ideal connections in the DC formulation
