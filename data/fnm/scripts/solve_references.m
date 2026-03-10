% solve_references.m -- Clean FNM data, export cleaned case, compute references.
%
% Usage:
%   octave --no-gui --no-window-system solve_references.m
%
% Inputs:
%   - MATPOWER-parsed case: data/fnm/reference/matpower_parse/mpc_case.mat
%
% Outputs:
%   - data/fnm/reference/cleaned/fnm_main_island.m    (MATPOWER case file)
%   - data/fnm/reference/cleaned/fnm_main_island.mat   (binary .mat for scipy)
%   - data/fnm/reference/cleaned/summary_cleaning.json  (committed manifest)
%   - data/fnm/reference/dcpf/  (buses_dcpf.csv, branches_dcpf.csv, summary_dcpf.json)
%   - data/fnm/reference/acpf/  (buses, branches, generators, summary)

% Determine paths
script_dir = fileparts(mfilename('fullpath'));
fnm_dir = fullfile(script_dir, '..');
repo_root = fullfile(fnm_dir, '..', '..');
matpower_path = fullfile(repo_root, 'evaluations', 'matpower', 'matpower8.1');

% Add MATPOWER
addpath(genpath(matpower_path));

% Load the pre-parsed case
mat_path = fullfile(fnm_dir, 'reference', 'matpower_parse', 'mpc_case.mat');
if ~exist(mat_path, 'file')
    error('mpc_case.mat not found at %s', mat_path);
