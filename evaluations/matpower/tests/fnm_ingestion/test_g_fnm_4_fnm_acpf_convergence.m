%% Test G-FNM-4: ACPF convergence test with DCPF warm-start and progressive relaxation
%%
%% Dimension: fnm_ingestion
%% Network: LARGE (FNM Annual S01 -- main island, pre-cleaned .mat)
%% Pass condition: No hard pass/fail gate. All outcomes are diagnostic findings.
%%   Record relaxation_level_achieved: 0%, 10%, 20%, or infeasible.
%% Tool: MATPOWER 8.1
%% Input path: matpower (fallback .mat file)

fprintf('\n=== G-FNM-4: ACPF Convergence on Cleaned FNM ===\n\n');

%% Setup MATPOWER
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath('/workspace/evaluations/matpower/tests/fnm_ingestion');

define_constants;

%% Load cleaned FNM case
fprintf('Loading cleaned FNM case...\n');
mat_path = '/workspace/data/fnm/reference/cleaned/fnm_main_island.mat';
mpc = loadcase(mat_path);
fprintf('  Buses: %d\n', size(mpc.bus, 1));
fprintf('  Branches: %d\n', size(mpc.branch, 1));
fprintf('  Generators: %d\n', size(mpc.gen, 1));
fprintf('  baseMVA: %.1f\n', mpc.baseMVA);

%% Step 1: Solve DCPF for warm-start angles
fprintf('\n--- Step 1: DCPF for warm-start angles ---\n');
mpopt = mpoption('verbose', 0, 'out.all', 0);

tic_dcpf = tic;
dcpf_results = rundcpf(mpc, mpopt);
dcpf_time = toc(tic_dcpf);

fprintf('  DCPF success: %d\n', dcpf_results.success);
fprintf('  DCPF wall clock: %.3f seconds\n', dcpf_time);

if ~dcpf_results.success
    fprintf('\nFATAL: DCPF did not converge. Cannot proceed with ACPF.\n');
    return
end

dcpf_angles = dcpf_results.bus(:, VA);
dcpf_init_mean_deg = mean(abs(dcpf_angles));
dcpf_init_max_abs_deg = max(abs(dcpf_angles));

fprintf('  DCPF init mean angle: %.4f deg\n', dcpf_init_mean_deg);
fprintf('  DCPF init max |angle|: %.4f deg\n', dcpf_init_max_abs_deg);

%% Step 2: ACPF at 0% relaxation (nominal thermal limits)
fprintf('\n--- Step 2: ACPF at 0%% relaxation (nominal limits) ---\n');

mpc_ac = mpc;
mpc_ac.bus(:, VM) = 1.0;
mpc_ac.bus(:, VA) = dcpf_angles;

% Newton-Raphson with generous iteration limit
mpopt_ac = mpoption('verbose', 0, 'out.all', 0, ...
                    'pf.alg', 'NR', ...
                    'pf.nr.max_it', 100, ...
                    'pf.tol', 1e-8);

[~, rss_txt] = system('grep VmHWM /proc/self/status');
rss_before = sscanf(rss_txt, 'VmHWM: %f') / 1024;

tic_ac = tic;
acpf_results_0 = runpf(mpc_ac, mpopt_ac);
acpf_time_0 = toc(tic_ac);

[~, rss_txt] = system('grep VmHWM /proc/self/status');
rss_after_0 = sscanf(rss_txt, 'VmHWM: %f') / 1024;

fprintf('  ACPF (0%% relax) success: %d\n', acpf_results_0.success);
fprintf('  Wall clock: %.3f seconds\n', acpf_time_0);
fprintf('  Peak RSS: %.1f MB\n', rss_after_0);

relaxation_achieved = 'none_yet';

if acpf_results_0.success
    vm_vals = acpf_results_0.bus(:, VM);
    non_flat = sum(abs(vm_vals - 1.0) > 1e-6);
    non_flat_pct = non_flat / length(vm_vals) * 100;
    fprintf('  Non-flat VM buses: %d / %d (%.1f%%)\n', non_flat, length(vm_vals), non_flat_pct);
    fprintf('  VM range: [%.4f, %.4f] pu\n', min(vm_vals), max(vm_vals));
    fprintf('  VA range: [%.4f, %.4f] deg\n', min(acpf_results_0.bus(:, VA)), ...
            max(acpf_results_0.bus(:, VA)));

    total_gen_p = sum(acpf_results_0.gen(:, PG));
    total_load_p = sum(acpf_results_0.bus(:, PD));
    total_loss = total_gen_p - total_load_p;
    loss_pct = total_loss / total_load_p * 100;
    fprintf('  Total gen P: %.1f MW\n', total_gen_p);
    fprintf('  Total load P: %.1f MW\n', total_load_p);
    fprintf('  Total losses: %.1f MW (%.2f%%)\n', total_loss, loss_pct);

    relaxation_achieved = '0%';
    fprintf('\n  ACPF CONVERGED at 0%% relaxation.\n');
