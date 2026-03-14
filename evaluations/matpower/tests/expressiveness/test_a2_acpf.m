%% Test A-2: Solve AC power flow (Newton-Raphson) on TINY
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Converges. Convergence residual below tolerance. NR iterations
%%   reported. Voltage magnitudes differ from flat-start (1.0 pu) on >95% of buses.
%%   Bus V/angles, line P/Q flows, losses accessible.
%% Tool: MATPOWER 8.1

%% Setup MATPOWER paths
mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

network_file = '/workspace/data/networks/case39.m';

result_status = 'fail';
errors = {};
workarounds = {};
dc_warm_start_needed = false;

try
    %% Load case
    mpc = loadcase(network_file);
    define_constants;

    %% Set flat start: V=1.0 pu, angles=0 for all buses
    mpc.bus(:, VM) = 1.0;
    mpc.bus(:, VA) = 0.0;

    %% Configure NR solver
    mpopt = mpoption('pf.alg', 'NR', 'verbose', 2, 'out.all', 0, ...
                     'pf.tol', 1e-8);

    %% Solve AC power flow
    tic;
    results = runpf(mpc, mpopt);
    solve_time = toc;

    if ~results.success
        fprintf('Flat start failed. Attempting DC warm start fallback...\n');
        errors{end + 1} = 'AC power flow did not converge from flat start';

        mpc_warm = loadcase(network_file);
        mpopt_dc = mpoption('verbose', 0, 'out.all', 0);
        dc_results = rundcpf(mpc_warm, mpopt_dc);
        if dc_results.success
            mpc_warm.bus(:, VA) = dc_results.bus(:, VA);
            mpc_warm.bus(:, VM) = 1.0;
            mpopt_warm = mpoption('pf.alg', 'NR', 'verbose', 2, 'out.all', 0, ...
                                  'pf.tol', 1e-8);
            tic;
            results = runpf(mpc_warm, mpopt_warm);
            solve_time = toc;
            if results.success
                dc_warm_start_needed = true;
                workarounds{end + 1} = 'DC warm start was needed for convergence';
                errors = {};  % clear the flat-start error since warm start succeeded
            else
                errors{end + 1} = 'AC power flow failed even with DC warm start';
            end
        else
            errors{end + 1} = 'DC warm start also failed';
        end
    end

    if results.success
        %% Extract results
        bus_count = size(results.bus, 1);
        branch_count = size(results.branch, 1);

        vm = results.bus(:, VM);
        va = results.bus(:, VA);
        bus_ids = results.bus(:, BUS_I);

        gen_pg = results.gen(:, PG);
        gen_qg = results.gen(:, QG);

        branch_pf = results.branch(:, PF);
        branch_pt = results.branch(:, PT);
        branch_qf = results.branch(:, QF);
        branch_qt = results.branch(:, QT);

        % Losses
        branch_p_loss = branch_pf + branch_pt;
        branch_q_loss = branch_qf + branch_qt;
        total_p_loss = sum(branch_p_loss);
        total_q_loss = sum(branch_q_loss);
        total_gen = sum(gen_pg);
        loss_pct = total_p_loss / total_gen * 100;

        % Convergence quality: check VM differs from flat start
        vm_differs = abs(vm - 1.0) > 1e-6;
        pct_vm_differs = sum(vm_differs) / bus_count * 100;

        % NR iteration count -- MATPOWER stores in results.iterations for PF
        if isfield(results, 'iterations')
            nr_iterations = results.iterations;
        else
            nr_iterations = -1;
        end

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Print results
        fprintf('\n=== Test A-2: ACPF Results ===\n');
        fprintf('Wall clock: %.4f s\n', solve_time);
        fprintf('DC warm start needed: %d\n', dc_warm_start_needed);
        fprintf('Buses: %d, Branches: %d\n', bus_count, branch_count);
        fprintf('Total generation: %.2f MW + %.2f MVAr\n', total_gen, sum(gen_qg));
        fprintf('Total load: %.2f MW + %.2f MVAr\n', sum(results.bus(:, PD)), ...
                sum(results.bus(:, QD)));
        fprintf('Total P losses: %.2f MW (%.2f%%)\n', total_p_loss, loss_pct);
        fprintf('Total Q losses: %.2f MVAr\n', total_q_loss);
        fprintf('VM range: [%.6f, %.6f] pu, mean: %.6f pu\n', min(vm), max(vm), mean(vm));
        fprintf('VA range: [%.4f, %.4f] deg\n', min(va), max(va));
        fprintf('VM differs from flat start: %.1f%% of buses\n', pct_vm_differs);
        fprintf('NR iterations: %d\n', nr_iterations);
        fprintf('PF tolerance: 1e-8\n');
        fprintf('Peak memory: %.1f MB\n', peak_memory_mb);

        fprintf('\nSample bus results (first 10):\n');
        fprintf('  Bus | VM (pu)    | VA (deg)\n');
        for i = 1:min(10, bus_count)
            fprintf('  %3d | %10.6f | %10.4f\n', bus_ids(i), vm(i), va(i));
        end

        fprintf('\nSample branch losses (first 5):\n');
        fprintf('  From -> To  | P loss (MW) | Q loss (MVAr)\n');
        for i = 1:min(5, branch_count)
            fprintf('  %3d -> %3d | %10.4f  | %10.4f\n', ...
                    results.branch(i, F_BUS), results.branch(i, T_BUS), ...
                    branch_p_loss(i), branch_q_loss(i));
        end

        %% Pass condition check
        if pct_vm_differs > 95
            result_status = 'pass';
        else
            errors{end + 1} = sprintf('Only %.1f%% of buses have VM != 1.0 pu (need >95%%)', ...
                                      pct_vm_differs);
        end

        %% Diagnostic finding about iteration count accessibility
        if nr_iterations == -1
            fprintf('\nDiagnostic finding: MATPOWER does not store NR iteration count\n');
            fprintf('in the results struct. Iterations are visible in verbose output\n');
            fprintf('but not programmatically accessible.\n');
        end
    end

catch e
    errors{end + 1} = e.message;
end

fprintf('\nStatus: %s\n', result_status);
if ~isempty(errors)
    fprintf('Errors: %s\n', strjoin(errors, '; '));
end
if ~isempty(workarounds)
    fprintf('Workarounds: %s\n', strjoin(workarounds, '; '));
end
