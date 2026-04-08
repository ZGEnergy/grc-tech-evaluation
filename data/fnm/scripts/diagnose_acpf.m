% diagnose_acpf.m -- Diagnose why ACPF diverges on the FNM.
%
% Checks: islands, bus types, negative impedances, extreme values, Q limits

script_dir = fileparts(mfilename('fullpath'));
fnm_dir = fullfile(script_dir, '..');
repo_root = fullfile(fnm_dir, '..', '..');
matpower_path = fullfile(repo_root, 'evaluations', 'matpower', 'matpower8.1');
addpath(genpath(matpower_path));

mat_path = fullfile(fnm_dir, 'reference', 'matpower_parse', 'mpc_case.mat');
load(mat_path, 'mpc');

fprintf('=== FNM Network Diagnostics ===\n\n');

bus = mpc.bus;
gen = mpc.gen;
branch = mpc.branch;

fprintf('Raw counts: %d buses, %d branches, %d generators\n', ...
        size(bus, 1), size(branch, 1), size(gen, 1));

% Bus type distribution
types = bus(:, 2);
fprintf('\nBus types:\n');
fprintf('  Type 1 (PQ):       %d\n', sum(types == 1));
fprintf('  Type 2 (PV):       %d\n', sum(types == 2));
fprintf('  Type 3 (Slack):    %d\n', sum(types == 3));
fprintf('  Type 4 (Isolated): %d\n', sum(types == 4));

% Branch status
fprintf('\nBranch status:\n');
fprintf('  In-service:  %d\n', sum(branch(:, 11) == 1));
fprintf('  Out-of-service: %d\n', sum(branch(:, 11) == 0));

% Generator status
fprintf('\nGenerator status:\n');
fprintf('  In-service:  %d\n', sum(gen(:, 8) > 0));
fprintf('  Out-of-service: %d\n', sum(gen(:, 8) <= 0));

% Check for problematic impedances
fprintf('\nBranch impedance issues (in-service only):\n');
in_service = branch(:, 11) == 1;
br_is = branch(in_service, :);
fprintf('  Zero R and X: %d\n', sum(br_is(:, 3) == 0 & br_is(:, 4) == 0));
fprintf('  Zero X only:  %d\n', sum(br_is(:, 4) == 0 & br_is(:, 3) ~= 0));
fprintf('  Negative X:   %d\n', sum(br_is(:, 4) < 0));
fprintf('  Negative R:   %d\n', sum(br_is(:, 3) < 0));
fprintf('  X < 1e-6:     %d\n', sum(abs(br_is(:, 4)) < 1e-6 & br_is(:, 4) ~= 0));

% Check for extreme values
fprintf('\nExtreme branch values (in-service):\n');
fprintf('  Max |X|: %.6f pu\n', max(abs(br_is(:, 4))));
fprintf('  Min |X| (nonzero): %.8f pu\n', min(abs(br_is(br_is(:, 4) ~= 0, 4))));
fprintf('  Max |R|: %.6f pu\n', max(abs(br_is(:, 3))));
fprintf('  Max tap ratio: %.4f\n', max(br_is(:, 9)));
fprintf('  Min tap ratio (nonzero): %.4f\n', min(br_is(br_is(:, 9) ~= 0, 9)));
fprintf('  Phase shifters (nonzero SHIFT): %d\n', sum(br_is(:, 10) ~= 0));

% Check for islands using graph connectivity
fprintf('\n=== Island Detection ===\n');
% Build adjacency from in-service branches
n_bus = size(bus, 1);
bus_nums = bus(:, 1);
bus_map = containers.Map(bus_nums, 1:n_bus);

% Union-Find (path compression inline)
parent = 1:n_bus;

for i = 1:size(br_is, 1)
    fb = br_is(i, 1);
    tb = br_is(i, 2);
    if bus_map.isKey(fb) && bus_map.isKey(tb)
        % find root of fb
        fi = bus_map(fb);
        while parent(fi) ~= fi
            fi = parent(fi);
        end
        % find root of tb
        ti = bus_map(tb);
        while parent(ti) ~= ti
            ti = parent(ti);
        end
        if fi ~= ti
            parent(fi) = ti;
        end
    end
end

% Count islands (among non-isolated buses)
active = find(types ~= 4);
island_roots = zeros(length(active), 1);
for i = 1:length(active)
    x = active(i);
    while parent(x) ~= x
        x = parent(x);
    end
    island_roots(i) = x;
end
[unique_islands, ~, ic] = unique(island_roots);
island_sizes = accumarray(ic, 1);
fprintf('Number of islands (non-isolated buses): %d\n', length(unique_islands));
fprintf('Island size distribution:\n');
sorted_sizes = sort(island_sizes, 'descend');
for i = 1:min(10, length(sorted_sizes))
    fprintf('  Island %d: %d buses\n', i, sorted_sizes(i));
end

% Check which islands have a slack bus
fprintf('\nSlack bus distribution across islands:\n');
slack_buses = find(types == 3);
for i = 1:length(slack_buses)
    si = slack_buses(i);
    x = si;
    while parent(x) ~= x
        x = parent(x);
    end
    island_id = x;
    island_size = sum(island_roots == island_id);
    fprintf('  Slack bus %d (index %d) in island of %d buses\n', ...
            bus(si, 1), si, island_size);
end

% Check PV buses without generators
pv_buses = bus(types == 2, 1);
gen_buses = unique(gen(gen(:, 8) > 0, 1));
orphan_pv = setdiff(pv_buses, gen_buses);
fprintf('\nPV buses without in-service generators: %d\n', length(orphan_pv));

% Generator Q limits
fprintf('\nGenerator Q-limit issues:\n');
active_gen = gen(gen(:, 8) > 0, :);
fprintf('  Qmax == Qmin: %d\n', sum(active_gen(:, 4) == active_gen(:, 5)));
fprintf('  Qmax < Qmin:  %d\n', sum(active_gen(:, 4) < active_gen(:, 5)));
fprintf('  Qmax == 0 and Qmin == 0: %d\n', ...
        sum(active_gen(:, 4) == 0 & active_gen(:, 5) == 0));

% Check Vg (voltage setpoint) range for active generators
fprintf('\nGenerator voltage setpoints:\n');
vg = active_gen(:, 6);
fprintf('  Min Vg: %.4f pu\n', min(vg));
fprintf('  Max Vg: %.4f pu\n', max(vg));
fprintf('  Mean Vg: %.4f pu\n', mean(vg));
fprintf('  Vg == 0: %d\n', sum(vg == 0));
fprintf('  Vg == 1.0: %d\n', sum(vg == 1.0));
fprintf('  Vg > 1.1: %d\n', sum(vg > 1.1));
fprintf('  Vg < 0.9: %d\n', sum(vg < 0.9));

fprintf('\n=== Diagnostics Complete ===\n');
