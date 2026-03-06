---
test_id: A-4
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# A-4: AC PF Feasibility Check on DC OPF Dispatch (case39)

## Result: PASS

## Metrics

- **Wall clock:** ~2.6 s
- **Lines of code:** 5 API calls (parse, solve_dc_opf, parse, set pg, compute_ac_pf!)
- **Workarounds:** None required
- **Depends on:** A-3 (DC OPF dispatch)

## Details

- **DC OPF objective:** 41,263.94 $/hr (reproduced from A-3)
- **AC PF method:** `compute_ac_pf!` (Newton-Raphson, non-JuMP, modifies data in-place)
- **AC PF convergence:** Yes (converges_ac: true)
- **No export/reimport required:** DC OPF dispatch set directly in data dict, AC PF run in same model context

### Voltage Violations (0.95-1.05 pu limits)

5 buses with voltage magnitude outside [0.95, 1.05]:
- Bus 25: vm = 1.0534
- Bus 26: vm = 1.0528
- Bus 28: vm = 1.0536
- Bus 29: vm = 1.0532
- Bus 36: vm = 1.0636

All violations are minor (within 1.4% of upper limit). Bus 36 has the largest deviation at 1.0636 pu.

### Thermal Violations

0 branches with thermal violations. Maximum loading: 89.2% (branch 3).

### Reactive Power

AC PF solves for reactive power (qg) at each generator:
- qg ranges from -0.079 (gen 9) to 2.352 (gen 2)
- Generator 2 pg adjusted from 6.46 (DC OPF) to 6.918 to account for losses

### Key Branch Loadings

| Branch | Loading % | Pf (pu) |

|--------|-----------|---------|

| 3 | 89.2% | 4.371 |

| 27 | 79.7% | -4.708 |

| 37 | 77.3% | -6.609 |

| 20 | 77.3% | -6.609 |

| 5 | 76.8% | -6.609 |

| 13 | 76.9% | -3.662 |

## API Pattern

```julia
# DC OPF (A-3)
data = PowerModels.parse_file(network_file)
result_dc = solve_dc_opf(data, HiGHS.Optimizer; setting=Dict("output"=>Dict("duals"=>true)))

# Fix dispatch and run AC PF (same model context, no export/reimport)
data_ac = PowerModels.parse_file(network_file)
for (gid, gen) in result_dc["solution"]["gen"]
    data_ac["gen"][gid]["pg"] = gen["pg"]
end
PowerModels.compute_ac_pf!(data_ac)  # modifies data_ac in-place, returns Nothing
# Results in data_ac["bus"][bid]["vm"/"va"] and via calc_branch_flow_ac(data_ac)

```

## Notes

- `compute_ac_pf!` returns `Nothing` (not a result dict like other solve functions). Solution is written directly into the data dict. This is inconsistent with `compute_dc_pf` which returns a result dict.
- Voltage violations are identifiable by inspecting `data_ac["bus"][bid]["vm"]` after solve.
- Thermal violations identifiable via `calc_branch_flow_ac(data_ac)` and comparing to `rate_a`.
- No workaround needed -- DC OPF to AC PF feasibility check is achievable within the same model context.

## Test Script

See `evaluations/powermodels/tests/expressiveness/A4_ac_feasibility.jl`
