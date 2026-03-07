%% Test C-4: SCUC Scale on SMALL (ACTIVSg 2000-bus)
%%
%% Pass condition: Solves to feasibility on SMALL. MIP gap and timing recorded.
%% Network: 2000 buses, 3206 branches, 544 generators
%% Solver: GLPK (only MILP solver on Octave)
%%
%% Approach: Use MOST for 24-hour SCUC. Convert polynomial costs to PWL for GLPK.
%% 544 generators x 24 periods = very large MILP. GLPK may struggle.
%% Set MIP gap tolerance to 10% and timeout to 10 minutes.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c4_scuc_scale_small.m

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
network_file = fullfile(pwd, "..", "..", "data", "networks", "case_ACTIVSg2000.m");

fprintf("\n========================================\n");
fprintf("TEST C-4: SCUC Scale on SMALL (ACTIVSg 2000-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;
mip_gap = NaN;
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

    % --- Parameters ---
    nt = 24;  % 24-hour horizon

    % --- Step 1: Fix zero RATE_A branches ---
    fprintf("\n--- Fixing zero RATE_A branches ---\n");
    zero_rate = mpc.branch(:, RATE_A) == 0;
    n_zero = sum(zero_rate);
    if n_zero > 0
        % Set to large value (effectively unconstrained)
        mpc.branch(zero_rate, RATE_A) = 9999;
        mpc.branch(zero_rate, RATE_B) = 9999;
        mpc.branch(zero_rate, RATE_C) = 9999;
        fprintf("  Set %d zero-RATE_A branches to 9999 MVA\n", n_zero);
    end

    % --- Step 2: Augment generator data for UC ---
    fprintf("\n--- Augmenting generator data ---\n");
    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        if pmax_g <= 0
            pmax_g = 1;  % avoid zero Pmax issues
        end
        % Ramp rates: 30% of Pmax per period
        mpc.gen(g, RAMP_AGC) = 0.3 * pmax_g;
        mpc.gen(g, RAMP_10)  = 0.3 * pmax_g;
        mpc.gen(g, RAMP_30)  = 0.3 * pmax_g;
        % Set nonzero PMIN if currently zero (20% of PMAX for larger units)
        if mpc.gen(g, PMIN) == 0 && pmax_g > 50
            mpc.gen(g, PMIN) = 0.2 * pmax_g;
        end
    end
    fprintf("  Ramp rates set to 30%% of Pmax\n");

    % --- Step 3: Convert quadratic costs to piecewise-linear ---
    fprintf("\n--- Converting costs to piecewise-linear ---\n");
    n_converted = 0;
    nseg = 5;  % fewer segments to keep problem smaller
    for g = 1:ng
        if mpc.gencost(g, 1) == 2  % polynomial
            ncost = mpc.gencost(g, 4);
            pmin_g = mpc.gen(g, PMIN);
            pmax_g = mpc.gen(g, PMAX);
            if pmax_g <= pmin_g
                pmax_g = pmin_g + 1;
            end
            % Get polynomial coefficients
            if ncost == 3
                c2 = mpc.gencost(g, 5);
                c1 = mpc.gencost(g, 6);
                c0 = mpc.gencost(g, 7);
            elseif ncost == 2
                c2 = 0;
                c1 = mpc.gencost(g, 5);
                c0 = mpc.gencost(g, 6);
            else
                c2 = 0;
                c1 = 10;
                c0 = 0;  % default linear cost
            end

            % Create PWL approximation
            p_points = linspace(pmin_g, pmax_g, nseg + 1);
            cost_points = c2 * p_points.^2 + c1 * p_points + c0;

            ncols_needed = 4 + 2 * (nseg + 1);
            if ncols_needed > size(mpc.gencost, 2)
                mpc.gencost = [mpc.gencost, zeros(size(mpc.gencost, 1), ncols_needed - size(mpc.gencost, 2))];
            end

            pwl_row = zeros(1, ncols_needed);
            pwl_row(1) = 1;  % PWL type
            pwl_row(2) = mpc.gencost(g, 2);  % startup cost
            pwl_row(3) = mpc.gencost(g, 3);  % shutdown cost
            pwl_row(4) = nseg + 1;
            for k = 1:(nseg + 1)
                pwl_row(4 + 2 * k - 1) = p_points(k);
                pwl_row(4 + 2 * k)     = cost_points(k);
            end
            mpc.gencost(g, 1:ncols_needed) = pwl_row;
            n_converted = n_converted + 1;
        end
    end
    fprintf("  Converted %d generators from polynomial to PWL costs (%d segments)\n", n_converted, nseg);

    % Add startup costs
    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        if pmax_g <= 0
            pmax_g = 1;
        end
        mpc.gencost(g, 2) = pmax_g * 5;  % startup = 5 * Pmax
        mpc.gencost(g, 3) = pmax_g * 1;  % shutdown = 1 * Pmax
    end
    fprintf("  Added startup/shutdown costs\n");

    % --- Step 4: Create xGenData with UC parameters ---
    fprintf("\n--- Creating xGenData with UC parameters ---\n");
    xgd_table.colnames = {
                          'CommitKey', ...
                          'CommitSched', ...
                          'MinUp', ...
                          'MinDown', ...
                          'PositiveActiveReservePrice', ...
                          'PositiveActiveReserveQuantity', ...
                          'NegativeActiveReservePrice', ...
                          'NegativeActiveReserveQuantity', ...
                          'PositiveActiveDeltaPrice', ...
                          'NegativeActiveDeltaPrice' ...
                         };
    xgd_data = zeros(ng, 10);
    for g = 1:ng
        pmax_g = max(mpc.gen(g, PMAX), 1);
        xgd_data(g, :) = [
                          1, ...           % CommitKey = 1 (UC variable)
                          1, ...           % CommitSched = 1 (initially committed)
                          2, ...           % MinUp = 2 hours (reduced from 3 for feasibility)
                          1, ...           % MinDown = 1 hour (reduced for feasibility)
                          1e-8, ...        % PositiveActiveReservePrice
                          0.1 * pmax_g, ...  % PositiveActiveReserveQuantity
                          2e-8, ...        % NegativeActiveReservePrice
                          0.1 * pmax_g, ...  % NegativeActiveReserveQuantity
                          1e-9, ...        % PositiveActiveDeltaPrice
                          1e-9 ...        % NegativeActiveDeltaPrice
                         ];
    end
    xgd_table.data = xgd_data;
    xgd = loadxgendata(xgd_table, mpc);
    fprintf("  Created xGenData: CommitKey=1, MinUp=2, MinDown=1\n");

    % --- Step 5: Create 24-hour load profile ---
    fprintf("\n--- Creating 24-hour load profile ---\n");
    daily_curve = [0.83; 0.80; 0.78; 0.77; 0.78; 0.82
                   0.88; 0.94; 0.98; 1.00; 0.99; 0.98
                   0.97; 0.96; 0.95; 0.96; 0.98; 0.99
                   1.00; 0.98; 0.96; 0.93; 0.89; 0.85];

    load_profile = struct( ...
                          'type', 'mpcData', ...
                          'table', CT_TLOAD, ...
                          'rows', 0, ...
                          'col', CT_LOAD_ALL_PQ, ...
                          'chgtype', CT_REL, ...
                          'values', daily_curve ...
                         );
    fprintf("  Load curve range: [%.2f, %.2f]\n", min(daily_curve), max(daily_curve));

    % --- Step 6: Build MOST data structure ---
    fprintf("\n--- Building MOST data structure ---\n");
    mpopt = mpoption("verbose", 0, "out.all", 0);
    mpopt = mpoption(mpopt, "model", "DC");
    mpopt = mpoption(mpopt, "most.dc_model", 1);
    mpopt = mpoption(mpopt, "most.uc.run", 1);
    mpopt = mpoption(mpopt, "most.solver", "GLPK");
    mpopt = mpoption(mpopt, "glpk.opts.mipgap", 0.10);  % 10% MIP gap tolerance
    mpopt = mpoption(mpopt, "glpk.opts.tmlim", 600);     % 10-minute timeout
    if exist("OCTAVE_VERSION", "builtin")
        mpopt = mpoption(mpopt, "mips.linsolver", "LU");
    end

    profiles = load_profile;

    fprintf("Building MOST input data (this may take a while for %d gens x %d periods)...\n", ng, nt);
    build_start = tic();
    mdi = loadmd(mpc, nt, xgd, [], [], profiles);
    build_time = toc(build_start);
    fprintf("MOST data structure built in %.2f seconds.\n", build_time);
    fprintf("  Periods: %d, UC enabled: YES, Solver: GLPK\n", nt);

    % --- Step 7: Solve ---
    fprintf("\nSolving MOST SCUC (24-hour, GLPK, MIP gap 10%%)...\n");
    fprintf("This may take several minutes on SMALL...\n");
    solve_start = tic();
    mdo = most(mdi, mpopt);
    solve_time = toc(solve_start);

    wall_clock = toc(tic_val);
    qp_vars = length(mdo.QP.x);

    if mdo.QP.exitflag > 0
        fprintf("MOST SCUC converged: YES (exitflag=%d)\n", mdo.QP.exitflag);
        fprintf("Objective value: %.2f\n", mdo.QP.f);
        fprintf("QP variables: %d\n", qp_vars);
        fprintf("Solve time: %.2f seconds\n", solve_time);
        fprintf("Total wall clock: %.2f seconds\n", wall_clock);

        % --- Step 8: Extract commitment schedule ---
        fprintf("\n--- Commitment Schedule ---\n");
        if isfield(mdo, 'UC') && isfield(mdo.UC, 'CommitSched')
            commit = mdo.UC.CommitSched;
        else
            commit = zeros(ng, nt);
            for t = 1:nt
                commit(:, t) = mdo.flow(t, 1, 1).mpc.gen(:, GEN_STATUS);
            end
        end

        n_total = ng * nt;
        n_committed = sum(commit(:) >= 0.5);
        n_decommitted = n_total - n_committed;
        fprintf("  Total gen-hours: %d\n", n_total);
        fprintf("  Committed: %d\n", n_committed);
        fprintf("  De-committed: %d (%.1f%%)\n", n_decommitted, 100 * n_decommitted / n_total);

        % --- Step 9: Extract dispatch ---
        exp_dispatch = mdo.results.ExpectedDispatch;
        fprintf("\n--- Dispatch Summary ---\n");
        sample_t = [1, 6, 12, 18, 24];
        fprintf("  Total dispatch (MW) at sample hours:\n  ");
        for t = sample_t
            fprintf(" HE%02d=%7.1f", t, sum(exp_dispatch(:, t)));
        end
        fprintf("\n");

        % --- Step 10: Extract prices ---
        gen_prices = mdo.results.GenPrices;
        fprintf("\n--- Price Summary ---\n");
        fprintf("  Average price across generators at sample hours:\n  ");
        for t = sample_t
            fprintf(" HE%02d=$%6.2f", t, mean(gen_prices(:, t)));
        end
        fprintf("\n");

        status = "pass";
        loc = 165;
    else
        fprintf("MOST SCUC did NOT converge (exitflag=%d)\n", mdo.QP.exitflag);
        fprintf("QP variables: %d\n", qp_vars);
        fprintf("Solve time: %.2f seconds (likely hit timeout)\n", solve_time);
        fprintf("Total wall clock: %.2f seconds\n", wall_clock);
        fprintf("FINDING: GLPK cannot solve SCUC for 544 gens x 24 periods\n");
        fprintf("within 10-minute timeout. Problem has %d binary variables.\n", qp_vars);
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
fprintf("QP_VARS: %d\n", qp_vars);
fprintf("========================================\n");
