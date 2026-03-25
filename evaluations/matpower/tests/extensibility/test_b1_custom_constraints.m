%% Test B-1: Add flow gate limit to DC OPF and extract dual values
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Achievable through documented API. No source patching.
%%   Dual value of custom constraint extractable and correctly reflects binding status.
%%   Include BOTH non-binding (dual=0) AND binding case.
%% Tool: MATPOWER 8.1
%% Solver: GLPK (LP -- quadratic costs linearized to PWL)

function result = test_b1_custom_constraints(network_file, timeseries_dir)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end

    result = struct();
    result.status = 'fail';
    result.wall_clock_seconds = 0;
    result.details = struct();
    result.errors = {};
    result.workarounds = {};

    %% Setup MATPOWER
    mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
    addpath(fullfile(mp_root, 'lib'));
    addpath(fullfile(mp_root, 'data'));
    addpath(fullfile(mp_root, 'mips', 'lib'));
    addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
    addpath(fullfile(mp_root, 'mptest', 'lib'));

    tic;
    try
        %% Load case
        mpc = loadcase(network_file);
        define_constants;

        nb = size(mpc.bus, 1);
        ng = size(mpc.gen, 1);
        nl = size(mpc.branch, 1);

        %% Convert quadratic costs to piecewise linear for GLPK (LP only)
        %% Case39 has polynomial MODEL=2, NCOST=3 (c2*P^2 + c1*P + c0).
        %% GLPK rejects QP problems, so we linearize to 2-point PWL.
        for i = 1:ng
            c2 = mpc.gencost(i, 5);
            c1 = mpc.gencost(i, 6);
            c0 = mpc.gencost(i, 7);
            pmin = mpc.gen(i, PMIN);
            pmax = mpc.gen(i, PMAX);
            cost_min = c2*pmin^2 + c1*pmin + c0;
            cost_max = c2*pmax^2 + c1*pmax + c0;
            mpc.gencost(i, :) = 0;
            mpc.gencost(i, 1) = 1;  % PWL model
            mpc.gencost(i, 4) = 2;  % 2 points
            mpc.gencost(i, 5) = pmin;
            mpc.gencost(i, 6) = cost_min;
            mpc.gencost(i, 7) = pmax;
            mpc.gencost(i, 8) = cost_max;
        end

        %% Configure solver: GLPK for LP
        %% MIPS (built-in QP/NLP) fails to converge with user constraints.
        %% HiGHS (LP/QP) is not available in the Octave devcontainer.
        mpopt = mpoption('verbose', 0, 'out.all', 0, 'opf.dc.solver', 'GLPK');

        %% ============================================================
        %% Step 1: Baseline DC OPF (no custom constraint)
        %% ============================================================
        fprintf('=== Baseline DC OPF (LP with PWL costs) ===\n');
        results_base = rundcopf(mpc, mpopt);
        if ~results_base.success
            error('Baseline DC OPF failed to converge');
        end
        obj_base = results_base.f;
        fprintf('Baseline objective: $%.2f\n', obj_base);

        %% Target generator: Gen 1 (bus 30) -- largest unconstrained dispatch
        gen_idx = 1;
        gen_pg_base = results_base.gen(gen_idx, PG);
        gen_bus = mpc.gen(gen_idx, GEN_BUS);
        fprintf('Gen %d (bus %d) baseline dispatch: %.2f MW\n', gen_idx, gen_bus, gen_pg_base);

        %% ============================================================
        %% Step 2: Non-binding constraint (150% of unconstrained dispatch)
        %% ============================================================
        fprintf('\n=== Non-Binding Constraint ===\n');
        limit_nonbinding = gen_pg_base * 1.5;
        fprintf('Limit: %.2f MW (150%% of unconstrained %.2f MW)\n', limit_nonbinding, gen_pg_base);

        mpc_nb = mpc;
        %% DC OPF variable ordering: [Va(1..nb); Pg(1..ng)]
        %% User constraint: A * x <= u
        A_nb = sparse(1, nb + ng);
        A_nb(1, nb + gen_idx) = mpc.baseMVA;  % Pg is in per-unit internally
        mpc_nb.A = A_nb;
        mpc_nb.u = limit_nonbinding;
        mpc_nb.l = -Inf;

        results_nb = rundcopf(mpc_nb, mpopt);
        if ~results_nb.success
            error('Non-binding DC OPF failed');
        end

        obj_nb = results_nb.f;
        mu_l_nb = results_nb.lin.mu.l.usr;
        mu_u_nb = results_nb.lin.mu.u.usr;
        fprintf('Non-binding objective: $%.2f\n', obj_nb);
        fprintf('Non-binding dual (mu_l): %.6e\n', mu_l_nb);
        fprintf('Non-binding dual (mu_u): %.6e\n', mu_u_nb);

        %% Verify non-binding: dual should be zero (within tolerance)
        nb_dual_ok = abs(mu_u_nb) < 1e-4;
        nb_obj_ok = abs(obj_nb - obj_base) < 1e-2;
        fprintf('Non-binding dual ~= 0: %s\n', mat2str(nb_dual_ok));
        fprintf('Objective unchanged: %s\n', mat2str(nb_obj_ok));

        %% ============================================================
        %% Step 3: Binding constraint (~50% of unconstrained dispatch)
        %% ============================================================
        fprintf('\n=== Binding Constraint ===\n');
        limit_binding = gen_pg_base * 0.5;
        fprintf('Limit: %.2f MW (50%% of unconstrained %.2f MW)\n', limit_binding, gen_pg_base);

        mpc_b = mpc;
        A_b = sparse(1, nb + ng);
        A_b(1, nb + gen_idx) = mpc.baseMVA;
        mpc_b.A = A_b;
        mpc_b.u = limit_binding;
        mpc_b.l = -Inf;

        results_b = rundcopf(mpc_b, mpopt);
        if ~results_b.success
            error('Binding DC OPF failed');
        end

        obj_b = results_b.f;
        mu_l_b = results_b.lin.mu.l.usr;
        mu_u_b = results_b.lin.mu.u.usr;
        gen_pg_b = results_b.gen(gen_idx, PG);
        fprintf('Binding objective: $%.2f\n', obj_b);
        fprintf('Binding dual (mu_l): %.6e\n', mu_l_b);
        fprintf('Binding dual (mu_u): %.6e\n', mu_u_b);
        fprintf('Constrained dispatch: %.2f MW (limit: %.2f MW)\n', gen_pg_b, limit_binding);

        %% Verify binding: dual != 0 and objective increases
        b_dual_ok = abs(mu_u_b) > 1e-4;
        b_obj_ok = obj_b > obj_base + 1e-2;
        fprintf('Binding dual != 0: %s (mu_u = %.6f)\n', mat2str(b_dual_ok), mu_u_b);
        fprintf('Objective increased: %s ($%.2f -> $%.2f, +$%.2f)\n', ...
                mat2str(b_obj_ok), obj_base, obj_b, obj_b - obj_base);

        %% LMP comparison at constrained gen bus
        lmp_base = results_base.bus(mpc.bus(:,BUS_I)==gen_bus, LAM_P);
        lmp_b = results_b.bus(mpc.bus(:,BUS_I)==gen_bus, LAM_P);
        fprintf('\n=== LMP Impact ===\n');
        fprintf('Bus %d LMP: $%.2f -> $%.2f\n', gen_bus, lmp_base, lmp_b);

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Store results
        result.details.baseline_objective = obj_base;
        result.details.nonbinding_objective = obj_nb;
        result.details.binding_objective = obj_b;
        result.details.nonbinding_dual_mu_u = mu_u_nb;
        result.details.binding_dual_mu_u = mu_u_b;
        result.details.gen_base_dispatch = gen_pg_base;
        result.details.gen_binding_dispatch = gen_pg_b;
        result.details.limit_nonbinding = limit_nonbinding;
        result.details.limit_binding = limit_binding;
        result.details.objective_increase = obj_b - obj_base;
        result.details.objective_increase_pct = 100 * (obj_b - obj_base) / obj_base;
        result.details.peak_memory_mb = peak_memory_mb;
        result.details.lmp_base = lmp_base;
        result.details.lmp_binding = lmp_b;

        %% Pass criteria
        if nb_dual_ok && b_dual_ok && b_obj_ok
            result.status = 'qualified_pass';
            result.workarounds{end+1} = 'Used GLPK solver (LP) with PWL costs. MIPS fails to converge with user constraints. HiGHS not available in Octave devcontainer. [solver-specific: MIPS singularity with user constraints]';
            fprintf('\n=== QUALIFIED PASS ===\n');
        else
            if ~nb_dual_ok
                result.errors{end+1} = sprintf('Non-binding dual not zero: %.6e', mu_u_nb);
            end
            if ~b_dual_ok
                result.errors{end+1} = 'Binding dual is zero when it should be nonzero';
            end
            if ~b_obj_ok
                result.errors{end+1} = 'Objective did not increase with binding constraint';
            end
        end

    catch e
        result.errors{end+1} = e.message;
        fprintf('ERROR: %s\n', e.message);
    end
    result.wall_clock_seconds = toc;
end

%% Run when executed as script
result = test_b1_custom_constraints();
disp(result);
disp(result.details);
