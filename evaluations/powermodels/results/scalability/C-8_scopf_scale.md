---
test_id: C-8
tool: powermodels
dimension: scalability
network: MEDIUM
status: fail
wall_clock_seconds: -1
peak_memory_mb: 15375
timestamp: 2026-03-05
---

# C-8: SCOPF (N-1, 500 contingencies) at MEDIUM (10000 buses)

## Result: FAIL (resource limits)

The SCOPF test did not complete within the observation window. Two attempts were made:

1. **HiGHS attempt:** Base DC OPF failed with QP solver error (same as C-3/C-7)
2. **Ipopt attempt:** Still computing after >20 minutes. Memory usage reached ~15.4 GB for the multi-network model.

## Resource Usage
- Peak memory: ~15,375 MB (15.4 GB) -- Ipopt attempt
- CPU cores: 1 (single-threaded)
- The multi-network model for even 20 contingencies creates a massive optimization problem

## Method

```julia
# Multi-network corrective SCOPF:
# Network 1 = base case, Networks 2..N+1 = contingency cases
mn_data = PowerModels.replicate(data, 1 + n_contingencies)
# Remove one branch per contingency network
# Build model, replace objective with base-case cost only
pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, build_mn_opf)

```

## Analysis
SCOPF at 10k buses is extremely resource-intensive:

1. **Memory scaling:** Each network replica of the 10k-bus system requires ~30 MB of model data. For 500 contingencies, the multi-network approach would need 500 x 30 MB = ~15 GB just for the data, plus the JuMP model overhead.

2. **The multi-network approach does not scale to 500 contingencies at 10k buses.** Even 20 contingencies consumed 15.4 GB of memory.

3. **PowerModelsSecurityConstrained.jl** (not installed) uses iterative contingency screening and lazy constraint generation, which is far more memory-efficient. The brute-force multi-network approach tested here is only suitable for small networks or small contingency counts.

4. **For production SCOPF at 10k buses**, either:
   - Use PowerModelsSecurityConstrained.jl with its screening/iteration approach
   - Implement a Benders decomposition (master problem + subproblems per contingency)
   - Use a commercial solver with more efficient memory management

## Fallback Attempts
The test script was configured to try progressively smaller contingency counts (500, 100, 20) if larger sizes failed. The memory consumption even at the initial data replication stage suggests that even 20 contingencies at 10k buses is at the limit of the available resources.
