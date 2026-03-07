# Observation: Documentation Gap -- B-9 PTDF Extraction

**Tag:** doc-gaps
**Test:** B-9 (PTDF Extraction)
**Dimension:** extensibility

## Observation

The PTDF object returned by `PowerNetworkMatrices.PTDF(sys)` has a non-standard
memory layout that is not documented:

1. **Dimension convention:** The `.data` matrix is stored as (buses x branches) = (39, 46),
   which is the transpose of the conventional PTDF convention (branches x buses).
   Users must compute `ptdf.data' * injections` (note the transpose) to get branch flows.

2. **Matrix conversion:** `Matrix(ptdf)` throws a `DimensionMismatch` error due to
   custom axis types. Users must use `ptdf.data` to access the raw matrix. This is
   not documented.

3. **Axis labels:** Row axes are bus numbers (Int64), column axes are branch names (String).
   Named element access works via `ptdf["branch_name", bus_number]`, which reverses
   the apparent row/column order of the data matrix.

The PTDF values themselves are correct -- flows computed from the PTDF matrix match
DCPF results to machine precision (max error 1.15e-14). The issue is purely one of
documentation and API ergonomics.

## Impact

Low-to-moderate. The PTDF extraction is a one-liner and the values are correct, but
the non-standard layout and broken `Matrix()` conversion could cause confusion for
users expecting conventional (branches x buses) format.
