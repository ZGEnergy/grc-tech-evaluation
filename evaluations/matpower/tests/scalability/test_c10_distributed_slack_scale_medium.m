%% Test C-10: Distributed Slack Scale on MEDIUM (ACTIVSg 10k-bus)
%%
%% Pass condition: Converges on MEDIUM. LMP comparison recorded.
%% Network: 10000 buses, 12706 branches, 2485 generators
%% Solver: MIPS
%%
%% Approach: Build PTDF-based DC OPF manually using opt_model with
%% distributed slack weights (load-proportional). Compare LMPs to
%% single-slack rundcopf results. This is the A-11 pattern scaled up.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c10_distributed_slack_scale_medium.m

% Add MATPOWER to path
mp_root = "/workspace/evaluations/matpower/matpower8.1";
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load column index constants
define_constants;

% Load network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case_ACTIVSg10k.m");

fprintf("\n========================================\n");
fprintf("TEST C-10: Distributed Slack Scale on MEDIUM (ACTIVSg 10k-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;
lmp_max_diff = 0;
dispatch_max_diff = 0;

tic_val = tic();
try
    % --- Load and prepare case ---
    fprintf("Loading network...\n");
    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nl, ng);

    % --- Fix zero RATE_A branches ---
    fprintf("\n--- Fixing zero RATE_A branches ---\n");
    zero_rate = mpc.branch(:, RATE_A) == 0;
    n_zero = sum(zero_rate);
    if n_zero > 0
        mpc.branch(zero_rate, RATE_A) = 9999;
        mpc.branch(zero_rate, RATE_B) = 9999;
        mpc.branch(zero_rate, RATE_C) = 9999;
        fprintf("  Set %d zero-RATE_A branches to 9999 MVA\n", n_zero);
    end

    % --- Step 1: Single-slack DC OPF reference ---
    fprintf("\n--- Step 1: Single-slack DC OPF ---\n");
    mpopt = mpoption("verbose", 0, "out.all", 0);
    if exist("OCTAVE_VERSION", "builtin")
        mpopt = mpoption(mpopt, "mips.linsolver", "LU");
    end

    single_start = tic();
    results_single = rundcopf(mpc, mpopt);
    single_time = toc(single_start);
    assert(results_single.success == 1, "Single-slack DC OPF failed");
    fprintf("  Converged in %.2f seconds. Objective: %.2f $/hr\n", single_time, results_single.f);

    lmp_single = results_single.bus(:, LAM_P);
    fprintf("  LMP range: [%.4f, %.4f] $/MWh\n", min(lmp_single), max(lmp_single));

    ref_bus = find(mpc.bus(:, BUS_TYPE) == 3);
    fprintf("  Reference bus: %d\n", mpc.bus(ref_bus(1), BUS_I));

    % --- Step 2: Convert to internal numbering ---
    fprintf("\n--- Step 2: Preparing internal data ---\n");
    mpc_int = ext2int(mpc);
    nb_int = size(mpc_int.bus, 1);
    ng_int = size(mpc_int.gen, 1);
    nl_int = size(mpc_int.branch, 1);
    fprintf("  Internal: %d buses, %d branches, %d generators\n", nb_int, nl_int, ng_int);

    % --- Step 3: Compute distributed-slack PTDF ---
    fprintf("\n--- Step 3: Computing distributed-slack PTDF ---\n");
    total_load = sum(mpc_int.bus(:, PD));
    slack_weights = mpc_int.bus(:, PD) / total_load;
    slack_weights(slack_weights < 0) = 0;  % no negative weights
    slack_weights = slack_weights / sum(slack_weights);  % renormalize
    fprintf("  Non-zero weight buses: %d (out of %d)\n", sum(slack_weights > 0), nb_int);

    ptdf_start = tic();
    H_dist = makePTDF(mpc_int, slack_weights);
    ptdf_time = toc(ptdf_start);
    fprintf("  Distributed-slack PTDF computed in %.2f seconds: %d x %d\n", ...
            ptdf_time, size(H_dist, 1), size(H_dist, 2));

    % Also compute single-slack PTDF for comparison
    H_single = makePTDF(mpc_int);
    ptdf_diff = max(max(abs(H_single - H_dist)));
    fprintf("  Max PTDF difference (single vs distributed): %.6f\n", ptdf_diff);

    % --- Step 4: Build manual PTDF-based DC OPF ---
    fprintf("\n--- Step 4: Building manual PTDF-based DC OPF ---\n");

    % Generator-to-bus mapping
    Cg = sparse(mpc_int.gen(:, GEN_BUS), (1:ng_int)', ones(ng_int, 1), nb_int, ng_int);

    om = opt_model;

    % Variables: Pg
    Pg0 = mpc_int.gen(:, PG);
    Pgmin = mpc_int.gen(:, PMIN);
    Pgmax = mpc_int.gen(:, PMAX);
    om.add_var('Pg', ng_int, Pg0, Pgmin, Pgmax);

    % Power balance: sum(Pg) = sum(Pd)
    total_pd = sum(mpc_int.bus(:, PD));
    Aeq = ones(1, nb_int) * Cg;
    om.add_lin_constraint('Pbal', Aeq, total_pd, total_pd, {'Pg'});

    % Flow limits using distributed-slack PTDF
    Pd_vec = mpc_int.bus(:, PD);
    Af = H_dist * Cg;
    rate_a = mpc_int.branch(:, RATE_A);
    flow_offset = H_dist * Pd_vec;

    flow_lb = -rate_a + flow_offset;
    flow_ub =  rate_a + flow_offset;

    % Only constrain branches with finite RATE_A (not 9999 unconstrained)
    active_br = find(rate_a > 0 & rate_a < 9000);
    fprintf("  Active flow constraints: %d branches (out of %d)\n", length(active_br), nl_int);

    om.add_lin_constraint('flow', Af(active_br, :), ...
                          flow_lb(active_br), flow_ub(active_br), {'Pg'});

    % Cost: quadratic from gencost
    Q = sparse(ng_int, ng_int);
    c_lin = zeros(ng_int, 1);
    k0 = 0;
    for g = 1:ng_int
        if mpc_int.gencost(g, 1) == 2
            ncost = mpc_int.gencost(g, 4);
            if ncost >= 3
                Q(g, g) = 2 * mpc_int.gencost(g, 5);
                c_lin(g) = mpc_int.gencost(g, 6);
                k0 = k0 + mpc_int.gencost(g, 7);
            elseif ncost == 2
                c_lin(g) = mpc_int.gencost(g, 5);
                k0 = k0 + mpc_int.gencost(g, 6);
            end
        end
    end
    om.add_quad_cost('gencost', Q, c_lin, k0, {'Pg'});

    % Solve
    fprintf("\n--- Solving distributed-slack DC OPF on MEDIUM ---\n");
    opt = struct('verbose', 0, 'alg', 'MIPS');
    solve_start = tic();
    [x_sol, f_sol, exitflag] = om.solve(opt);
    solve_time = toc(solve_start);

    fprintf("  opt_model.solve exitflag: %d\n", exitflag);
    fprintf("  Solve time: %.2f seconds\n", solve_time);

    if exitflag <= 0
        error("Manual PTDF-based OPF did not converge (exitflag=%d)", exitflag);
    end

    Pg_dist = om.get_soln('var', 'Pg');
    fprintf("  Distributed-slack OPF converged. Objective: %.2f $/hr\n", f_sol);

    % --- Step 5: Extract LMPs ---
    fprintf("\n--- Step 5: Extracting LMPs ---\n");

    [mu_l_pbal, mu_u_pbal] = om.get_soln('lin', {'mu_l', 'mu_u'}, 'Pbal');
    [mu_l_flow, mu_u_flow] = om.get_soln('lin', {'mu_l', 'mu_u'}, 'flow');

    energy_price = mu_u_pbal - mu_l_pbal;
    fprintf("  Energy price (balance multiplier): %.4f $/MWh\n", energy_price);

    mu_net = mu_u_flow - mu_l_flow;
    mu_full = zeros(nl_int, 1);
    mu_full(active_br) = mu_net;

    % LMP_i = energy + congestion
    dist_lmp = energy_price * ones(nb_int, 1) + H_dist' * mu_full;
    fprintf("  Distributed-slack LMP range: [%.4f, %.4f] $/MWh\n", ...
            min(dist_lmp), max(dist_lmp));

    % --- Step 6: Compare ---
    fprintf("\n--- Step 6: Comparison ---\n");

    % Map single-slack results to internal ordering for comparison
    lmp_single_int = results_single.bus(mpc_int.order.bus.e2i(mpc_int.order.bus.e2i > 0), LAM_P);
    % More robust: use the internal case order
    % rundcopf returns external ordering; we need internal
    res_int = ext2int(results_single);
    lmp_single_int = res_int.bus(:, LAM_P);
    pg_single_int = res_int.gen(:, PG);

    % Dispatch comparison
    dispatch_max_diff = max(abs(Pg_dist - pg_single_int));
    fprintf("  Max dispatch difference: %.4f MW\n", dispatch_max_diff);

    % LMP comparison
    lmp_max_diff = max(abs(dist_lmp - lmp_single_int));
    fprintf("  Max LMP difference: %.6f $/MWh\n", lmp_max_diff);
    lmp_differs = lmp_max_diff > 0.001;
    fprintf("  LMPs differ: %s\n", mat2str(lmp_differs));

    % Show sample buses
    fprintf("\n  Sample bus comparison:\n");
    fprintf("  Bus#   LMP_single  LMP_dist     Diff\n");
    sample_idx = round(linspace(1, nb_int, min(10, nb_int)));
    for k = 1:length(sample_idx)
        bi = sample_idx(k);
        fprintf("  %5d  %9.4f   %9.4f  %9.4f\n", ...
                mpc_int.bus(bi, BUS_I), lmp_single_int(bi), dist_lmp(bi), ...
                dist_lmp(bi) - lmp_single_int(bi));
    end

    % Statistics
    fprintf("\n  LMP Statistics:\n");
    fprintf("    Single-slack: mean=%.4f, std=%.4f\n", mean(lmp_single_int), std(lmp_single_int));
    fprintf("    Distributed:  mean=%.4f, std=%.4f\n", mean(dist_lmp), std(dist_lmp));
    fprintf("    Correlation:  %.6f\n", corr(lmp_single_int, dist_lmp));

    % --- Summary ---
    wall_clock = toc(tic_val);
    fprintf("\n--- Summary ---\n");
    fprintf("Network: MEDIUM (%d buses, %d generators)\n", nb, ng);
    fprintf("Single-slack DC OPF: %.2f seconds\n", single_time);
    fprintf("PTDF computation: %.2f seconds\n", ptdf_time);
    fprintf("Distributed-slack OPF: %.2f seconds\n", solve_time);
    fprintf("Total wall clock: %.2f seconds\n", wall_clock);
    fprintf("Max LMP difference: %.6f $/MWh\n", lmp_max_diff);
    fprintf("LMPs differ: %s\n", mat2str(lmp_differs));

    status = "qualified_pass";
    loc = 155;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    if isfield(err, 'stack') && length(err.stack) > 0
        fprintf("Error in: %s (line %d)\n", err.stack(1).name, err.stack(1).line);
    end
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("LMP_MAX_DIFF: %.6f\n", lmp_max_diff);
fprintf("DISPATCH_MAX_DIFF: %.4f\n", dispatch_max_diff);
fprintf("========================================\n");
