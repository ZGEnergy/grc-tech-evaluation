%% Test C-5: AC feasibility with progressive constraint relaxation on MEDIUM
%%
%% Dimension: scalability
%% Network: MEDIUM (ACTIVSg 10k)
%% Pass condition: Progressive relaxation diagnostic -- all outcomes produce
%%   informational data. Record relaxation level achieved (0%, 10%, 20%, or infeasible).
%% Tool: MATPOWER 8.1
%% Solver: Newton-Raphson (built-in) for PF, convergence protocol applied

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
peak_memory_mb = -1;
relaxation_achieved = 'infeasible';

try
    define_constants;

    %% Load base case
    fprintf('Loading %s...\n', network_file);
    mpc_base = loadcase(network_file);
    nb = size(mpc_base.bus, 1);
    nl = size(mpc_base.branch, 1);
    ng = size(mpc_base.gen, 1);
    fprintf('Network: %d buses, %d branches, %d generators\n', nb, nl, ng);

    %% Relaxation levels: 0%, 10%, 20%
    relaxation_levels = [0.0, 0.10, 0.20];

    for r = 1:length(relaxation_levels)
        relax_pct = relaxation_levels(r) * 100;
        fprintf('\n=== AC Feasibility: %.0f%% relaxation ===\n', relax_pct);

        mpc = loadcase(network_file);

        %% Apply relaxation to voltage limits
        if relaxation_levels(r) > 0
            vmin_orig = mpc.bus(:, VMIN);
            vmax_orig = mpc.bus(:, VMAX);
            vrange = vmax_orig - vmin_orig;
            mpc.bus(:, VMIN) = vmin_orig - relaxation_levels(r) * vrange;
            mpc.bus(:, VMAX) = vmax_orig + relaxation_levels(r) * vrange;
            fprintf('Voltage limits relaxed: [%.4f, %.4f] -> [%.4f, %.4f] pu\n', ...
                    min(vmin_orig), max(vmax_orig), min(mpc.bus(:, VMIN)), max(mpc.bus(:, VMAX)));
        end

        %% Attempt 1: Flat start ACPF
        mpc.bus(:, VM) = 1.0;
        mpc.bus(:, VA) = 0.0;
        mpopt_ac = mpoption('pf.alg', 'NR', 'verbose', 2, 'out.all', 0, ...
                            'pf.tol', 1e-8, 'pf.nr.max_it', 50);

        tic;
        results_ac = runpf(mpc, mpopt_ac);
        t_flat = toc;

        converged = false;
        start_method = 'flat';
        solve_time = t_flat;

        if results_ac.success
            converged = true;
        else
            %% Attempt 2: DC warm start
            fprintf('  Flat start failed. Trying DC warm start...\n');
            mpc_warm = loadcase(network_file);
            if relaxation_levels(r) > 0
                mpc_warm.bus(:, VMIN) = mpc.bus(:, VMIN);
                mpc_warm.bus(:, VMAX) = mpc.bus(:, VMAX);
            end

            dc_pf = rundcpf(mpc_warm, mpoption('verbose', 0, 'out.all', 0));
            if dc_pf.success
                mpc_warm.bus(:, VA) = dc_pf.bus(:, VA);
                mpc_warm.bus(:, VM) = 1.0;
            end

            tic;
            results_ac = runpf(mpc_warm, mpopt_ac);
            t_warm = toc;

            if results_ac.success
                converged = true;
                start_method = 'dc_warm';
                solve_time = t_warm;
            else
                %% Attempt 3: Relaxed tolerance
                fprintf('  DC warm start failed. Trying relaxed tolerance (1e-4)...\n');
                mpopt_relaxed = mpoption('pf.alg', 'NR', 'verbose', 0, 'out.all', 0, ...
                                         'pf.tol', 1e-4, 'pf.nr.max_it', 100);
                tic;
                results_ac = runpf(mpc_warm, mpopt_relaxed);
                t_relaxed = toc;

                if results_ac.success
                    converged = true;
                    start_method = 'dc_warm+relaxed_tol';
                    solve_time = t_relaxed;
                else
                    solve_time = t_flat + t_warm + t_relaxed;
                end
            end
        end

        if converged
            vm = results_ac.bus(:, VM);
            va = results_ac.bus(:, VA);
            nr_iters = -1;
            if isfield(results_ac, 'iterations')
                nr_iters = results_ac.iterations;
            end

            %% Compute max bus mismatch (use ext2int for consecutive bus numbering)
            res_int = ext2int(results_ac);
            nb_int = size(res_int.bus, 1);
            ng_int = size(res_int.gen, 1);
            vm_int = res_int.bus(:, VM);
            va_int = res_int.bus(:, VA);
            [Ybus, ~, ~] = makeYbus(res_int.baseMVA, res_int.bus, res_int.branch);
            V = vm_int .* exp(1j * va_int * pi / 180);
            Sbus_calc = V .* conj(Ybus * V);
            Pg = zeros(nb_int, 1);
            Qg = zeros(nb_int, 1);
            for g_idx = 1:ng_int
                bus_idx = find(res_int.bus(:, BUS_I) == res_int.gen(g_idx, GEN_BUS));
                if ~isempty(bus_idx)
                    Pg(bus_idx) = Pg(bus_idx) + res_int.gen(g_idx, PG);
                    Qg(bus_idx) = Qg(bus_idx) + res_int.gen(g_idx, QG);
                end
            end
            Pd = res_int.bus(:, PD);
            Qd = res_int.bus(:, QD);
            Sspec = (Pg - Pd + 1j*(Qg - Qd)) / res_int.baseMVA;
            ref_bus = find(res_int.bus(:, BUS_TYPE) == 3);
            pv_pq = setdiff(1:nb_int, ref_bus);
            mismatch = Sbus_calc(pv_pq) - Sspec(pv_pq);
            max_bus_mismatch = max(max(abs(real(mismatch))), max(abs(imag(mismatch))));

            %% Voltage violations (against original limits from file)
            mpc_orig = loadcase(network_file);
            v_over = sum(vm > mpc_orig.bus(:, VMAX));
            v_under = sum(vm < mpc_orig.bus(:, VMIN));

            %% Thermal violations
            pf_mva = sqrt(results_ac.branch(:, PF).^2 + results_ac.branch(:, QF).^2);
            orig_rates = mpc_orig.branch(:, RATE_A);
            thermal_viol = sum((pf_mva > orig_rates) & (orig_rates > 0));

            %% Reactive power limit violations
            qg = results_ac.gen(:, QG);
            qmax = results_ac.gen(:, QMAX);
            qmin = results_ac.gen(:, QMIN);
            q_over = sum(qg > qmax + 1e-3);
            q_under = sum(qg < qmin - 1e-3);

            %% Losses
            total_p_loss = sum(results_ac.branch(:, PF) + results_ac.branch(:, PT));
            total_gen = sum(results_ac.gen(:, PG));
            loss_pct = total_p_loss / total_gen * 100;

            fprintf('  CONVERGED (start: %s, time: %.4f s, iters: %d)\n', ...
                    start_method, solve_time, nr_iters);
            fprintf('  Max bus mismatch: %.6e pu\n', max_bus_mismatch);
            fprintf('  VM range: [%.6f, %.6f] pu\n', min(vm), max(vm));
            fprintf('  VA range: [%.4f, %.4f] deg\n', min(va), max(va));
            fprintf('  Total gen: %.2f MW, Losses: %.2f MW (%.2f%%)\n', total_gen, ...
                    total_p_loss, loss_pct);
            fprintf('  Voltage violations (vs original limits): %d over, %d under\n', v_over, ...
                    v_under);
            fprintf('  Thermal violations (vs original limits): %d / %d\n', thermal_viol, nl);
            fprintf('  Q-limit violations: %d over, %d under\n', q_over, q_under);

            relaxation_achieved = sprintf('%.0f%%', relax_pct);

            if relax_pct == 0
                result_status = 'pass';
                fprintf('  0%% relaxation converged -- AC feasible!\n');
            end
        else
            fprintf('  FAILED at %.0f%% relaxation\n', relax_pct);
        end
    end

    %% If 0% failed but higher relaxation succeeded, still informational
    if strcmp(result_status, 'fail')
        if ~strcmp(relaxation_achieved, 'infeasible')
            result_status = 'informational';
            workarounds{end + 1} = sprintf('AC feasibility required %s relaxation', ...
                                           relaxation_achieved);
        end
    end

    %% Peak memory
    [~, mem_out] = system('grep VmHWM /proc/self/status');
    peak_kb = sscanf(mem_out, 'VmHWM: %f');
    if ~isempty(peak_kb)
        peak_memory_mb = peak_kb / 1024;
    end

catch e
    errors{end + 1} = e.message;
    fprintf('ERROR: %s\n', e.message);
    for i = 1:length(e.stack)
        fprintf('  at %s line %d\n', e.stack(i).name, e.stack(i).line);
    end
end

fprintf('\n=== Final ===\n');
fprintf('Status: %s\n', result_status);
fprintf('Relaxation achieved: %s\n', relaxation_achieved);
fprintf('Peak memory: %.1f MB\n', peak_memory_mb);
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