end
load(mat_path, 'mpc');
fprintf('Loaded mpc: %d buses, %d branches, %d generators\n', ...
        size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

% =========================================================================
% Stage 1: Data Cleaning (per protocol v6)
% =========================================================================
fprintf('\n=== Stage 1: Data Cleaning ===\n');

cleaning_log = struct();

% --- Fix 1: Negative reactance -> absolute value (series capacitors) ---
neg_x = (mpc.branch(:, 4) < 0);
n_neg_x = sum(neg_x);
if n_neg_x > 0
    mpc.branch(neg_x, 4) = abs(mpc.branch(neg_x, 4));
    fprintf('Fix 1: Coerced %d negative-X branches to |X| (series capacitors)\n', n_neg_x);
end
cleaning_log.negative_x_coerced = n_neg_x;

% --- Fix 2: Zero reactance -> small value ---
zero_x = (mpc.branch(:, 4) == 0);
n_zero_x = sum(zero_x);
if n_zero_x > 0
    mpc.branch(zero_x, 4) = 0.0001;
    fprintf('Fix 2: Set %d zero-X branches to X=0.0001 pu\n', n_zero_x);
end
cleaning_log.zero_x_fixed = n_zero_x;

% --- Fix 3: Zero resistance -> small value ---
zero_r = (mpc.branch(:, 3) == 0);
n_zero_r = sum(zero_r);
if n_zero_r > 0
    mpc.branch(zero_r, 3) = 0.0001;
    fprintf('Fix 3: Set %d zero-R branches to R=0.0001 pu\n', n_zero_r);
end
cleaning_log.zero_r_fixed = n_zero_r;

% --- Fix 4: Zero thermal rating -> unlimited ---
if size(mpc.branch, 2) >= 6
    zero_rate = (mpc.branch(:, 6) == 0);
    n_zero_rate = sum(zero_rate);
    if n_zero_rate > 0
        mpc.branch(zero_rate, 6) = 9999;
        fprintf('Fix 4: Set %d zero-RATE_A branches to 9999 MVA\n', n_zero_rate);
    end
else
    n_zero_rate = 0;
end
cleaning_log.zero_rate_a_fixed = n_zero_rate;

% =========================================================================
% Stage 2: Island Extraction
% =========================================================================
fprintf('\n=== Stage 2: Island Extraction ===\n');

mpci = extract_islands(mpc);
n_islands = length(mpci);
fprintf('Found %d islands:\n', n_islands);
island_info = {};
for i = 1:n_islands
    nb = size(mpci{i}.bus, 1);
    nbr = size(mpci{i}.branch, 1);
    ng = size(mpci{i}.gen, 1);
    fprintf('  Island %d: %d buses, %d branches, %d gens\n', i, nb, nbr, ng);
    island_info{i} = struct('buses', nb, 'branches', nbr, 'gens', ng);
end

% Select the largest island
island_sizes = cellfun(@(x) size(x.bus, 1), mpci);
[~, main_idx] = max(island_sizes);
mpc_main = mpci{main_idx};
fprintf('Selected island %d (%d buses) as main island\n', ...
        main_idx, size(mpc_main.bus, 1));

cleaning_log.islands_total = n_islands;
cleaning_log.main_island_buses = size(mpc_main.bus, 1);
cleaning_log.main_island_branches = size(mpc_main.branch, 1);
cleaning_log.main_island_gens = size(mpc_main.gen, 1);
cleaning_log.excluded_buses = size(mpc.bus, 1) - size(mpc_main.bus, 1);

% =========================================================================
% Stage 3: Multi-Slack Reduction
% =========================================================================
fprintf('\n=== Stage 3: Slack Bus Reduction ===\n');

slack_idx = find(mpc_main.bus(:, 2) == 3);
n_slack = length(slack_idx);
fprintf('Slack buses in main island: %d\n', n_slack);

if n_slack == 0
    % Promote the bus with the largest generator to slack
    [~, max_gen_idx] = max(mpc_main.gen(:, 9));  % col 9 = Pmax
    slack_bus_num = mpc_main.gen(max_gen_idx, 1);
    bus_idx = find(mpc_main.bus(:, 1) == slack_bus_num);
    mpc_main.bus(bus_idx, 2) = 3;
    fprintf('Assigned slack to bus %d (largest Pmax = %.1f MW)\n', ...
            slack_bus_num, mpc_main.gen(max_gen_idx, 9));
    cleaning_log.slack_action = 'promoted_largest_gen';
    cleaning_log.slack_bus = slack_bus_num;
elseif n_slack > 1
    kept_slack = mpc_main.bus(slack_idx(1), 1);
    demoted = [];
    for i = 2:length(slack_idx)
        demoted(end + 1) = mpc_main.bus(slack_idx(i), 1);
        mpc_main.bus(slack_idx(i), 2) = 2;  % demote to PV
    end
    fprintf('Kept bus %d as slack, demoted %d others to PV: [%s]\n', ...
            kept_slack, length(demoted), num2str(demoted));
    cleaning_log.slack_action = 'demoted_extras';
    cleaning_log.slack_bus = kept_slack;
    cleaning_log.slack_demoted = demoted;
else
    cleaning_log.slack_action = 'none_needed';
    cleaning_log.slack_bus = mpc_main.bus(slack_idx(1), 1);
end

% =========================================================================
% Stage 4: Export Cleaned Case
% =========================================================================
fprintf('\n=== Stage 4: Export Cleaned Case ===\n');

cleaned_dir = fullfile(fnm_dir, 'reference', 'cleaned');
if ~exist(cleaned_dir, 'dir')
    mkdir(cleaned_dir);
end

% Ensure the case name is set
mpc_main.casename = 'fnm_main_island';

% Save as MATPOWER .m case file (readable by MATPOWER, PowerModels.jl, etc.)
case_m_path = fullfile(cleaned_dir, 'fnm_main_island.m');
savecase(case_m_path, mpc_main);
fprintf('Saved cleaned case: %s\n', case_m_path);

% Save as .mat binary (readable by scipy.io.loadmat)
case_mat_path = fullfile(cleaned_dir, 'fnm_main_island.mat');
mpc = mpc_main;  % savecase uses 'mpc' variable name
save(case_mat_path, 'mpc');
fprintf('Saved cleaned case: %s\n', case_mat_path);

% Count in-service elements in cleaned case
n_buses_clean = size(mpc_main.bus, 1);
n_branches_clean = size(mpc_main.branch, 1);
n_branches_active = sum(mpc_main.branch(:, 11) ~= 0);
n_gens_clean = size(mpc_main.gen, 1);
n_gens_active = sum(mpc_main.gen(:, 8) > 0);
n_loads = sum(mpc_main.bus(:, 3) ~= 0 | mpc_main.bus(:, 4) ~= 0);

fprintf('Cleaned case: %d buses, %d branches (%d active), %d gens (%d active), %d loads\n', ...
        n_buses_clean, n_branches_clean, n_branches_active, n_gens_clean, n_gens_active, n_loads);

% Write cleaning manifest (JSON - this file gets committed)
manifest_path = fullfile(cleaned_dir, 'summary_cleaning.json');
fid = fopen(manifest_path, 'w');
fprintf(fid, '{\n');
fprintf(fid, '  "source": "data/fnm/reference/matpower_parse/mpc_case.mat",\n');
src_buses = size(mpci{1}.bus, 1) + cleaning_log.excluded_buses;
fprintf(fid, '  "source_buses": %d,\n', src_buses);
fprintf(fid, '  "cleaning_steps": [\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 1,\n');
fprintf(fid, '      "name": "negative_x_to_abs",\n');
desc = 'Coerce negative reactance to |X| (series capacitors)';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "affected_branches": %d\n', cleaning_log.negative_x_coerced);
fprintf(fid, '    },\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 2,\n');
fprintf(fid, '      "name": "zero_x_to_small",\n');
desc = 'Set zero reactance to 0.0001 pu (singular admittance)';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "affected_branches": %d\n', cleaning_log.zero_x_fixed);
fprintf(fid, '    },\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 3,\n');
fprintf(fid, '      "name": "zero_r_to_small",\n');
desc = 'Set zero resistance to 0.0001 pu (NR Jacobian)';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "affected_branches": %d\n', cleaning_log.zero_r_fixed);
fprintf(fid, '    },\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 4,\n');
fprintf(fid, '      "name": "zero_rate_a_to_unlimited",\n');
desc = 'Set zero thermal rating to 9999 MVA (unlimited)';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "affected_branches": %d\n', cleaning_log.zero_rate_a_fixed);
fprintf(fid, '    },\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 5,\n');
fprintf(fid, '      "name": "island_extraction",\n');
desc = 'Extract largest connected island';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "islands_total": %d,\n', cleaning_log.islands_total);
fprintf(fid, '      "main_island_buses": %d,\n', cleaning_log.main_island_buses);
fprintf(fid, '      "excluded_buses": %d\n', cleaning_log.excluded_buses);
fprintf(fid, '    },\n');
fprintf(fid, '    {\n');
fprintf(fid, '      "step": 6,\n');
fprintf(fid, '      "name": "single_slack_bus",\n');
desc = 'Ensure exactly one slack (type-3) bus';
fprintf(fid, '      "description": "%s",\n', desc);
fprintf(fid, '      "action": "%s",\n', cleaning_log.slack_action);
fprintf(fid, '      "slack_bus": %d\n', cleaning_log.slack_bus);
fprintf(fid, '    }\n');
fprintf(fid, '  ],\n');
fprintf(fid, '  "output_files": [\n');
fprintf(fid, '    "fnm_main_island.m",\n');
fprintf(fid, '    "fnm_main_island.mat"\n');
fprintf(fid, '  ],\n');
fprintf(fid, '  "cleaned_network": {\n');
fprintf(fid, '    "buses": %d,\n', n_buses_clean);
fprintf(fid, '    "branches_total": %d,\n', n_branches_clean);
fprintf(fid, '    "branches_active": %d,\n', n_branches_active);
fprintf(fid, '    "generators_total": %d,\n', n_gens_clean);
fprintf(fid, '    "generators_active": %d,\n', n_gens_active);
fprintf(fid, '    "loads_nonzero": %d,\n', n_loads);
fprintf(fid, '    "baseMVA": %.1f\n', mpc_main.baseMVA);
fprintf(fid, '  },\n');
fprintf(fid, '  "matpower_version": "8.1",\n');
note = 'Import directly -- all cleaning pre-applied';
fprintf(fid, '  "note": "%s"\n', note);
fprintf(fid, '}\n');
fclose(fid);
fprintf('Cleaning manifest written: %s\n', manifest_path);

% Reload mpc_main into 'mpc' alias for solve stages
mpc = mpc_main;

% =========================================================================
% Stage 5: DCPF Reference Solution
% =========================================================================
fprintf('\n=== Stage 5: DCPF Reference Solution ===\n');

mpopt_dc = mpoption('verbose', 2, 'out.all', 0);
tic;
results_dc = rundcpf(mpc, mpopt_dc);
dcpf_time = toc;

if results_dc.success
    fprintf('DCPF CONVERGED in %.2f seconds\n', dcpf_time);
else
    fprintf('DCPF FAILED\n');
end

% Write DCPF outputs
dcpf_dir = fullfile(fnm_dir, 'reference', 'dcpf');
if ~exist(dcpf_dir, 'dir')
    mkdir(dcpf_dir);
end

% rundcpf returns results in external numbering
results_dc_ext = results_dc;

% buses_dcpf.csv: bus_number, va_deg, pd_mw, base_kv, bus_type
bus_dc = results_dc_ext.bus;
fid = fopen(fullfile(dcpf_dir, 'buses_dcpf.csv'), 'w');
fprintf(fid, 'bus_number,va_deg,pd_mw,base_kv,bus_type\n');
for i = 1:size(bus_dc, 1)
    % Skip isolated buses (type 4)
    if bus_dc(i, 2) == 4
        continue
    end
    fprintf(fid, '%d,%.8f,%.4f,%.2f,%d\n', ...
            bus_dc(i, 1), bus_dc(i, 9), bus_dc(i, 3), bus_dc(i, 10), bus_dc(i, 2));
end
fclose(fid);

% branches_dcpf.csv: from_bus, to_bus, pf_mw, status
br_dc = results_dc_ext.branch;
fid = fopen(fullfile(dcpf_dir, 'branches_dcpf.csv'), 'w');
fprintf(fid, 'from_bus,to_bus,pf_mw,status\n');
for i = 1:size(br_dc, 1)
    if br_dc(i, 11) == 0
        continue
    end  % skip out-of-service
    fprintf(fid, '%d,%d,%.8f,%d\n', ...
            br_dc(i, 1), br_dc(i, 2), br_dc(i, 14), br_dc(i, 11));
end
fclose(fid);

% Find slack bus
slack_idx = find(bus_dc(:, 2) == 3);
if ~isempty(slack_idx)
    slack_bus = bus_dc(slack_idx(1), 1);
    slack_angle = bus_dc(slack_idx(1), 9);
else
    slack_bus = -1;
    slack_angle = 0;
end

% Count non-isolated buses
n_active_buses = sum(bus_dc(:, 2) ~= 4);
n_active_branches = sum(br_dc(:, 11) ~= 0);
n_active_gens = sum(results_dc_ext.gen(:, 8) > 0);

% summary_dcpf.json
total_gen_mw = sum(results_dc_ext.gen(results_dc_ext.gen(:, 8) > 0, 2));
total_load_mw = sum(bus_dc(bus_dc(:, 2) ~= 4, 3));

fid = fopen(fullfile(dcpf_dir, 'summary_dcpf.json'), 'w');
fprintf(fid, '{\n');
fprintf(fid, '  "success": %d,\n', results_dc.success);
fprintf(fid, '  "wall_clock_seconds": %.4f,\n', dcpf_time);
fprintf(fid, '  "total_gen_mw": %.4f,\n', total_gen_mw);
fprintf(fid, '  "total_load_mw": %.4f,\n', total_load_mw);
fprintf(fid, '  "slack_bus": %d,\n', slack_bus);
fprintf(fid, '  "slack_angle": %.8f,\n', slack_angle);
fprintf(fid, '  "n_buses": %d,\n', n_active_buses);
fprintf(fid, '  "n_branches": %d,\n', n_active_branches);
fprintf(fid, '  "n_gens": %d,\n', n_active_gens);
fprintf(fid, '  "main_island_only": true\n');
fprintf(fid, '}\n');
fclose(fid);
fprintf('DCPF reference written to %s\n', dcpf_dir);

% =========================================================================
% Stage 6: ACPF Reference Solution
% =========================================================================
fprintf('\n=== Stage 6: ACPF Reference Solution ===\n');

% Initialize: use PV bus voltage setpoints from gen table, DCPF angles
mpc_ac = mpc;
mpc_ac.bus(:, 8) = 1.0;   % VM flat start
mpc_ac.bus(:, 9) = results_dc_ext.bus(:, 9);  % DC warm start angles

% Set PV bus VM to generator voltage setpoints (col 6 in gen table)
for i = 1:size(mpc_ac.gen, 1)
    if mpc_ac.gen(i, 8) > 0  % in-service
        gen_bus = mpc_ac.gen(i, 1);
        bus_idx = find(mpc_ac.bus(:, 1) == gen_bus);
        if ~isempty(bus_idx)
            mpc_ac.bus(bus_idx(1), 8) = mpc_ac.gen(i, 6);  % VG setpoint
        end
    end
end
fprintf('Initialized VM from gen setpoints for %d PV/slack buses\n', ...
        sum(mpc_ac.bus(:, 2) >= 2 & mpc_ac.bus(:, 2) <= 3));
fprintf('Initialized VA from DCPF angles\n');

% ---- Attempt 1: Fast Decoupled XB (more robust for large networks) ----
fprintf('\n--- Attempt 1: Fast Decoupled XB ---\n');
mpopt_fd = mpoption('verbose', 2, 'out.all', 0);
mpopt_fd = mpoption(mpopt_fd, 'pf.alg', 'FDXB');
mpopt_fd = mpoption(mpopt_fd, 'pf.tol', 1e-8);
mpopt_fd = mpoption(mpopt_fd, 'pf.fd.max_it', 1000);
mpopt_fd = mpoption(mpopt_fd, 'pf.enforce_q_lims', 0);

tic;
results_ac = runpf(mpc_ac, mpopt_fd);
acpf_time = toc;

if ~results_ac.success
    % ---- Attempt 2: Relaxed tolerance FDXB ----
    fprintf('\n--- Attempt 2: FDXB with relaxed tolerance (1e-4) ---\n');
    mpopt_fd2 = mpoption(mpopt_fd, 'pf.tol', 1e-4);
    tic;
    results_ac = runpf(mpc_ac, mpopt_fd2);
    acpf_time = toc;

    if results_ac.success
        fprintf('FDXB converged at 1e-4, refining with NR...\n');
        % Refine with NR from the FD solution
        mpopt_nr = mpoption('verbose', 2, 'out.all', 0);
        mpopt_nr = mpoption(mpopt_nr, 'pf.alg', 'NR');
        mpopt_nr = mpoption(mpopt_nr, 'pf.tol', 1e-8);
        mpopt_nr = mpoption(mpopt_nr, 'pf.nr.max_it', 50);
        mpopt_nr = mpoption(mpopt_nr, 'pf.enforce_q_lims', 0);
        tic;
        results_refined = runpf(results_ac, mpopt_nr);
        refine_time = toc;
        if results_refined.success
            results_ac = results_refined;
            acpf_time = acpf_time + refine_time;
            fprintf('NR refinement converged in %.2f seconds\n', refine_time);
        else
            fprintf('NR refinement failed -- using FD solution at 1e-4\n');
        end
    end
end

if ~results_ac.success
    % ---- Attempt 3: Newton-Raphson from DC warm start ----
    fprintf('\n--- Attempt 3: Newton-Raphson from DC warm start ---\n');
    mpopt_nr = mpoption('verbose', 2, 'out.all', 0);
    mpopt_nr = mpoption(mpopt_nr, 'pf.alg', 'NR');
    mpopt_nr = mpoption(mpopt_nr, 'pf.tol', 1e-8);
    mpopt_nr = mpoption(mpopt_nr, 'pf.nr.max_it', 100);
    mpopt_nr = mpoption(mpopt_nr, 'pf.enforce_q_lims', 0);
    tic;
    results_ac = runpf(mpc_ac, mpopt_nr);
    acpf_time = toc;
end

if ~results_ac.success
    % ---- Attempt 4: Gauss-Seidel warm-up then NR ----
    fprintf('\n--- Attempt 4: Gauss-Seidel (200 iter) then NR ---\n');
    mpopt_gs = mpoption('verbose', 2, 'out.all', 0);
    mpopt_gs = mpoption(mpopt_gs, 'pf.alg', 'GS');
    mpopt_gs = mpoption(mpopt_gs, 'pf.tol', 1e-2);
    mpopt_gs = mpoption(mpopt_gs, 'pf.gs.max_it', 200);
    mpopt_gs = mpoption(mpopt_gs, 'pf.enforce_q_lims', 0);
    results_gs = runpf(mpc_ac, mpopt_gs);
    if results_gs.success
        mpopt_nr2 = mpoption('verbose', 2, 'out.all', 0);
        mpopt_nr2 = mpoption(mpopt_nr2, 'pf.tol', 1e-8);
        mpopt_nr2 = mpoption(mpopt_nr2, 'pf.nr.max_it', 100);
        mpopt_nr2 = mpoption(mpopt_nr2, 'pf.enforce_q_lims', 0);
        tic;
        results_ac = runpf(results_gs, mpopt_nr2);
        acpf_time = toc;
    end
end

% Q-limit enforcement stage (if base converged)
q_enforced = false;
if results_ac.success
    fprintf('ACPF base CONVERGED in %.2f seconds (%d iterations)\n', ...
            acpf_time, results_ac.iterations);

    mpopt_ql = mpoption('verbose', 2, 'out.all', 0);
    mpopt_ql = mpoption(mpopt_ql, 'pf.tol', 1e-8);
    mpopt_ql = mpoption(mpopt_ql, 'pf.nr.max_it', 100);
    mpopt_ql = mpoption(mpopt_ql, 'pf.enforce_q_lims', 1);
    tic;
    results_ql = runpf(results_ac, mpopt_ql);
    ql_time = toc;

    if results_ql.success
        fprintf('ACPF Q-limit enforcement CONVERGED in %.2f seconds\n', ql_time);
        results_ac = results_ql;
        q_enforced = true;
        acpf_time = acpf_time + ql_time;
    else
        fprintf('Q-limit enforcement FAILED -- using base solution\n');
    end
else
    fprintf('ACPF FAILED on all attempts\n');
end

% Write ACPF outputs
acpf_dir = fullfile(fnm_dir, 'reference', 'acpf');
if ~exist(acpf_dir, 'dir')
    mkdir(acpf_dir);
end

% runpf returns results in external numbering
results_ac_ext = results_ac;

% Remove isolated buses from count
bus_ac = results_ac_ext.bus;
n_isolated = sum(bus_ac(:, 2) == 4);

% buses_acpf.csv: bus_number, vm_pu, va_deg, pd_mw, qd_mvar, bus_type
fid = fopen(fullfile(acpf_dir, 'buses_acpf.csv'), 'w');
fprintf(fid, 'bus_number,vm_pu,va_deg,pd_mw,qd_mvar,bus_type\n');
for i = 1:size(bus_ac, 1)
    if bus_ac(i, 2) == 4
        continue
    end
    fprintf(fid, '%d,%.8f,%.8f,%.4f,%.4f,%d\n', ...
            bus_ac(i, 1), bus_ac(i, 8), bus_ac(i, 9), bus_ac(i, 3), bus_ac(i, 4), bus_ac(i, 2));
end
fclose(fid);

% branches_acpf.csv: from_bus, to_bus, pf_mw, qf_mvar, pt_mw, qt_mvar, status
br_ac = results_ac_ext.branch;
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

% generators_acpf.csv: bus_number, pg_mw, qg_mvar, status, vm_setpoint
gen_ac = results_ac_ext.gen;
fid = fopen(fullfile(acpf_dir, 'generators_acpf.csv'), 'w');
fprintf(fid, 'bus_number,pg_mw,qg_mvar,status,vm_setpoint\n');
for i = 1:size(gen_ac, 1)
    if gen_ac(i, 8) <= 0
        continue
    end
    fprintf(fid, '%d,%.8f,%.8f,%d,%.8f\n', ...
            gen_ac(i, 1), gen_ac(i, 2), gen_ac(i, 3), gen_ac(i, 8), gen_ac(i, 6));
end
fclose(fid);

% summary_acpf.json
active_gens = gen_ac(gen_ac(:, 8) > 0, :);
active_buses = bus_ac(bus_ac(:, 2) ~= 4, :);
total_gen_mw_ac = sum(active_gens(:, 2));
total_gen_mvar_ac = sum(active_gens(:, 3));
total_load_mw_ac = sum(active_buses(:, 3));
total_load_mvar_ac = sum(active_buses(:, 4));
losses_mw = total_gen_mw_ac - total_load_mw_ac;

fid = fopen(fullfile(acpf_dir, 'summary_acpf.json'), 'w');
fprintf(fid, '{\n');
fprintf(fid, '  "success": %d,\n', results_ac.success);
fprintf(fid, '  "wall_clock_seconds": %.4f,\n', acpf_time);
fprintf(fid, '  "iterations": %d,\n', results_ac.iterations);
fprintf(fid, '  "total_gen_mw": %.4f,\n', total_gen_mw_ac);
fprintf(fid, '  "total_gen_mvar": %.4f,\n', total_gen_mvar_ac);
fprintf(fid, '  "total_load_mw": %.4f,\n', total_load_mw_ac);
fprintf(fid, '  "total_load_mvar": %.4f,\n', total_load_mvar_ac);
fprintf(fid, '  "losses_mw": %.4f,\n', losses_mw);
fprintf(fid, '  "n_buses": %d,\n', size(active_buses, 1));
fprintf(fid, '  "n_branches": %d,\n', sum(br_ac(:, 11) ~= 0));
fprintf(fid, '  "n_gens": %d,\n', size(active_gens, 1));
fprintf(fid, '  "solver": "Newton-Raphson",\n');
fprintf(fid, '  "tolerance": 1e-8,\n');
fprintf(fid, '  "q_limits_enforced": %s,\n', mat2str(q_enforced));
fprintf(fid, '  "isolated_buses_removed": %d,\n', n_isolated);
fprintf(fid, '  "main_island_only": true,\n');
fprintf(fid, '  "initial_conditions": "dcpf_warm_start_flat_vm"\n');
fprintf(fid, '}\n');
fclose(fid);
fprintf('ACPF reference written to %s\n', acpf_dir);

fprintf('\n=== DONE ===\n');
