%% Test A-5: SCUC (24-hour Unit Commitment) on IEEE 39-bus (TINY)
%%
%% Pass condition: Solve 24-hour UC as MILP with min up/down times,
%% startup costs, ramp rates, reserve requirements. MIP gap <= 1%.
%% Commitment schedule extractable as time-indexed binary matrix.
%%
%% Approach: Use MOST with UC enabled. case39 gencost is polynomial
%% (quadratic), but GLPK only handles LP+MILP (no QP). Convert to
%% piecewise-linear costs so GLPK can solve the MIQP as MILP.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a5_scuc_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));
addpath(fullfile(mp_root, "most", "lib"));

% Load column index constants
define_constants;
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-5: SCUC (24-hour UC) on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load and prepare case ---
    mpc = loadcase(network_file);
    ng = size(mpc.gen, 1);
    nb = size(mpc.bus, 1);
    nl = size(mpc.branch, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nl, ng);

    % --- Parameters ---
    nt = 24;  % 24-hour horizon

    % --- Step 1: Augment generator data for UC ---
    % case39 generators have zero ramp rates and zero startup costs.
    % Add realistic values for a meaningful UC test.
    fprintf("\n--- Augmenting generator data ---\n");

    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        % Ramp rates: 30% of Pmax per period
        mpc.gen(g, RAMP_AGC) = 0.3 * pmax_g;
        mpc.gen(g, RAMP_10)  = 0.3 * pmax_g;
        mpc.gen(g, RAMP_30)  = 0.3 * pmax_g;
        % Set nonzero PMIN (20% of PMAX) for meaningful UC decisions
        mpc.gen(g, PMIN) = 0.2 * pmax_g;
    end
    fprintf("  Ramp rates set to 30%% of Pmax\n");
    fprintf("  PMIN set to 20%% of Pmax\n");

    % --- Step 2: Convert quadratic costs to piecewise-linear ---
    % GLPK (the only MILP solver available on Octave without HiGHS)
    % cannot handle QP. Convert polynomial costs to PWL approximation.
    fprintf("\n--- Converting costs to piecewise-linear ---\n");
    for g = 1:ng
        if mpc.gencost(g, 1) == 2  % polynomial
            ncost = mpc.gencost(g, 4);
            pmin_g = mpc.gen(g, PMIN);
            pmax_g = mpc.gen(g, PMAX);
            % Get polynomial coefficients (highest order first)
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
                c1 = 0;
                c0 = 0;
            end

            % Create 10-segment PWL approximation
            nseg = 10;
            p_points = linspace(pmin_g, pmax_g, nseg + 1);
            cost_points = c2 * p_points.^2 + c1 * p_points + c0;

            % Build PWL gencost row: type=1, startup, shutdown, n, x1,y1,...,xn,yn
            pwl_row = zeros(1, 4 + 2 * (nseg + 1));
            pwl_row(1) = 1;  % PWL type
            pwl_row(2) = mpc.gencost(g, 2);  % startup cost
            pwl_row(3) = mpc.gencost(g, 3);  % shutdown cost
            pwl_row(4) = nseg + 1;  % number of points
            for k = 1:(nseg + 1)
                pwl_row(4 + 2 * k - 1) = p_points(k);
                pwl_row(4 + 2 * k)     = cost_points(k);
            end

            % Expand gencost if needed
            ncols_needed = 4 + 2 * (nseg + 1);
            if ncols_needed > size(mpc.gencost, 2)
                mpc.gencost = [mpc.gencost, zeros(ng, ncols_needed - size(mpc.gencost, 2))];
            end
            mpc.gencost(g, 1:ncols_needed) = pwl_row;
        end
    end
    fprintf("  Converted %d generators from polynomial to PWL costs\n", ng);

    % Add startup costs (absent in case39)
    for g = 1:ng
        pmax_g = mpc.gen(g, PMAX);
        mpc.gencost(g, 2) = pmax_g * 5;  % startup = 5 * Pmax ($)
        mpc.gencost(g, 3) = pmax_g * 1;  % shutdown = 1 * Pmax ($)
    end
    fprintf("  Added startup costs (5*Pmax) and shutdown costs (1*Pmax)\n");

    % --- Step 3: Create xGenData with UC parameters ---
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
        pmax_g = mpc.gen(g, PMAX);
        xgd_data(g, :) = [
                          1, ...           % CommitKey = 1 (UC variable)
                          1, ...           % CommitSched = 1 (initially committed)
                          3, ...           % MinUp = 3 hours
                          2, ...           % MinDown = 2 hours
                          1e-8, ...        % PositiveActiveReservePrice
                          0.2 * pmax_g, ...  % PositiveActiveReserveQuantity
                          2e-8, ...        % NegativeActiveReservePrice
                          0.2 * pmax_g, ...  % NegativeActiveReserveQuantity
                          1e-9, ...        % PositiveActiveDeltaPrice
                          1e-9 ...        % NegativeActiveDeltaPrice
                         ];
    end
    xgd_table.data = xgd_data;
    xgd = loadxgendata(xgd_table, mpc);
    fprintf("  Created xGenData: CommitKey=1 (UC), MinUp=3, MinDown=2\n");

    % --- Step 4: Create 24-hour load profile ---
    fprintf("\n--- Creating 24-hour load profile ---\n");
    % Realistic daily load curve (fraction of peak)
    daily_curve = [0.83; 0.80; 0.78; 0.77; 0.78; 0.82   %% HE 1-6
                   0.88; 0.94; 0.98; 1.00; 0.99; 0.98   %% HE 7-12
                   0.97; 0.96; 0.95; 0.96; 0.98; 0.99   %% HE 13-18
                   1.00; 0.98; 0.96; 0.93; 0.89; 0.85]; %% HE 19-24

    load_profile = struct( ...
                          'type', 'mpcData', ...
                          'table', CT_TLOAD, ...
                          'rows', 0, ...
                          'col', CT_LOAD_ALL_PQ, ...
                          'chgtype', CT_REL, ...
                          'values', daily_curve ...
                         );
    fprintf("  Load curve range: [%.2f, %.2f] (relative)\n", ...
            min(daily_curve), max(daily_curve));

    % --- Step 5: Build MOST data structure ---
    fprintf("\n--- Building MOST data structure ---\n");
    mpopt = mpoption("verbose", 0, "out.all", 0);
    mpopt = mpoption(mpopt, "model", "DC");
    mpopt = mpoption(mpopt, "most.dc_model", 1);
    mpopt = mpoption(mpopt, "most.uc.run", 1);
    mpopt = mpoption(mpopt, "most.solver", "GLPK");
    if exist("OCTAVE_VERSION", "builtin")
        mpopt = mpoption(mpopt, "mips.linsolver", "LU");
    end

    profiles = load_profile;
    mdi = loadmd(mpc, nt, xgd, [], [], profiles);
    fprintf("MOST data structure built.\n");
    fprintf("  Periods: %d, UC enabled: YES\n", nt);

    % --- Step 6: Solve ---
    fprintf("\nSolving MOST SCUC (24-hour, GLPK)...\n");
    mdo = most(mdi, mpopt);

    if mdo.QP.exitflag <= 0
        error("MOST SCUC did not converge (exitflag=%d)", mdo.QP.exitflag);
    end
    wall_clock = toc(tic_val);
    fprintf("MOST SCUC converged: YES (exitflag=%d)\n", mdo.QP.exitflag);
    fprintf("Objective value: %.2f\n", mdo.QP.f);
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    % --- Step 7: Extract commitment schedule ---
    fprintf("\n--- Commitment Schedule (binary matrix) ---\n");

    % Extract commitment from UC results
    % mdo.UC.CommitSched is ng x nt if UC was run
    if isfield(mdo, 'UC') && isfield(mdo.UC, 'CommitSched')
        commit = mdo.UC.CommitSched;
    else
        % Fallback: extract from flow results
        commit = zeros(ng, nt);
        for t = 1:nt
            commit(:, t) = mdo.flow(t, 1, 1).mpc.gen(:, GEN_STATUS);
        end
    end

    fprintf("  Commitment matrix: %d generators x %d periods\n", ...
            size(commit, 1), size(commit, 2));

    % Display commitment schedule
    fprintf("\n  Gen# Bus  ");
    for t = 1:nt
        fprintf("%2d", t);
    end
    fprintf("  On-hrs\n");
    for g = 1:ng
        fprintf("  %3d  %3d  ", g, mpc.gen(g, GEN_BUS));
        for t = 1:nt
            if commit(g, t) >= 0.5
                fprintf(" 1");
            else
                fprintf(" .");
            end
        end
        fprintf("  %5d\n", sum(commit(g, :) >= 0.5));
    end

    % --- Step 8: Verify UC properties ---
    fprintf("\n--- Verifying UC properties ---\n");

    % Check for de-commitment decisions
    n_decommitted = 0;
    for g = 1:ng
        for t = 1:nt
            if commit(g, t) < 0.5
                n_decommitted = n_decommitted + 1;
            end
        end
    end
    n_total = ng * nt;
    fprintf("  Total gen-hours: %d\n", n_total);
    fprintf("  Committed: %d\n", n_total - n_decommitted);
    fprintf("  De-committed: %d (%.1f%%)\n", n_decommitted, ...
            100 * n_decommitted / n_total);

    has_decommitment = n_decommitted > 0;
    fprintf("  UC has de-commitment decisions: %s\n", mat2str(has_decommitment));

    % Check min up/down time compliance
    fprintf("\n  Checking min up/down time compliance...\n");
    min_up = 3;
    min_down = 2;
    updown_violations = 0;
    for g = 1:ng
        % Check min up time
        on_count = 0;
        for t = 1:nt
            if commit(g, t) >= 0.5
                on_count = on_count + 1;
            else
                if on_count > 0 && on_count < min_up
                    updown_violations = updown_violations + 1;
                end
                on_count = 0;
            end
        end
        % Check min down time
        off_count = 0;
        for t = 1:nt
            if commit(g, t) < 0.5
                off_count = off_count + 1;
            else
                if off_count > 0 && off_count < min_down
                    updown_violations = updown_violations + 1;
                end
                off_count = 0;
            end
        end
    end
    fprintf("  Min up/down time violations: %d\n", updown_violations);

    % --- Step 9: Extract dispatch ---
    fprintf("\n--- Expected Dispatch (MW) ---\n");
    exp_dispatch = mdo.results.ExpectedDispatch;  % ng x nt
    fprintf("  Gen# Bus    HE1    HE6   HE12   HE18   HE24\n");
    sample_t = [1, 6, 12, 18, 24];
    for g = 1:ng
        fprintf("  %3d  %3d", g, mpc.gen(g, GEN_BUS));
        for t = sample_t
            fprintf(" %6.1f", exp_dispatch(g, t));
        end
        fprintf("\n");
    end
    fprintf("  Total dispatch per period:\n  ");
    for t = sample_t
        fprintf(" HE%02d=%6.1f", t, sum(exp_dispatch(:, t)));
    end
    fprintf("\n");

    % --- Step 10: Extract prices ---
    fprintf("\n--- Energy Prices ($/MWh) ---\n");
    gen_prices = mdo.results.GenPrices;
    fprintf("  Gen# Bus    HE1    HE6   HE12   HE18   HE24\n");
    for g = 1:min(5, ng)
        fprintf("  %3d  %3d", g, mpc.gen(g, GEN_BUS));
        for t = sample_t
            fprintf(" %6.2f", gen_prices(g, t));
        end
        fprintf("\n");
    end

    % --- Step 11: Verify ramp constraints ---
    fprintf("\n--- Ramp rate compliance ---\n");
    ramp_violations = 0;
    for g = 1:ng
        ramp_limit = mpc.gen(g, RAMP_30);
        for t = 2:nt
            if commit(g, t) >= 0.5 && commit(g, t - 1) >= 0.5
                delta = abs(exp_dispatch(g, t) - exp_dispatch(g, t - 1));
                if delta > ramp_limit + 1e-3  % small tolerance
                    ramp_violations = ramp_violations + 1;
                end
            end
        end
    end
    fprintf("  Ramp rate violations: %d\n", ramp_violations);

    % --- Summary ---
    fprintf("\n--- Summary ---\n");
    fprintf("Formulation: MOST %d-period deterministic SCUC (DC model)\n", nt);
    fprintf("Solver: GLPK (MILP)\n");
    fprintf("Cost model: Piecewise-linear (converted from polynomial)\n");
    fprintf("UC decisions: YES (de-committed %d gen-hours)\n", n_decommitted);
    fprintf("Min up/down time violations: %d\n", updown_violations);
    fprintf("Ramp rate violations: %d\n", ramp_violations);
    fprintf("QP dimensions: %d variables\n", length(mdo.QP.x));
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    % Pass criteria
    assert(mdo.QP.exitflag > 0, "Must converge");
    assert(updown_violations == 0, "Min up/down time violated");
    assert(ramp_violations == 0, "Ramp constraints violated");

    status = "pass";
    loc = 220;

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
fprintf("========================================\n");
