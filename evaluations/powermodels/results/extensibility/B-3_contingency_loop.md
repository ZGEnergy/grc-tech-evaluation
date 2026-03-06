# B-3: N-1 DCPF Contingency Loop (TINY — case39)

## Tool
PowerModels.jl v0.21.5

## Status: PASS

## Summary
N-1 contingency analysis across all 46 branches using `compute_dc_pf`. Each contingency clones the data dict with `deepcopy`, disables one branch (`br_status=0`), and solves DCPF without re-parsing from file. 37 of 46 contingencies solve successfully; 9 fail due to network islanding.

## Approach
1. Parse network once with `PowerModels.parse_file()`
2. Solve base case DCPF with `compute_dc_pf(data)`
3. For each branch: `deepcopy(data)` -> set `br_status=0` -> `compute_dc_pf(cdata)`
4. Compute line loading from bus angle differences and branch susceptance
5. Track maximum loading per contingency

## Results

| Metric | Value |

|--------|-------|

| Total branches | 46 |

| Contingencies solved | 37 |

| Contingencies failed (islanding) | 9 |

| Worst contingency | Branch 42 (172.07% loading) |

| Wall clock (all 46 contingencies) | 0.51s |

| Re-parsed from file | No |

### Top 5 worst contingencies

| Removed Branch | Max Loading (%) |

|---------------|-----------------|

| 42 | 172.07 |

| 35 | 161.05 |

| 23 | 134.61 |

| 14 | 119.09 |

| 28 | 115.20 |

### Failed contingencies (islanding)
Branch IDs: 5, 20, 32, 33, 34, 37, 39, 41, 46

## API Friction
- `compute_dc_pf` is a direct linear solve (not JuMP-based), so it is fast for contingency loops.
- The `deepcopy` + modify pattern works cleanly without any re-parsing overhead.
- Failed contingencies (island-creating) produce solver errors rather than graceful "island detected" messages.

## Script
`tests/extensibility/test_b3_contingency_loop.jl`
