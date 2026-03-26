---
test_id: G-2
tool: matpower
dimension: gate
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: "84277a12"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.199609
timestamp: 2026-03-24T23:11:07Z
---

# G-2: Network Ingestion — SMALL (ACTIVSg 2000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.1996 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages (Vm, Va): clean
  - No NaN/Inf in branch ratings (RATE_A): clean
  - Zero RATE_A branches: 0 (all branches have flow limits)
  - No NaN/Inf in generator limits (Pmin, Pmax): clean
  - Generator cost data present: yes (544 rows in gencost, matches gen count)
  - Slack/reference bus (type 3): 1 found
- **Errors/warnings:** None

## Test Script

```octave
addpath(genpath('/workspace/evaluations/matpower/matpower8.1'));

%% G-2: SMALL — ACTIVSg 2000
network_file = '/workspace/data/networks/case_ACTIVSg2000.m';
exp_buses = 2000; exp_branches = 3206; exp_gens = 544;

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
