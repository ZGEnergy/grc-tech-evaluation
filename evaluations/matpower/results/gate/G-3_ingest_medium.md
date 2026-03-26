---
test_id: G-3
tool: matpower
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: "2da513c6"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.773542
timestamp: 2026-03-24T23:11:07Z
---

# G-3: Network Ingestion — MEDIUM (ACTIVSg 10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 0.7735 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages (Vm, Va): clean
  - No NaN/Inf in branch ratings (RATE_A): clean
  - Zero RATE_A branches: 2462 of 12706 (19.4%) — these branches have no thermal limit set, which means OPF will treat them as unconstrained. This is a property of the ACTIVSg 10k case file, not a MATPOWER ingestion issue.
  - No NaN/Inf in generator limits (Pmin, Pmax): clean
  - Generator cost data present: yes (2485 rows in gencost, matches gen count)
  - Slack/reference bus (type 3): 1 found
- **Errors/warnings:** 2462 branches with zero RATE_A (see data quality notes)

## Test Script

```octave
addpath(genpath('/workspace/evaluations/matpower/matpower8.1'));

%% G-3: MEDIUM — ACTIVSg 10k
network_file = '/workspace/data/networks/case_ACTIVSg10k.m';
exp_buses = 10000; exp_branches = 12706; exp_gens = 2485;

tic;
mpc = loadcase(network_file);
load_time = toc;

buses = size(mpc.bus, 1);
branches = size(mpc.branch, 1);
gens = size(mpc.gen, 1);

fprintf('COUNTS: buses=%d branches=%d gens=%d\n', buses, branches, gens);
fprintf('MATCH: buses=%d branches=%d gens=%d\n', buses==exp_buses, branches==exp_branches, gens==exp_gens);
fprintf('LOAD_TIME: %.6f\n', load_time);

bus_vm = mpc.bus(:,8); bus_va = mpc.bus(:,9);
nan_vm = sum(isnan(bus_vm) | isinf(bus_vm));
nan_va = sum(isnan(bus_va) | isinf(bus_va));
rate_a = mpc.branch(:,6);
nan_rate = sum(isnan(rate_a) | isinf(rate_a));
zero_rate = sum(rate_a == 0);
pmax = mpc.gen(:,9); pmin = mpc.gen(:,10);
nan_gen = sum(isnan(pmax) | isinf(pmax) | isnan(pmin) | isinf(pmin));
has_gencost = isfield(mpc, 'gencost');
if has_gencost; gencost_rows = size(mpc.gencost, 1); else; gencost_rows = 0; end
slack_buses = sum(mpc.bus(:,2) == 3);

fprintf('AUDIT_NAN_VM: %d\n', nan_vm);
fprintf('AUDIT_NAN_VA: %d\n', nan_va);
fprintf('AUDIT_NAN_RATE: %d\n', nan_rate);
fprintf('AUDIT_ZERO_RATE: %d\n', zero_rate);
fprintf('AUDIT_NAN_GEN: %d\n', nan_gen);
fprintf('AUDIT_HAS_GENCOST: %d\n', has_gencost);
fprintf('AUDIT_GENCOST_ROWS: %d\n', gencost_rows);
fprintf('AUDIT_SLACK_BUSES: %d\n', slack_buses);
```
