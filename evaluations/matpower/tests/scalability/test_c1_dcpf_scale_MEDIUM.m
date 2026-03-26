%% Test C-1: DCPF on MEDIUM (ACTIVSg 10k)
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: Completes DCPF on MEDIUM within time budget.
%% Tool: MATPOWER 8.1

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
solve_time = 0;
peak_memory_mb = -1;

try
    define_constants;

    %% Baseline memory before load
    [~, mem_before] = system('grep VmRSS /proc/self/status');
    rss_before_kb = sscanf(mem_before, 'VmRSS: %f');

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);

    %% Configure options
    mpopt = mpoption('verbose', 0, 'out.all', 0);

    %% Solve DCPF -- timed
    tic;
    results = rundcpf(mpc, mpopt);
    solve_time = toc;

    %% Peak memory after solve
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end

    %% Current RSS
    [~, mem_rss] = system('grep VmRSS /proc/self/status');
    rss_kb = sscanf(mem_rss, 'VmRSS: %f');
    rss_mb = rss_kb / 1024;

    if results.success
        %% Extract key results for verification
        va = results.bus(:, VA);
        nonzero_angles = sum(abs(va) > 1e-6);
        max_flow = max(abs(results.branch(:, PF)));
        total_gen = sum(results.gen(:, PG));
        total_load = sum(results.bus(:, PD));

        fprintf('\n=== Test C-1: DCPF MEDIUM Results ===\n');
        fprintf('Status: CONVERGED\n');
        fprintf('Wall clock: %.6f s\n', solve_time);
        fprintf('Peak memory (VmHWM): %.1f MB\n', peak_memory_mb);
        fprintf('Current RSS: %.1f MB\n', rss_mb);
        fprintf('Total generation: %.2f MW\n', total_gen);
        fprintf('Total load: %.2f MW\n', total_load);
        fprintf('Max branch flow: %.2f MW\n', max_flow);
        fprintf('Nonzero voltage angles: %d / %d\n', nonzero_angles, nb);
        fprintf('Angle range: [%.4f, %.4f] deg\n', min(va), max(va));

        result_status = 'pass';
    else
        errors{end + 1} = 'DCPF did not converge on MEDIUM network';
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Wall clock: %.6f s\n', solve_time);
fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
if ~isempty(errors)
    fprintf('Errors:\n');
    for i = 1:length(errors)
        fprintf('  - %s\n', errors{i});
    end
end
