# B-9: PTDF Extraction (TINY — case39)

## Tool
PowerModels.jl v0.21.5

## Status: PASS

## Summary
PTDF matrix computed via native `calc_basic_ptdf_matrix()` API. Dimensions verified as (46, 39) = (branches x buses). Flow predictions from PTDF match DCPF results within machine epsilon (max diff: 1.3e-14). Reference bus column is zero. Native API requires `make_basic_network()` preprocessing.

## Approach
1. `data = PowerModels.parse_file(network_file)`
2. `basic_data = PowerModels.make_basic_network(data)` — renumbers, removes inactive, ensures single component
3. `ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)` — computes B_branch * B_inv
4. `theta = PowerModels.compute_basic_dc_pf(basic_data)` — solves B*theta = -injections
5. `dcpf_flows = B_branch * theta` via `calc_basic_branch_susceptance_matrix()`
6. `ptdf_flows = ptdf * injections` via `calc_basic_bus_injection()`
7. Verify: `ptdf_flows = -dcpf_flows` (sign convention: `compute_basic_dc_pf` uses `theta = -B_inv * inj`)

## Results

| Metric | Value |

|--------|-------|

| PTDF dimensions | (46, 39) |

| Expected dimensions | (46, 39) |

| Max flow diff (PTDF vs DCPF) | 1.33e-14 |

| Mean flow diff | 2.93e-15 |

| Flow match within 1e-6 | Yes |

| Ref bus index | 31 |

| Ref bus column max value | 0.0 |

| Wall clock | 2.37s |

### Sample PTDF values

| Entry | Value |

|-------|-------|

| PTDF[1,1] | 0.544576 |

| PTDF[1,2] | -0.211923 |

| PTDF[1,39] | 0.397292 |

### Sample flows

| Branch | DCPF flow | PTDF flow |

|--------|-----------|-----------|

| 1 | 1.767285 | -1.767285 |

| 2 | -0.791285 | 0.791285 |

| 3 | -3.215552 | 3.215552 |

## Sign Convention Note
`compute_basic_dc_pf` solves `theta = -B_inv * injections`, so `B_branch * theta = -(PTDF * injections)`. The DCPF and PTDF flows differ by exactly a sign. This is consistent behavior, not a bug.

## API Quality
- **Clean native API**: `calc_basic_ptdf_matrix()` is a one-liner that returns a dense matrix
- **Prerequisite**: Must call `make_basic_network()` first (renumbers buses 1..N, ensures single component, removes inactive elements)
- **Also available**: `calc_basic_ptdf_row()` for single-row extraction (efficient for sparse checks)
- **No friction**: Works exactly as documented

## Script
`tests/extensibility/test_b9_ptdf_extraction.jl`
