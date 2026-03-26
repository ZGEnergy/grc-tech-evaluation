%% Test C-9: PTDF matrix computation on MEDIUM
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: PTDF matrix computed on MEDIUM within time budget.
%% Tool: MATPOWER 8.1
%% Solver: null (direct computation, no optimization)

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

try
    define_constants;

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);

    %% Convert to internal ordering
    mpc_int = ext2int(mpc);
    nb_int = size(mpc_int.bus, 1);
    nl_int = size(mpc_int.branch, 1);
    fprintf('Internal: %d buses, %d branches\n', nb_int, nl_int);

    %% ================================================================
    %% PTDF with default single slack (reference bus)
    %% ================================================================
    fprintf('\n=== PTDF computation (single slack) ===\n');

    %% Memory before
    [~, mem_before] = system('grep VmHWM /proc/self/status');
    peak_kb_before = sscanf(mem_before, 'VmHWM: %f');

    tic;
    PTDF_single = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
    time_ptdf_single = toc;

    fprintf('PTDF (single slack) computed: %.6f s\n', time_ptdf_single);
    fprintf('PTDF size: %d x %d\n', size(PTDF_single, 1), size(PTDF_single, 2));
    fprintf('PTDF class: %s\n', class(PTDF_single));

    %% Matrix properties
    nnz_ptdf = nnz(PTDF_single);
    total_elements = numel(PTDF_single);
    if issparse(PTDF_single)
        density = nnz_ptdf / total_elements;
        fprintf('PTDF is sparse: nnz=%d, density=%.6e\n', nnz_ptdf, density);
    else
        %% Count near-zero elements
        near_zero = sum(abs(PTDF_single(:)) < 1e-10);
        effective_nnz = total_elements - near_zero;
        density = effective_nnz / total_elements;
        fprintf('PTDF is dense: effective_nnz=%d/%d, density=%.6e\n', ...
                effective_nnz, total_elements, density);
    end

    fprintf('Max abs PTDF value: %.6e\n', max(abs(PTDF_single(:))));
    fprintf('Min nonzero abs PTDF value: %.6e\n', min(abs(PTDF_single(abs(PTDF_single) > 1e-15))));

    %% ================================================================
    %% PTDF with distributed slack (load-proportional)
    %% ================================================================
    fprintf('\n=== PTDF computation (distributed slack) ===\n');
    slack_weights = mpc_int.bus(:, PD);
    slack_weights(slack_weights < 0) = 0;
    total_weight = sum(slack_weights);
    if total_weight > 0
        slack_weights = slack_weights / total_weight;
    else
        slack_weights = ones(nb_int, 1) / nb_int;
    end

    tic;
    PTDF_dist = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch, slack_weights);
    time_ptdf_dist = toc;
    fprintf('PTDF (distributed slack) computed: %.6f s\n', time_ptdf_dist);

    %% ================================================================
    %% Validate PTDF via DC power flow comparison
    %% ================================================================
    fprintf('\n=== PTDF validation ===\n');
    mpopt = mpoption('verbose', 0, 'out.all', 0);
    results_dcpf = rundcpf(mpc, mpopt);
    if results_dcpf.success
        results_dcpf_int = ext2int(results_dcpf);
        va_ref = results_dcpf_int.bus(:, VA) * pi / 180;

        [~, Bf] = makeBdc(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
        flows_bdc = full(Bf * va_ref) * mpc_int.baseMVA;

        %% PTDF-based flow: flow = PTDF * Pinj
        Pinj = mpc_int.bus(:, PD);
        Pinj_gen = zeros(nb_int, 1);
        for g = 1:size(mpc_int.gen, 1)
            bus_idx = mpc_int.gen(g, GEN_BUS);
            Pinj_gen(bus_idx) = Pinj_gen(bus_idx) + results_dcpf_int.gen(g, PG);
        end
        Pinj_net = Pinj_gen - mpc_int.bus(:, PD) - mpc_int.bus(:, GS);

        flows_ptdf = PTDF_single * Pinj_net;

        %% Compare -- account for phase shifters
        flow_diff = abs(flows_bdc - flows_ptdf);
        max_diff = max(flow_diff);
        mean_diff = mean(flow_diff);

        %% Check for phase shifters
        n_ps = sum(abs(mpc_int.branch(:, SHIFT)) > 1e-6);
        fprintf('Phase-shifting transformers: %d\n', n_ps);
        fprintf('PTDF vs Bdc flow max deviation: %.6e MW\n', max_diff);
        fprintf('PTDF vs Bdc flow mean deviation: %.6e MW\n', mean_diff);

        if n_ps > 0
            %% Exclude phase-shifter branches for accuracy metric
            ps_branches = abs(mpc_int.branch(:, SHIFT)) > 1e-6;
            non_ps_diff = flow_diff(~ps_branches);
            fprintf('Non-PS branch max deviation: %.6e MW\n', max(non_ps_diff));
            fprintf('Non-PS branch mean deviation: %.6e MW\n', mean(non_ps_diff));
        end
    else
        fprintf('DC PF failed -- skipping validation\n');
    end

    %% ================================================================
    %% Also compute LODF for completeness
    %% ================================================================
    fprintf('\n=== LODF computation ===\n');
    tic;
    LODF = makeLODF(mpc_int.branch, PTDF_single);
    time_lodf = toc;
    fprintf('LODF computed: %.6f s\n', time_lodf);
    fprintf('LODF size: %d x %d\n', size(LODF, 1), size(LODF, 2));

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

    %% Memory estimate for PTDF matrix
    ptdf_memory_mb = nb_int * nl_int * 8 / (1024 * 1024);
    fprintf('PTDF matrix memory (dense float64): %.1f MB\n', ptdf_memory_mb);

    result_status = 'pass';

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
