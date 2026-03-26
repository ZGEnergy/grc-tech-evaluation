---
test_id: G-1
tool: matpower
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "0a74adbf"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.048662
timestamp: 2026-03-24T23:11:07Z
---

# G-1: Network Ingestion — TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.0487 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages (Vm, Va): clean
  - No NaN/Inf in branch ratings (RATE_A): clean
  - Zero RATE_A branches: 0 (all branches have flow limits)
  - No NaN/Inf in generator limits (Pmin, Pmax): clean
  - Generator cost data present: yes (10 rows in gencost, matches gen count)
  - Slack/reference bus (type 3): 1 found
- **Errors/warnings:** None

## Test Script

```octave
addpath(genpath('/workspace/evaluations/matpower/matpower8.1'));

%% G-1: TINY — IEEE 39-bus
network_file = '/workspace/data/networks/case39.m';
exp_buses = 39; exp_branches = 46; exp_gens = 10;

tic;
mpc = loadcase(network_file);
load_time = toc;

buses = size(mpc.bus, 1);
branches = size(mpc.branch, 1);
gens = size(mpc.gen, 1);

fprintf('COUNTS: buses=%d branches=%d gens=%d\n', buses, branches, gens);
fprintf('MATCH: buses=%d branches=%d gens=%d\n', buses==exp_buses, branches==exp_branches, gens==exp_gens);
fprintf('LOAD_TIME: %.6f\n', load_time);

% Audit: NaN/Inf checks
bus_vm = mpc.bus(:,8);  % Vm column
bus_va = mpc.bus(:,9);  % Va column
nan_vm = sum(isnan(bus_vm) | isinf(bus_vm));
nan_va = sum(isnan(bus_va) | isinf(bus_va));

% Branch ratings (column 6 = RATE_A)
rate_a = mpc.branch(:,6);
nan_rate = sum(isnan(rate_a) | isinf(rate_a));
zero_rate = sum(rate_a == 0);

% Gen limits (columns 9=PMAX, 10=PMIN)
pmax = mpc.gen(:,9);
pmin = mpc.gen(:,10);
nan_gen = sum(isnan(pmax) | isinf(pmax) | isnan(pmin) | isinf(pmin));

% Cost data
has_gencost = isfield(mpc, 'gencost');
if has_gencost
  gencost_rows = size(mpc.gencost, 1);
else
  gencost_rows = 0;
end

% Slack bus
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
