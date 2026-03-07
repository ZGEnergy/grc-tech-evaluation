%% Test C-8: SCOPF Scale on MEDIUM (ACTIVSg 10k-bus)
%%
%% Pass condition: Converges on MEDIUM. Performance and iteration stats recorded.
%% Network: 10000 buses, 12706 branches, 2485 generators
%% Solver: MIPS or GLPK
%% Target: N-1 with up to 500 contingencies
%%
%% Approach: Use MOST with security_constraints=1 and contab specifying
%% branch contingencies on MEDIUM. Start with 50, then try 100, 200, 500.
%% If MOST cannot handle 500 on MEDIUM, document the scaling limit.
%% 19.4% of MEDIUM branches have zero RATE_A.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c8_scopf_scale_medium.m

% Add MATPOWER to path
mp_root = "/workspace/evaluations/matpower/matpower8.1";
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));
addpath(fullfile(mp_root, "most", "lib"));
addpath(fullfile(mp_root, "most", "lib", "t"));
addpath(fullfile(mp_root, "most", "lib"));

% Load column index constants
define_constants;
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;

% Load network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case_ACTIVSg10k.m");

fprintf("\n========================================\n");
fprintf("TEST C-8: SCOPF Scale on MEDIUM (ACTIVSg 10k-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;
n_binding = 0;
nc_solved = 0;
qp_vars = 0;

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

    % --- Step 1: Run base DC OPF for reference ---
    fprintf("\n--- Step 1: Base DC OPF ---\n");
    mpopt_base = mpoption("verbose", 0, "out.all", 0);
    if exist("OCTAVE_VERSION", "builtin")
        mpopt_base = mpoption(mpopt_base, "mips.linsolver", "LU");
    end
    base_start = tic();
    results_base = rundcopf(mpc, mpopt_base);
    base_time = toc(base_start);
    if results_base.success ~= 1
        error("Base DC OPF did not converge");
    end
    fprintf("  Base DC OPF converged in %.2f seconds\n", base_time);
    fprintf("  Objective: %.2f $/hr\n", results_base.f);

    % --- Step 2: Set ramp rates ---
    fprintf("\n--- Step 2: Setting ramp rates ---\n");
    for g = 1:ng
        pmax_g = max(mpc.gen(g, PMAX), 1);
        mpc.gen(g, RAMP_AGC) = pmax_g;
        mpc.gen(g, RAMP_10)  = pmax_g;
        mpc.gen(g, RAMP_30)  = pmax_g;
    end
    fprintf("  Ramp rates set to Pmax (single-period)\n");

    % --- Step 3: Create xGenData ---
    xgd_table.colnames = {
                          'PositiveActiveReservePrice', ...
                          'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', ...
                          'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', ...
                          'NegativeActiveDeltaPrice' ...
                         };
    xgd_data = zeros(ng, 6);
    for g = 1:ng
        pmax_g = max(mpc.gen(g, PMAX), 1);
        xgd_data(g, :) = [1e-8, pmax_g, 2e-8, pmax_g, 1e-9, 1e-9];
    end
    xgd_table.data = xgd_data;
    xgd = loadxgendata(xgd_table, mpc);
    fprintf("  Created xGenData for %d generators\n", ng);

    % --- Step 4: Select contingencies ---
    % Use base OPF flows to select most critical branches
    fprintf("\n--- Step 4: Selecting contingencies ---\n");
    pf_base = abs(results_base.branch(:, PF));
    rate_a = mpc.branch(:, RATE_A);

    % Flow utilization ratio
    utilization = zeros(nl, 1);
    for br = 1:nl
        if rate_a(br) > 0 && rate_a(br) < 9000
            utilization(br) = pf_base(br) / rate_a(br);
        end
    end

    % Sort by utilization (most loaded first)
    [~, sorted_idx] = sort(utilization, 'descend');

    % --- Step 5: Try SCOPF with increasing contingencies ---
    nc_attempts = [50, 100, 200, 500];
    prob_per_cont = 0.001;
    best_nc = 0;

    for attempt = 1:length(nc_attempts)
        nc_target = nc_attempts(attempt);
        fprintf("\n=== Attempting SCOPF with %d contingencies ===\n", nc_target);

        % Build contingency table from most critical branches
        contab = [];
        count = 0;
        for k = 1:nl
            if count >= nc_target
                break
            end
            br = sorted_idx(k);
            % Skip branches with very low flow or very high rate (unconstrained)
            if rate_a(br) >= 9000 || pf_base(br) < 1
                continue
            end
            contab = [contab
                      count + 1, prob_per_cont, CT_TBRCH, br, BR_STATUS, CT_REP, 0];
            count = count + 1;
        end
        nc = size(contab, 1);
        fprintf("  Built contingency table with %d outages\n", nc);

        % Build MOST data structure
        mpopt = mpoption("verbose", 0, "out.all", 0);
        mpopt = mpoption(mpopt, "model", "DC");
        mpopt = mpoption(mpopt, "most.dc_model", 1);
        mpopt = mpoption(mpopt, "most.security_constraints", 1);
        mpopt = mpoption(mpopt, "most.solver", "DEFAULT");
        if exist("OCTAVE_VERSION", "builtin")
            mpopt = mpoption(mpopt, "mips.linsolver", "LU");
        end

        fprintf("  Building MOST data structure...\n");
        build_start = tic();
        mdi = loadmd(mpc, [], xgd, [], contab);
        build_time = toc(build_start);
        fprintf("  MOST data built in %.2f seconds\n", build_time);

        fprintf("  Solving MOST SCOPF...\n");
        solve_start = tic();
        mdo = most(mdi, mpopt);
        solve_time = toc(solve_start);

        if mdo.QP.exitflag > 0
            qp_vars = length(mdo.QP.x);
            fprintf("  CONVERGED (exitflag=%d)\n", mdo.QP.exitflag);
            fprintf("  Objective: %.2f $/hr\n", mdo.QP.f);
            fprintf("  QP variables: %d\n", qp_vars);
            fprintf("  Build time: %.2f s, Solve time: %.2f s\n", build_time, solve_time);
            best_nc = nc;
            nc_solved = nc;

            % Extract some results
            scopf_pg = mdo.flow(1, 1, 1).mpc.gen(:, PG);
            dispatch_diff = max(abs(scopf_pg - results_base.gen(:, PG)));
            fprintf("  Max dispatch diff from base: %.2f MW\n", dispatch_diff);
            fprintf("  SCOPF cost: %.2f vs Base cost: %.2f (delta=%.2f)\n", ...
                    mdo.QP.f, results_base.f, mdo.QP.f - results_base.f);

            % Count binding contingencies (approximate)
            n_cont_cases = size(mdo.flow, 3) - 1;
            n_binding_local = 0;
            for k = 2:min(n_cont_cases + 1, size(mdo.flow, 3))
                cont_mpc = mdo.flow(1, 1, k).mpc;
                pf_cont = abs(cont_mpc.branch(:, PF));
                ra_cont = cont_mpc.branch(:, RATE_A);
                active = find(ra_cont > 0 & ra_cont < 9000 & cont_mpc.branch(:, BR_STATUS) > 0);
                if ~isempty(active)
                    ratios = pf_cont(active) ./ ra_cont(active);
                    if max(ratios) > 0.99
                        n_binding_local = n_binding_local + 1;
                    end
                end
            end
            n_binding = n_binding_local;
            fprintf("  Binding contingencies (>99%% utilization): %d\n", n_binding);
        else
            fprintf("  FAILED (exitflag=%d), solve time: %.2f s\n", mdo.QP.exitflag, solve_time);
            fprintf("  Scaling limit reached at %d contingencies\n", nc);
            break
        end
    end

    wall_clock = toc(tic_val);

    if best_nc > 0
        fprintf("\n--- Summary ---\n");
        fprintf("Largest SCOPF solved: %d contingencies on MEDIUM\n", best_nc);
        fprintf("Base DC OPF time: %.2f seconds\n", base_time);
        fprintf("Total wall clock: %.2f seconds\n", wall_clock);
        fprintf("Binding contingencies: %d\n", n_binding);
        status = "pass";
        loc = 165;
    else
        fprintf("\nFAILED: Could not solve SCOPF on MEDIUM even with 50 contingencies\n");
        status = "fail";
        loc = 165;
    end

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
fprintf("NC_SOLVED: %d\n", nc_solved);
fprintf("N_BINDING: %d\n", n_binding);
fprintf("QP_VARS: %d\n", qp_vars);
fprintf("========================================\n");