else
    fprintf('  ACPF did NOT converge at 0%% relaxation.\n');
end

%% Step 3: ACPF at 10% relaxation (if Step 2 failed)
if strcmp(relaxation_achieved, 'none_yet')
    fprintf('\n--- Step 3: ACPF at 10%% relaxation (RATE_A x 1.10) ---\n');

    mpc_ac_10 = mpc;
    mpc_ac_10.bus(:, VM) = 1.0;
    mpc_ac_10.bus(:, VA) = dcpf_angles;
    mpc_ac_10.branch(:, RATE_A) = mpc.branch(:, RATE_A) * 1.10;

    tic_ac_10 = tic;
    acpf_results_10 = runpf(mpc_ac_10, mpopt_ac);
    acpf_time_10 = toc(tic_ac_10);

    [~, rss_txt] = system('grep VmHWM /proc/self/status');
    rss_after_10 = sscanf(rss_txt, 'VmHWM: %f') / 1024;

    fprintf('  ACPF (10%% relax) success: %d\n', acpf_results_10.success);
    fprintf('  Wall clock: %.3f seconds\n', acpf_time_10);
    fprintf('  Peak RSS: %.1f MB\n', rss_after_10);

    if acpf_results_10.success
        vm_vals = acpf_results_10.bus(:, VM);
        non_flat = sum(abs(vm_vals - 1.0) > 1e-6);
        fprintf('  Non-flat VM buses: %d / %d (%.1f%%)\n', non_flat, length(vm_vals), ...
                non_flat / length(vm_vals) * 100);
        fprintf('  VM range: [%.4f, %.4f] pu\n', min(vm_vals), max(vm_vals));

        relaxation_achieved = '10%';
        fprintf('\n  ACPF CONVERGED at 10%% relaxation.\n');
    else
        fprintf('  ACPF did NOT converge at 10%% relaxation.\n');
    end
end

%% Step 4: ACPF at 20% relaxation (if Step 3 failed)
if strcmp(relaxation_achieved, 'none_yet')
    fprintf('\n--- Step 4: ACPF at 20%% relaxation (RATE_A x 1.20) ---\n');

    mpc_ac_20 = mpc;
    mpc_ac_20.bus(:, VM) = 1.0;
    mpc_ac_20.bus(:, VA) = dcpf_angles;
    mpc_ac_20.branch(:, RATE_A) = mpc.branch(:, RATE_A) * 1.20;

    tic_ac_20 = tic;
    acpf_results_20 = runpf(mpc_ac_20, mpopt_ac);
    acpf_time_20 = toc(tic_ac_20);

    [~, rss_txt] = system('grep VmHWM /proc/self/status');
    rss_after_20 = sscanf(rss_txt, 'VmHWM: %f') / 1024;

    fprintf('  ACPF (20%% relax) success: %d\n', acpf_results_20.success);
    fprintf('  Wall clock: %.3f seconds\n', acpf_time_20);
    fprintf('  Peak RSS: %.1f MB\n', rss_after_20);

    if acpf_results_20.success
        vm_vals = acpf_results_20.bus(:, VM);
        non_flat = sum(abs(vm_vals - 1.0) > 1e-6);
        fprintf('  Non-flat VM buses: %d / %d (%.1f%%)\n', non_flat, length(vm_vals), ...
                non_flat / length(vm_vals) * 100);
        fprintf('  VM range: [%.4f, %.4f] pu\n', min(vm_vals), max(vm_vals));

        relaxation_achieved = '20%';
        fprintf('\n  ACPF CONVERGED at 20%% relaxation.\n');
    else
        relaxation_achieved = 'infeasible';
        fprintf('\n  ACPF did NOT converge at 20%% relaxation.\n');
    end
end

%% Summary
fprintf('\n=== SUMMARY ===\n');
fprintf('DCPF warm-start: success\n');
fprintf('  dcpf_init_mean_deg: %.4f\n', dcpf_init_mean_deg);
fprintf('  dcpf_init_max_abs_deg: %.4f\n', dcpf_init_max_abs_deg);
fprintf('relaxation_level_achieved: %s\n', relaxation_achieved);
fprintf('Status: informational (no pass/fail gate)\n');
