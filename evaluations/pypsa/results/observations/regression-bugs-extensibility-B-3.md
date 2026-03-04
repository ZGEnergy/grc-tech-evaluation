# Observation: PyPSA 1.1.2 regression bugs in power flow contingency paths

**Dimension:** extensibility
**Test:** B-3 (N-1 DCPF contingency loop)
**Tool:** pypsa 1.1.2
**Severity:** moderate — affects built-in contingency API and island-causing branch outages

## Bug 1: `lpf_contingency()` AttributeError

**File:** `pypsa/network/power_flow.py`, line 934
**Trigger:** Calling `net.lpf_contingency()` with default single snapshot
**Error:** `AttributeError: 'DataFrame' object has no attribute 'to_frame'`

**Root cause:** `pd.concat({c: series for c in components})` produces a DataFrame (not a
Series) when the resulting index is a MultiIndex. The code then calls `.to_frame("base")`
which is a Series method. Should use `.rename(columns={0: "base"})` or similar.

**Impact:** The BODF-based O(branches)-per-contingency method is completely unusable. Users
must fall back to the O(branches * solve_cost) loop approach.

## Bug 2: `lpf()` KeyError on island-causing outages

**File:** `pypsa/network/power_flow.py`, line 1840
**Trigger:** Deactivating a branch that splits the network into sub-networks where one
sub-network has no Lines (only Transformers) or vice versa
**Error:** `KeyError: 'Line'`

**Root cause:** After solving, the code iterates over `self.components` (all passive branch
types in the sub-network) and indexes into the `flows` DataFrame with `flows.loc[:, c.name]`.
The `flows` DataFrame is built from `branches_i` which may not include all component types
if the sub-network has no active branches of that type. The component iteration should be
filtered to only component types present in the flows DataFrame.

**Impact:** 2 of 46 contingencies on IEEE 39-bus fail (both island-causing). Workaround:
catch KeyError.

## Recommendation

Both bugs appear to be regressions introduced by the component store refactoring in PyPSA 1.x.
They should be reported upstream. Neither is architectural — both are fixable with 1-2 line
patches.
