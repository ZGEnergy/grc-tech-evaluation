%% Test C-8: SCOPF with 50 contingencies on MEDIUM
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: Completes SCOPF with 50 contingencies on MEDIUM.
%% Tool: MATPOWER 8.1
%% Solver: MIPS (built-in; HiGHS unavailable in Octave)
%%
%% MATPOWER has no native turnkey SCOPF -- uses LODF-based constraint injection
%% via mpc.A/l/u with Benders-style cut generation.

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
benders_iters = 0;
peak_memory_mb = -1;
time_scopf = 0;

try
    define_constants;

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);
    fprintf('Branches with RATE_A=0 (unlimited): %d\n', sum(mpc.branch(:, RATE_A) == 0));

    nvar = nb + ng;

    %% Step 1: Solve base-case DC OPF (no derating)
    mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'MIPS');

    tic;
    results_base = rundcopf(mpc, mpopt);
    time_base = toc;

    if ~results_base.success
        error('Base-case DC OPF did not converge');
    end

    base_cost = results_base.f;
    base_gen = results_base.gen(:, PG);
    fprintf('Base-case DC OPF (MIPS): cost=$%.2f, time=%.3f s\n', base_cost, time_base);

    mu_sf = results_base.branch(:, MU_SF);
    mu_st = results_base.branch(:, MU_ST);
    binding_base = sum((mu_sf > 1e-6) | (mu_st > 1e-6));
    lmp_base = results_base.bus(:, LAM_P);
    fprintf('Binding branches: %d / %d\n', binding_base, nl);
    fprintf('LMP range: [%.4f, %.4f] $/MWh\n', min(lmp_base), max(lmp_base));

    %% Step 2: Build PTDF and LODF
    fprintf('\n=== Building PTDF/LODF matrices ===\n');
    mpc_int = ext2int(mpc);
    nb_int = size(mpc_int.bus, 1);
    nl_int = size(mpc_int.branch, 1);

    tic;
    PTDF = makePTDF(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);
    time_ptdf = toc;
    fprintf('PTDF computed: %.3f s\n', time_ptdf);

    tic;
    LODF = makeLODF(mpc_int.branch, PTDF);
    time_lodf = toc;
    fprintf('LODF computed: %.3f s\n', time_lodf);

    [~, Bf] = makeBdc(mpc_int.baseMVA, mpc_int.bus, mpc_int.branch);

    %% Step 3: Select 50 contingencies (most loaded non-radial branches)
    fprintf('\n=== Selecting 50 contingencies ===\n');
    results_int = ext2int(results_base);
    va_int = results_int.bus(:, VA) * pi / 180;
    base_flows_mw = full(Bf * va_int) * mpc_int.baseMVA;
    rate_a_int = mpc_int.branch(:, RATE_A);

    loading = zeros(nl_int, 1);
    for l = 1:nl_int
        if rate_a_int(l) > 0
            loading(l) = abs(base_flows_mw(l)) / rate_a_int(l);
        end
    end

    in_service = find(mpc_int.branch(:, BR_STATUS) == 1);
    valid_cont = [];
    for k = 1:length(in_service)
        br = in_service(k);
        col = LODF(:, br);
        if ~any(isinf(col) | isnan(col))
            valid_cont = [valid_cont; br];
        end
    end
    fprintf('Valid (non-radial) contingency branches: %d\n', length(valid_cont));

    [~, si] = sort(loading(valid_cont), 'descend');
    n_cont = min(50, length(valid_cont));
    cont_branches = valid_cont(si(1:n_cont));
    fprintf('Selected %d contingencies\n', n_cont);
    fprintf('Loading range: %.1f%% to %.1f%%\n', ...
            100 * loading(cont_branches(end)), 100 * loading(cont_branches(1)));

    %% Step 4: N-1 screening
    fprintf('\n=== N-1 screening ===\n');
    rate_a_pu = rate_a_int / mpc_int.baseMVA;
    total_violations = 0;
    worst_overload = 0;
    for k = 1:n_cont
        k_br = cont_branches(k);
        for l = 1:nl_int
            if l == k_br || rate_a_int(l) <= 0; continue; end
            lodf_val = LODF(l, k_br);
            if abs(lodf_val) < 0.01 || isinf(lodf_val) || isnan(lodf_val); continue; end
            post_flow = abs(base_flows_mw(l) + lodf_val * base_flows_mw(k_br));
            if post_flow > rate_a_int(l) * 1.005
                total_violations = total_violations + 1;
                overload = post_flow / rate_a_int(l);
                if overload > worst_overload; worst_overload = overload; end
            end
        end
    end
    fprintf('Post-contingency violations: %d (worst overload: %.1f%%)\n', ...
            total_violations, 100 * worst_overload);

    %% Step 5: Benders SCOPF (worst violation per contingency)
    fprintf('\n=== Benders SCOPF (MIPS, 1 thread) ===\n');
    mpc_iter = mpc;
    all_A = [];
    all_l = [];
    all_u = [];
    added_keys = {};
    benders_converged = false;
    scopf_cost = 0;
    last_success = false;

    tic;
    for benders_iter = 1:20
        benders_iters = benders_iter;
        results_iter = rundcopf(mpc_iter, mpopt);

        if ~results_iter.success
            fprintf('Benders iter %d: SOLVER FAILED with %d user constraints\n', ...
                    benders_iter, size(all_A, 1));
            errors{end + 1} = sprintf('MIPS solver failed at Benders iter %d with %d constraints [solver-specific: MIPS numerical singularity on 10k with user constraints]', ...
                                       benders_iter, size(all_A, 1));
            last_success = false;
            break;
        end

        last_success = true;
        scopf_cost = results_iter.f;
        results_iter_int = ext2int(results_iter);
        va_iter = results_iter_int.bus(:, VA) * pi / 180;
        flows_iter = full(Bf * va_iter) * mpc_int.baseMVA;

        new_violations = 0;
        for k = 1:n_cont
            k_br = cont_branches(k);
            worst_l = -1;
            worst_over = 0;
            for l = 1:nl_int
                if l == k_br || rate_a_int(l) <= 0; continue; end
                lodf_val = LODF(l, k_br);
                if abs(lodf_val) < 0.01 || isinf(lodf_val) || isnan(lodf_val); continue; end
                post_flow = abs(flows_iter(l) + lodf_val * flows_iter(k_br));
                if post_flow > rate_a_int(l) * 1.005
                    overload = post_flow / rate_a_int(l);
                    key = sprintf('%d_%d', k_br, l);
                    if overload > worst_over && ~any(strcmp(added_keys, key))
                        worst_over = overload;
                        worst_l = l;
                    end
                end
            end
            if worst_l > 0
                new_violations = new_violations + 1;
                key = sprintf('%d_%d', k_br, worst_l);
                added_keys{end + 1} = key;
                lodf_val = LODF(worst_l, k_br);
                coeff = full(Bf(worst_l, :) + lodf_val * Bf(k_br, :));
                row = sparse(1, nvar);
                row(1, 1:nb_int) = coeff;
                all_A = [all_A; row];
                all_l = [all_l; -rate_a_pu(worst_l)];
                all_u = [all_u; rate_a_pu(worst_l)];
            end
        end

        fprintf('Benders iter %d: cost=$%.2f, new_cuts=%d, total=%d\n', ...
                benders_iter, scopf_cost, new_violations, size(all_A, 1));

        if new_violations == 0
            benders_converged = true;
            fprintf('Benders CONVERGED after %d iterations\n', benders_iter);
            break;
        end

        mpc_iter = mpc;
        mpc_iter.A = all_A;
        mpc_iter.l = all_l;
        mpc_iter.u = all_u;
    end
    time_scopf = toc;
    fprintf('SCOPF wall clock: %.3f s\n', time_scopf);

    %% Compute redispatch if any iteration succeeded
    redispatch_mw = 0;
    if last_success && benders_iters >= 1
        scopf_gen = results_iter.gen(:, PG);
        redispatch_mw = sum(abs(scopf_gen - base_gen));
        max_gen_shift = max(abs(scopf_gen - base_gen));
        fprintf('\nSCOPF cost: $%.2f (base: $%.2f, premium: $%.2f)\n', ...
                scopf_cost, base_cost, scopf_cost - base_cost);
        fprintf('Total redispatch: %.2f MW\n', redispatch_mw);
        fprintf('Max single-gen shift: %.2f MW\n', max_gen_shift);
    end

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end
    fprintf('\nPeak memory: %.1f MB\n', peak_memory_mb);

    [~, nproc_out] = system('nproc');
    cpu_available = str2double(strtrim(nproc_out));
    fprintf('CPU threads available: %d\n', cpu_available);
    fprintf('CPU threads used: 1 (Octave is single-threaded)\n');

    %% Status assessment
    if benders_converged && redispatch_mw >= 5.0
        result_status = 'qualified_pass';
        workarounds{end + 1} = 'No native SCOPF; LODF-based constraint injection via mpc.A/l/u';
    elseif benders_converged
        result_status = 'constrained_pass';
        workarounds{end + 1} = 'SCOPF converged but minimal redispatch (uncongested base case)';
    elseif benders_iters >= 2 && ~last_success
        %% Benders started but solver failed on augmented problem
        result_status = 'fail';
        workarounds{end + 1} = 'LODF constraint injection via mpc.A/l/u works mechanically but MIPS fails numerically at MEDIUM scale with user constraints';
    else
        result_status = 'fail';
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Benders iterations: %d\n', benders_iters);
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
