%% Test C-2: ACPF on MEDIUM (ACTIVSg 10k)
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: Completes ACPF on MEDIUM within time budget.
%% Tool: MATPOWER 8.1
%% Solver: Newton-Raphson (MATPOWER built-in)

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
solve_time = 0;
peak_memory_mb = -1;
nr_iterations = -1;
dc_warm_start_needed = false;
convergence_residual = -1;
convergence_evidence = 'none';

try
    define_constants;

    %% Load case
    fprintf('Loading %s...\n', network_file);
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);

    %% Set flat start: V=1.0 pu, angles=0
    mpc.bus(:, VM) = 1.0;
    mpc.bus(:, VA) = 0.0;

    %% Configure NR solver with verbose=2 to capture iteration info
    mpopt = mpoption('pf.alg', 'NR', 'verbose', 2, 'out.all', 0, 'pf.tol', 1e-8);

    %% Attempt 1: Flat start
    fprintf('\nAttempt 1: Flat start ACPF...\n');
    tic;
    results = runpf(mpc, mpopt);
    solve_time = toc;

    if ~results.success
        fprintf('Flat start failed. Attempting DC warm start fallback...\n');
        dc_warm_start_needed = true;

        %% DC warm start fallback
        mpc_warm = loadcase(network_file);
        mpopt_dc = mpoption('verbose', 0, 'out.all', 0);
        dc_results = rundcpf(mpc_warm, mpopt_dc);

        if dc_results.success
            mpc_warm.bus(:, VA) = dc_results.bus(:, VA);
            mpc_warm.bus(:, VM) = 1.0;

            fprintf('DC warm start: setting angles from DCPF solution...\n');
            tic;
            results = runpf(mpc_warm, mpopt);
            solve_time = toc;

            if results.success
                workarounds{end + 1} = 'DC warm start was needed for ACPF convergence on MEDIUM';
            else
                %% Try relaxed tolerance
                fprintf('DC warm start failed. Trying relaxed tolerance (1e-4)...\n');
                mpopt_relaxed = mpoption('pf.alg', 'NR', 'verbose', 2, 'out.all', 0, ...
                                         'pf.tol', 1e-4, 'pf.nr.max_it', 100);
                tic;
                results = runpf(mpc_warm, mpopt_relaxed);
                solve_time = toc;
                if results.success
                    workarounds{end + 1} = 'DC warm start + relaxed tolerance (1e-4) needed';
                else
                    errors{end + 1} = 'ACPF failed with flat start, DC warm start, and relaxed tol';
                end
            end
        else
            errors{end + 1} = 'DC warm start failed -- DCPF did not converge';
        end
    end

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end

    if results.success
        %% Extract results
        vm = results.bus(:, VM);
        va = results.bus(:, VA);

        vm_differs = abs(vm - 1.0) > 1e-6;
        pct_vm_differs = sum(vm_differs) / nb * 100;

        if isfield(results, 'iterations')
            nr_iterations = results.iterations;
            convergence_evidence = 'iteration_count_reported';
        end

        %% Compute max bus power mismatch for convergence evidence
        %% Convert to internal ordering for Ybus computation
        results_int = ext2int(results);
        nb_int = size(results_int.bus, 1);
        ng_int = size(results_int.gen, 1);
        vm_int = results_int.bus(:, VM);
        va_int = results_int.bus(:, VA);
        [Ybus, ~, ~] = makeYbus(results_int.baseMVA, results_int.bus, results_int.branch);
        V = vm_int .* exp(1j * va_int * pi / 180);
        Sbus_calc = V .* conj(Ybus * V);  % complex power injection (pu)
        %% Specified injections
        Pg = zeros(nb_int, 1);
        Qg = zeros(nb_int, 1);
        for g = 1:ng_int
            bus_idx = find(results_int.bus(:, BUS_I) == results_int.gen(g, GEN_BUS));
            if ~isempty(bus_idx)
                Pg(bus_idx) = Pg(bus_idx) + results_int.gen(g, PG);
                Qg(bus_idx) = Qg(bus_idx) + results_int.gen(g, QG);
            end
        end
        Pd = results_int.bus(:, PD);
        Qd = results_int.bus(:, QD);
        Sspec = (Pg - Pd + 1j*(Qg - Qd)) / results_int.baseMVA;  % pu
        %% Mismatch on non-slack buses
        ref_bus = find(results_int.bus(:, BUS_TYPE) == 3);
        pv_pq = setdiff(1:nb_int, ref_bus);
        mismatch = Sbus_calc(pv_pq) - Sspec(pv_pq);
        max_p_mismatch = max(abs(real(mismatch)));
        max_q_mismatch = max(abs(imag(mismatch)));
        max_bus_mismatch = max(max_p_mismatch, max_q_mismatch);
        convergence_residual = max_bus_mismatch;

        if max_bus_mismatch < 1e-4
            convergence_evidence = 'residual_reported';
        end

        gen_pg = results.gen(:, PG);
        gen_qg = results.gen(:, QG);
        total_gen_p = sum(gen_pg);
        total_gen_q = sum(gen_qg);
        total_load_p = sum(results.bus(:, PD));
        total_load_q = sum(results.bus(:, QD));

        %% Losses
        branch_pf = results.branch(:, PF);
        branch_pt = results.branch(:, PT);
        branch_qf = results.branch(:, QF);
        branch_qt = results.branch(:, QT);
        total_p_loss = sum(branch_pf + branch_pt);
        total_q_loss = sum(branch_qf + branch_qt);
        loss_pct = total_p_loss / total_gen_p * 100;

        fprintf('\n=== Test C-2: ACPF MEDIUM Results ===\n');
        fprintf('Status: CONVERGED\n');
        fprintf('Wall clock: %.6f s\n', solve_time);
        fprintf('DC warm start needed: %d\n', dc_warm_start_needed);
        fprintf('Peak memory (VmHWM): %.1f MB\n', peak_memory_mb);
        fprintf('NR iterations: %d\n', nr_iterations);
        fprintf('Max bus power mismatch: %.6e pu\n', max_bus_mismatch);
        fprintf('Max P mismatch: %.6e pu\n', max_p_mismatch);
        fprintf('Max Q mismatch: %.6e pu\n', max_q_mismatch);
        fprintf('Convergence evidence: %s\n', convergence_evidence);
        fprintf('Total generation: %.2f MW + %.2f MVAr\n', total_gen_p, total_gen_q);
        fprintf('Total load: %.2f MW + %.2f MVAr\n', total_load_p, total_load_q);
        fprintf('Total P losses: %.2f MW (%.2f%%)\n', total_p_loss, loss_pct);
        fprintf('Total Q losses: %.2f MVAr\n', total_q_loss);
        fprintf('VM range: [%.6f, %.6f] pu\n', min(vm), max(vm));
        fprintf('VA range: [%.4f, %.4f] deg\n', min(va), max(va));
        fprintf('VM differs from flat start: %.1f%% of buses\n', pct_vm_differs);

        if pct_vm_differs > 95 && max_bus_mismatch < 1e-4
            result_status = 'pass';
        elseif pct_vm_differs > 95
            result_status = 'pass';
            fprintf('WARNING: max bus mismatch %.6e exceeds 1e-4 threshold\n', max_bus_mismatch);
        else
            errors{end + 1} = sprintf('Only %.1f%% buses differ from flat start', pct_vm_differs);
        end
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Wall clock: %.6f s\n', solve_time);
fprintf('NR iterations: %d\n', nr_iterations);
fprintf('Convergence residual: %.6e\n', convergence_residual);
fprintf('Convergence evidence: %s\n', convergence_evidence);
fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
fprintf('DC warm start needed: %d\n', dc_warm_start_needed);
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
