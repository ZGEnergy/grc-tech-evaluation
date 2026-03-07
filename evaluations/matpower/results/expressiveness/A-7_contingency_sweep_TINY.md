---
test_id: A-7
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 21.385
peak_memory_mb: null
loc: 150
timestamp: "2026-03-06T00:00:00Z"
---

# A-7: N-M Contingency Sweep (Pruned, Escalating) on TINY

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Focus bus:** 16 (central hub with 4 connections)
- **Graph distance:** x=3 (BFS neighborhood)
- **Max contingency order:** m=3 (N-1, N-2, N-3)
- **Analysis type:** DC power flow (rundcpf)
- **Wall clock:** 21.385 seconds (581 contingency evaluations)

## Contingency Enumeration

### Step 1: BFS Neighborhood
Buses within distance 3 of bus 16: 20 buses
`[3 4 13 14 15 16 17 18 19 20 21 22 23 24 26 27 33 34 35 36]`

### Step 2: Branches in Scope
21 branches (both endpoints within neighborhood) out of 46 total.

### Step 3: N-1 Sweep (21 cases)

| Branch | From-To | Load Loss (MW) | Status |
|--------|---------|----------------|--------|
| 6      | 3->4    | 0.00           | OK     |
| 7      | 3->18   | 0.00           | OK     |
| 9      | 4->14   | -0.00          | OK     |
| 23     | 13->14  | -0.00          | OK     |
| 24     | 14->15  | -0.00          | OK     |
| 25     | 15->16  | 0.00           | OK     |
| 26     | 16->17  | -0.00          | OK     |
| 27     | 16->19  | 6254.23        | DIVERGED |
| 28     | 16->21  | 0.00           | OK     |
| 29     | 16->24  | 0.00           | OK     |
| 30     | 17->18  | 0.00           | OK     |
| 31     | 17->27  | 0.00           | OK     |
| 32     | 19->20  | 6254.23        | DIVERGED |
| 33     | 19->33  | 6254.23        | DIVERGED |
| 34     | 20->34  | 6254.23        | DIVERGED |
| 35     | 21->22  | 0.00           | OK     |
| 36     | 22->23  | 0.00           | OK     |
| 37     | 22->35  | 6254.23        | DIVERGED |
| 38     | 23->24  | 0.00           | OK     |
| 39     | 23->36  | 6254.23        | DIVERGED |
| 42     | 26->27  | 0.00           | OK     |

### Step 4: Pruning
6 branches pruned (cause system islanding / total load loss):
- Branch 27 (16->19), 32 (19->20), 33 (19->33), 34 (20->34), 37 (22->35), 39 (23->36)

These are radial connections to generator buses -- removing them islands the generator,
causing the DC power flow to become singular.

15 surviving branches for higher-order contingencies.

### Step 5: N-2 Sweep (105 cases)
- C(15,2) = 105 pairs evaluated
- 15 cases caused near-total load loss (islanding)
- Top worst: branches 7+30 (3->18, 17->18), 24+25 (14->15, 15->16), etc.

### Step 6: N-3 Sweep (455 cases)
- C(15,3) = 455 triples evaluated
- 188 cases caused near-total load loss
- Total evaluation: 581 contingency cases

## API Observations

### No Model Reconstruction
Each contingency is evaluated by toggling `BR_STATUS` in the `mpc.branch` matrix:

```matlab
mpc_c = mpc;                        % copy struct (cheap)
mpc_c.branch(bi, BR_STATUS) = 0;    % trip branch
results_c = rundcpf(mpc_c, mpopt);  % solve
```

No model rebuild, re-indexing, or file I/O per contingency. The struct copy + column
toggle is the entire setup cost.

### Adjacency Construction
MATPOWER does not provide a built-in graph/BFS utility. The adjacency list was built
manually from `mpc.branch(:, [F_BUS T_BUS])`. This is straightforward in Octave/MATLAB
but requires ~20 lines of boilerplate. The `connected_components` function exists but
operates on incidence matrices, not BFS with depth limits.

### Singular Matrix Warnings
Some contingencies cause bus islanding, producing singular B matrices in the DC power
flow. MATPOWER warns but does not crash -- `results.success` is set to 0, allowing
clean detection. This is handled correctly.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a7_contingency_sweep_tiny.m`
