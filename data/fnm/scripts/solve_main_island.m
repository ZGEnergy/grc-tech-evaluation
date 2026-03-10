% solve_main_island.m -- Extract the main island and solve DCPF + ACPF.
%
% The FNM has 4 islands: main (27862 buses) + 3 tiny (63, 9, 3 buses).
% The tiny islands cause multi-slack issues that confuse solvers.
% Extract the main island, set a single slack, and solve.

script_dir = fileparts(mfilename('fullpath'));
fnm_dir = fullfile(script_dir, '..');
repo_root = fullfile(fnm_dir, '..', '..');
matpower_path = fullfile(repo_root, 'evaluations', 'matpower', 'matpower8.1');
addpath(genpath(matpower_path));

mat_path = fullfile(fnm_dir, 'reference', 'matpower_parse', 'mpc_case.mat');
load(mat_path, 'mpc');
fprintf('Loaded: %d buses, %d branches, %d gens\n', ...
        size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

% ---- Data fixes ----
zero_x = (mpc.branch(:, 4) == 0);
if any(zero_x)
    mpc.branch(zero_x, 4) = 0.0001;
    fprintf('Fixed %d zero-X branches\n', sum(zero_x));
end
if size(mpc.branch, 2) >= 6
    zero_rate = (mpc.branch(:, 6) == 0);
    if any(zero_rate)
        mpc.branch(zero_rate, 6) = 9999;
        fprintf('Fixed %d zero-RATE_A branches\n', sum(zero_rate));
    end
end

% ---- Extract main island using MATPOWER's extract_islands ----
fprintf('\nExtracting islands...\n');
mpci = extract_islands(mpc);

% mpci is a cell array of mpc structs, one per island
fprintf('Found %d islands:\n', length(mpci));
for i = 1:length(mpci)
    fprintf('  Island %d: %d buses, %d branches, %d gens\n', ...
            i, size(mpci{i}.bus, 1), size(mpci{i}.branch, 1), size(mpci{i}.gen, 1));
end

% Find the largest island
island_sizes = cellfun(@(x) size(x.bus, 1), mpci);
[~, main_idx] = max(island_sizes);
mpc_main = mpci{main_idx};
fprintf('\nUsing island %d (%d buses) as main island\n', ...
        main_idx, size(mpc_main.bus, 1));

% Ensure exactly one slack bus
n_slack = sum(mpc_main.bus(:, 2) == 3);
fprintf('Slack buses in main island: %d\n', n_slack);
if n_slack == 0
    % Find the largest generator and make its bus the slack
    [~, max_gen_idx] = max(mpc_main.gen(:, 9));  % col 9 = Pmax
    slack_bus_num = mpc_main.gen(max_gen_idx, 1);
    bus_idx = find(mpc_main.bus(:, 1) == slack_bus_num);
    mpc_main.bus(bus_idx, 2) = 3;
    fprintf('Assigned slack to bus %d (largest Pmax = %.1f MW)\n', ...
            slack_bus_num, mpc_main.gen(max_gen_idx, 9));
elseif n_slack > 1
    slack_idx = find(mpc_main.bus(:, 2) == 3);
    for i = 2:length(slack_idx)
        mpc_main.bus(slack_idx(i), 2) = 2;
    end
    fprintf('Reduced to 1 slack (bus %d)\n', mpc_main.bus(slack_idx(1), 1));
end

% ---- DCPF on main island ----
fprintf('\n=== DCPF on Main Island ===\n');
mpopt_dc = mpoption('verbose', 1, 'out.all', 0);
tic;
results_dc = rundcpf(mpc_main, mpopt_dc);
dcpf_time = toc;

if results_dc.success
    fprintf('DCPF CONVERGED in %.2f seconds\n', dcpf_time);
else
    fprintf('DCPF FAILED\n');
end

% ---- ACPF on main island ----
fprintf('\n=== ACPF on Main Island ===\n');

% Warm start: use DCPF angles
mpc_ac = mpc_main;
if results_dc.success
    mpc_ac.bus(:, 9) = results_dc.bus(:, 9);
    fprintf('Using DCPF angles as warm start\n');
end

% Try each solver variant
algorithms = {'NR-IC', 'NR-SP', 'NR-SH', 'NR-IH', 'NR', 'FDXB', 'FDBX'};
results_ac = struct('success', 0);
acpf_time = 0;
winning_alg = '';

for a = 1:length(algorithms)
    alg = algorithms{a};
    fprintf('\n--- Trying %s ---\n', alg);

    mpopt = mpoption('verbose', 1, 'out.all', 0);
    mpopt = mpoption(mpopt, 'pf.alg', alg);
    mpopt = mpoption(mpopt, 'pf.tol', 1e-8);
    if strcmp(alg, 'FDXB') || strcmp(alg, 'FDBX')
        mpopt = mpoption(mpopt, 'pf.fd.max_it', 1000);
    else
        mpopt = mpoption(mpopt, 'pf.nr.max_it', 200);
    end
    mpopt = mpoption(mpopt, 'pf.enforce_q_lims', 0);

    tic;
    results_ac = runpf(mpc_ac, mpopt);
    acpf_time = toc;

    if results_ac.success
        fprintf('%s CONVERGED in %.2f sec, %d iterations\n', ...
                alg, acpf_time, results_ac.iterations);
        winning_alg = alg;
        break
    else
        fprintf('%s failed\n', alg);
    end
end

% ---- Write reference outputs ----
if results_dc.success
    dcpf_dir = fullfile(fnm_dir, 'reference', 'dcpf');
    if ~exist(dcpf_dir, 'dir')
        mkdir(dcpf_dir);
    end

    bus_dc = results_dc.bus;
    br_dc = results_dc.branch;

    fid = fopen(fullfile(dcpf_dir, 'buses_dcpf.csv'), 'w');
    fprintf(fid, 'bus_number,va_deg,pd_mw,base_kv,bus_type\n');
    for i = 1:size(bus_dc, 1)
        if bus_dc(i, 2) == 4
            continue
        end
        fprintf(fid, '%d,%.8f,%.4f,%.2f,%d\n', ...
                bus_dc(i, 1), bus_dc(i, 9), bus_dc(i, 3), bus_dc(i, 10), bus_dc(i, 2));
    end
    fclose(fid);

    fid = fopen(fullfile(dcpf_dir, 'branches_dcpf.csv'), 'w');
    fprintf(fid, 'from_bus,to_bus,pf_mw,status\n');
    for i = 1:size(br_dc, 1)
        if br_dc(i, 11) == 0
            continue
        end
        fprintf(fid, '%d,%d,%.8f,%d\n', ...
                br_dc(i, 1), br_dc(i, 2), br_dc(i, 14), br_dc(i, 11));
    end
    fclose(fid);

    slack_idx = find(bus_dc(:, 2) == 3);
    active_buses = bus_dc(bus_dc(:, 2) ~= 4, :);
    active_gens = results_dc.gen(results_dc.gen(:, 8) > 0, :);

    fid = fopen(fullfile(dcpf_dir, 'summary_dcpf.json'), 'w');
    fprintf(fid, '{\n');
    fprintf(fid, '  "success": %d,\n', results_dc.success);
    fprintf(fid, '  "wall_clock_seconds": %.4f,\n', dcpf_time);
    fprintf(fid, '  "total_gen_mw": %.4f,\n', sum(active_gens(:, 2)));
    fprintf(fid, '  "total_load_mw": %.4f,\n', sum(active_buses(:, 3)));
    fprintf(fid, '  "slack_bus": %d,\n', bus_dc(slack_idx(1), 1));
    fprintf(fid, '  "slack_angle": %.8f,\n', bus_dc(slack_idx(1), 9));
    fprintf(fid, '  "n_buses": %d,\n', size(active_buses, 1));
    fprintf(fid, '  "n_branches": %d,\n', sum(br_dc(:, 11) ~= 0));
    fprintf(fid, '  "n_gens": %d,\n', size(active_gens, 1));
    fprintf(fid, '  "main_island_only": true\n');
    fprintf(fid, '}\n');
    fclose(fid);
    fprintf('DCPF reference written\n');
end

if results_ac.success
    acpf_dir = fullfile(fnm_dir, 'reference', 'acpf');
    if ~exist(acpf_dir, 'dir')
        mkdir(acpf_dir);
    end

    bus_ac = results_ac.bus;
    br_ac = results_ac.branch;
    gen_ac = results_ac.gen;
    active_gens = gen_ac(gen_ac(:, 8) > 0, :);
    active_buses = bus_ac(bus_ac(:, 2) ~= 4, :);
    n_isolated = sum(bus_ac(:, 2) == 4);

    fid = fopen(fullfile(acpf_dir, 'buses_acpf.csv'), 'w');
    fprintf(fid, 'bus_number,vm_pu,va_deg,pd_mw,qd_mvar,bus_type\n');
    for i = 1:size(bus_ac, 1)
        if bus_ac(i, 2) == 4
            continue
        end
        fprintf(fid, '%d,%.8f,%.8f,%.4f,%.4f,%d\n', ...
                bus_ac(i, 1), bus_ac(i, 8), bus_ac(i, 9), ...
                bus_ac(i, 3), bus_ac(i, 4), bus_ac(i, 2));
    end
    fclose(fid);

    fid = fopen(fullfile(acpf_dir, 'branches_acpf.csv'), 'w');
    fprintf(fid, 'from_bus,to_bus,pf_mw,qf_mvar,pt_mw,qt_mvar,status\n');
    for i = 1:size(br_ac, 1)
        if br_ac(i, 11) == 0
            continue
        end
        fprintf(fid, '%d,%d,%.8f,%.8f,%.8f,%.8f,%d\n', ...
                br_ac(i, 1), br_ac(i, 2), br_ac(i, 14), br_ac(i, 15), ...
                br_ac(i, 16), br_ac(i, 17), br_ac(i, 11));
    end
    fclose(fid);

    fid = fopen(fullfile(acpf_dir, 'generators_acpf.csv'), 'w');
    fprintf(fid, 'bus_number,pg_mw,qg_mvar,status,vm_setpoint\n');
    for i = 1:size(gen_ac, 1)
        if gen_ac(i, 8) <= 0
            continue
        end
        fprintf(fid, '%d,%.8f,%.8f,%d,%.8f\n', ...
                gen_ac(i, 1), gen_ac(i, 2), gen_ac(i, 3), ...
                gen_ac(i, 8), gen_ac(i, 6));
    end
    fclose(fid);

    fid = fopen(fullfile(acpf_dir, 'summary_acpf.json'), 'w');
    fprintf(fid, '{\n');
    fprintf(fid, '  "success": %d,\n', results_ac.success);
    fprintf(fid, '  "wall_clock_seconds": %.4f,\n', acpf_time);
    fprintf(fid, '  "iterations": %d,\n', results_ac.iterations);
    fprintf(fid, '  "algorithm": "%s",\n', winning_alg);
    fprintf(fid, '  "total_gen_mw": %.4f,\n', sum(active_gens(:, 2)));
    fprintf(fid, '  "total_gen_mvar": %.4f,\n', sum(active_gens(:, 3)));
    fprintf(fid, '  "total_load_mw": %.4f,\n', sum(active_buses(:, 3)));
    fprintf(fid, '  "total_load_mvar": %.4f,\n', sum(active_buses(:, 4)));
    fprintf(fid, '  "losses_mw": %.4f,\n', sum(active_gens(:, 2)) - sum(active_buses(:, 3)));
    fprintf(fid, '  "n_buses": %d,\n', size(active_buses, 1));
    fprintf(fid, '  "n_branches": %d,\n', sum(br_ac(:, 11) ~= 0));
    fprintf(fid, '  "n_gens": %d,\n', size(active_gens, 1));
    fprintf(fid, '  "solver": "MATPOWER 8.1",\n');
    fprintf(fid, '  "tolerance": 1e-8,\n');
    fprintf(fid, '  "q_limits_enforced": false,\n');
    fprintf(fid, '  "isolated_buses_removed": %d,\n', n_isolated);
    fprintf(fid, '  "main_island_only": true,\n');
    fprintf(fid, '  "initial_conditions": "dcpf_warm_start_flat_vm"\n');
    fprintf(fid, '}\n');
    fclose(fid);
    fprintf('ACPF reference written\n');
else
    fprintf('\n=== ALL ACPF ATTEMPTS FAILED ===\n');
    acpf_dir = fullfile(fnm_dir, 'reference', 'acpf');
    if ~exist(acpf_dir, 'dir')
        mkdir(acpf_dir);
    end
    fid = fopen(fullfile(acpf_dir, 'summary_acpf.json'), 'w');
    fprintf(fid, '{\n');
    fprintf(fid, '  "success": 0,\n');
    n_main = size(mpc_main.bus, 1);
    fprintf(fid, ...
            '  "failure_reason": "All MATPOWER variants diverged (%d buses)",\n', ...
            n_main);
    fprintf(fid, '  "attempts": [');
    for a = 1:length(algorithms)
        fprintf(fid, '"%s"', algorithms{a});
        if a < length(algorithms)
            fprintf(fid, ', ');
        end
    end
    fprintf(fid, '],\n');
    fprintf(fid, '  "n_buses": %d,\n', sum(mpc_main.bus(:, 2) ~= 4));
    fprintf(fid, '  "all_vg_flat": true,\n');
    fprintf(fid, '  "all_vm_flat": true,\n');
    fprintf(fid, '  "main_island_only": true\n');
    fprintf(fid, '}\n');
    fclose(fid);
end

fprintf('\n=== DONE ===\n');
