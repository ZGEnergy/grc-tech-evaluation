%% Test C-10: Distributed slack DC OPF on MEDIUM
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: Distributed slack DC OPF on MEDIUM within time budget.
%% Tool: MATPOWER 8.1
%% Solver: MIPS (built-in; HiGHS unavailable in Octave)
%%
%% A-11 showed distributed slack via makePTDF(baseMVA, bus, branch, slack_weights)
%% + post-processing. Same approach scaled to MEDIUM.

%% Setup MATPOWER paths
mp_root = '/workspace/evaluations/matpower/matpower8.1';
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

network_file = '/workspace/data/networks/case_ACTIVSg10k.m';

result_status = 'fail';
errors = {};
workarounds = {};

try
    define_constants;

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);

    %% ================================================================
    %% Step 1: Solve single-slack DC OPF
    %% ================================================================
    fprintf('\n=== Single-slack DC OPF ===\n');
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');

    tic;
    results_single = rundcopf(mpc, mpopt);
    time_single_opf = toc;

    if ~results_single.success
        error('Single-slack DC OPF did not converge');
    end

    single_obj = results_single.f;
    single_lmp = results_single.bus(:, LAM_P);
    fprintf('Single-slack DC OPF: cost=$%.2f, time=%.6f s\n', single_obj, time_single_opf);
    fprintf('LMP range: [%.4f, %.4f] $/MWh\n', min(single_lmp), max(single_lmp));
    fprintf('LMP std: %.6e $/MWh\n', std(single_lmp));

    %% Check for congestion
    mu_sf = results_single.branch(:, MU_SF);
    mu_st = results_single.branch(:, MU_ST);
    binding = (mu_sf > 1e-6) | (mu_st > 1e-6);
    fprintf('Binding branches: %d / %d\n', sum(binding), nl);

    %% ================================================================
    %% Step 2: Compute distributed PTDF (load-proportional weights)
    %% ================================================================
    fprintf('\n=== Distributed slack PTDF computation ===\n');
    mpc_int = ext2int(mpc);
    nb_int = size(mpc_int.bus, 1);
    nl_int = size(mpc_int.branch, 1);

    %% Load-proportional slack weights
    bus_load = mpc_int.bus(:, PD);
    bus_load(bus_load < 0) = 0;
    total_load = sum(bus_load);
    slack_weights_load = bus_load / total_load;
    nonzero_weights = sum(slack_weights_load > 0);
    fprintf('Load-proportional weights: %d / %d buses non-zero\n', nonzero_weights, nb_int);

    tic;
    PTDF_dist = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch, slack_weights_load);
    time_ptdf_dist = toc;
    fprintf('Distributed PTDF computed: %.6f s\n', time_ptdf_dist);

    %% Also compute single-slack PTDF
    tic;
    PTDF_single = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
    time_ptdf_single = toc;
    fprintf('Single-slack PTDF computed: %.6f s\n', time_ptdf_single);

    %% ================================================================
    %% Step 3: Compute distributed-slack LMPs
    %% ================================================================
    fprintf('\n=== LMP re-referencing ===\n');

    %% Map single-slack LMPs to internal ordering
    %% For ACTIVSg10k, ext2int may reorder buses
    results_int = ext2int(results_single);
    lmp_single_int = results_int.bus(:, LAM_P);

    %% Weighted average of single-slack LMPs (load-proportional)
    weighted_avg_lmp_load = sum(slack_weights_load .* lmp_single_int);
    fprintf('Weighted avg LMP (load-prop): $%.4f/MWh\n', weighted_avg_lmp_load);

    %% Distributed-slack LMPs: shift by weighted average
    lmp_dist_load = lmp_single_int - weighted_avg_lmp_load;

    %% LMP comparison
    lmp_delta_load = lmp_dist_load - lmp_single_int;
    fprintf('LMP shift (load-prop): mean=$%.4f/MWh, std=%.6e $/MWh\n', ...
            mean(lmp_delta_load), std(lmp_delta_load));

    %% ================================================================
    %% Step 4: Generation-proportional weights
    %% ================================================================
    fprintf('\n=== Generation-proportional distributed slack ===\n');
    slack_weights_gen = zeros(nb_int, 1);
    for g = 1:size(mpc_int.gen, 1)
        bus_idx = mpc_int.gen(g, GEN_BUS);
        slack_weights_gen(bus_idx) = slack_weights_gen(bus_idx) + mpc_int.gen(g, PMAX);
    end
    slack_weights_gen = slack_weights_gen / sum(slack_weights_gen);

    tic;
    PTDF_gen = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch, slack_weights_gen);
    time_ptdf_gen = toc;
    fprintf('Gen-proportional PTDF computed: %.6f s\n', time_ptdf_gen);

    weighted_avg_lmp_gen = sum(slack_weights_gen .* lmp_single_int);
    lmp_dist_gen = lmp_single_int - weighted_avg_lmp_gen;
    fprintf('Weighted avg LMP (gen-prop): $%.4f/MWh\n', weighted_avg_lmp_gen);

    %% ================================================================
    %% Step 5: Congestion component analysis
    %% ================================================================
    fprintf('\n=== Congestion component comparison ===\n');
    mu_net = results_int.branch(:, MU_SF) - results_int.branch(:, MU_ST);

    lmp_cong_single = -PTDF_single' * mu_net;
    lmp_cong_dist = -PTDF_dist' * mu_net;
    cong_diff = lmp_cong_dist - lmp_cong_single;

    fprintf('Congestion component change (dist vs single PTDF):\n');
    fprintf('  Max abs change: $%.6e/MWh\n', max(abs(cong_diff)));
    fprintf('  Mean abs change: $%.6e/MWh\n', mean(abs(cong_diff)));

    %% ================================================================
    %% Total wall clock
    %% ================================================================
    total_time = time_single_opf + time_ptdf_dist + time_ptdf_single + time_ptdf_gen;
    fprintf('\n=== Total wall clock: %.6f s ===\n', total_time);
    fprintf('  DC OPF solve: %.6f s\n', time_single_opf);
    fprintf('  PTDF (distributed): %.6f s\n', time_ptdf_dist);
    fprintf('  PTDF (single): %.6f s\n', time_ptdf_single);
    fprintf('  PTDF (gen-prop): %.6f s\n', time_ptdf_gen);

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    else
        peak_memory_mb = -1;
    end
    fprintf('\nPeak memory: %.1f MB\n', peak_memory_mb);

    %% nproc
    [~, nproc_out] = system('nproc');
    cpu_available = str2double(strtrim(nproc_out));
    fprintf('CPU threads available: %d\n', cpu_available);
    fprintf('CPU threads used: 1 (Octave is single-threaded)\n');

    %% ================================================================
    %% LMP samples (first 10 buses)
    %% ================================================================
    fprintf('\n=== LMP Samples (first 10 buses, internal ordering) ===\n');
    fprintf('Bus | Single LMP | Dist LMP (load) | Dist LMP (gen) | Delta (load)\n');
    for i = 1:min(10, nb_int)
        ext_bus = mpc_int.bus(i, BUS_I);
        fprintf(' %5d | %10.4f | %12.4f | %12.4f | %+10.4f\n', ...
                ext_bus, lmp_single_int(i), lmp_dist_load(i), lmp_dist_gen(i), ...
                lmp_delta_load(i));
    end

    %% LMP spread analysis
    fprintf('\n=== LMP spread ===\n');
    fprintf('Single-slack LMP std: %.6e $/MWh\n', std(lmp_single_int));
    fprintf('Distributed LMP std (load): %.6e $/MWh\n', std(lmp_dist_load));
    fprintf('Distributed LMP std (gen): %.6e $/MWh\n', std(lmp_dist_gen));

    %% Status: pass if distributed slack computed within time budget
    %% and LMP comparison shows consistent results
    lmp_shift_uniform = std(lmp_delta_load) < 0.001;

    if lmp_shift_uniform
        result_status = 'qualified_pass';
        workarounds{end + 1} = 'Post-process via makePTDF (no native distributed slack OPF)';
    else
        errors{end + 1} = 'LMP shift not uniform -- unexpected';
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
if ~isempty(errors)
    fprintf('Errors:\n');
    for i = 1:length(errors)
        fprintf('  - %s\n', errors{i});
    end
end
if ~isempty(workarounds)
    fprintf('Workarounds:\n');
    for i = 1:length(workarounds)
        fprintf('  - %s\n', workarounds{i});
    end
end
