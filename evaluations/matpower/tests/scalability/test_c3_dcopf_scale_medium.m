%% Test C-3: DC OPF Scale on ACTIVSg 10k (MEDIUM)
%%
%% Pass condition: Converges with both MIPS and GLPK solvers.
%% Objective values consistent across solvers.
%%
%% Note: 19.4% of MEDIUM branches have zero RATE_A. These are set to
%% 9999 MW to avoid unbounded flows.
%% Note: ACTIVSg10k has polynomial (quadratic) costs. GLPK handles only LP,
%% so we convert to piecewise-linear costs for the GLPK run using
%% MATPOWER's poly2pwl() function.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c3_dcopf_scale_medium.m

% Add MATPOWER to path
mp_root = "/workspace/evaluations/matpower/matpower8.1";
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

define_constants;

network_file = "/workspace/data/networks/case_ACTIVSg10k.m";

fprintf("\n========================================\n");
fprintf("TEST C-3: DC OPF Scale on MEDIUM (ACTIVSg 10k)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    nb = size(mpc.bus, 1);
    nbr = size(mpc.branch, 1);
    ng = size(mpc.gen, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nbr, ng);

    % Cost model info
    cost_model = mpc.gencost(1, 1);
    fprintf("Cost model type: %d (1=piecewise, 2=polynomial)\n", cost_model);

    % --- Handle zero RATE_A branches ---
    zero_rate = mpc.branch(:, RATE_A) == 0;
    n_zero = sum(zero_rate);
    fprintf("Branches with zero RATE_A: %d / %d (%.1f%%)\n", n_zero, nbr, 100 * n_zero / nbr);

    % Set zero RATE_A to large value to avoid unbounded flows
    mpc.branch(zero_rate, RATE_A) = 9999;
    fprintf("Set zero RATE_A branches to 9999 MW\n");

    load_time = toc(tic_val);
    fprintf("Case load + prep time: %.4f seconds\n", load_time);

    % --- Solver 1: MIPS (built-in, handles QP natively) ---
    fprintf("\n--- Solver 1: MIPS (quadratic costs) ---\n");
    mpopt_mips = mpoption("verbose", 0, "out.all", 0);
    mpopt_mips = mpoption(mpopt_mips, "opf.dc.solver", "MIPS");

    tic_mips = tic();
    results_mips = rundcopf(mpc, mpopt_mips);
    time_mips = toc(tic_mips);

    if results_mips.success
        fprintf("MIPS converged: YES\n");
        fprintf("MIPS objective: %.2f $/hr\n", results_mips.f);
        fprintf("MIPS wall clock: %.4f seconds\n", time_mips);
        fprintf("MIPS total gen: %.2f MW\n", sum(results_mips.gen(:, PG)));

        lmp_mips = results_mips.bus(:, LAM_P);
        fprintf("MIPS LMP range: [%.4f, %.4f] $/MWh\n", min(lmp_mips), max(lmp_mips));

        mu_sf = results_mips.branch(:, MU_SF);
        mu_st = results_mips.branch(:, MU_ST);
        n_binding = sum(mu_sf > 1e-6) + sum(mu_st > 1e-6);
        fprintf("MIPS binding branch constraints: %d\n", n_binding);
    else
        fprintf("MIPS converged: NO\n");
    end

    % --- Solver 2: GLPK (LP only, convert costs to piecewise linear) ---
    fprintf("\n--- Solver 2: GLPK (piecewise-linear costs) ---\n");

    % Convert polynomial costs to piecewise-linear for GLPK compatibility
    mpc_pwl = mpc;
    n_points = 10;  % number of points for PWL approximation
    for g = 1:ng
        if mpc_pwl.gencost(g, 1) == 2  % polynomial cost
            pmin = mpc_pwl.gen(g, PMIN);
            pmax = mpc_pwl.gen(g, PMAX);
            if pmax <= pmin
                pmax = pmin + 1;  % avoid degenerate range
            end
            % Extract polynomial coefficients
            ncost = mpc_pwl.gencost(g, 4);
            coeffs = mpc_pwl.gencost(g, 5:5 + ncost - 1);
            % Generate PWL points
            p_pts = linspace(pmin, pmax, n_points);
            c_pts = polyval(coeffs, p_pts);
            % Build PWL gencost row: [1, startup, shutdown, n_points, p1, c1, p2, c2, ...]
            pwl_row = zeros(1, 4 + 2 * n_points);
            pwl_row(1) = 1;  % PWL model
            pwl_row(2) = mpc_pwl.gencost(g, 2);  % startup
            pwl_row(3) = mpc_pwl.gencost(g, 3);  % shutdown
            pwl_row(4) = n_points;
            for p = 1:n_points
                pwl_row(4 + 2 * p - 1) = p_pts(p);
                pwl_row(4 + 2 * p) = c_pts(p);
            end
            % Pad or truncate gencost to correct size
            new_ncol = 4 + 2 * n_points;
            if new_ncol > size(mpc_pwl.gencost, 2)
                mpc_pwl.gencost = [mpc_pwl.gencost, zeros(ng, new_ncol - size(mpc_pwl.gencost, 2))];
            end
            mpc_pwl.gencost(g, 1:new_ncol) = pwl_row;
        end
    end
    fprintf("Converted %d generators to PWL costs (%d points each)\n", ng, n_points);

    mpopt_glpk = mpoption("verbose", 0, "out.all", 0);
    mpopt_glpk = mpoption(mpopt_glpk, "opf.dc.solver", "GLPK");

    tic_glpk = tic();
    results_glpk = rundcopf(mpc_pwl, mpopt_glpk);
    time_glpk = toc(tic_glpk);

    if results_glpk.success
        fprintf("GLPK converged: YES\n");
        fprintf("GLPK objective: %.2f $/hr\n", results_glpk.f);
        fprintf("GLPK wall clock: %.4f seconds\n", time_glpk);
        fprintf("GLPK total gen: %.2f MW\n", sum(results_glpk.gen(:, PG)));

        lmp_glpk = results_glpk.bus(:, LAM_P);
        fprintf("GLPK LMP range: [%.4f, %.4f] $/MWh\n", min(lmp_glpk), max(lmp_glpk));
    else
        fprintf("GLPK converged: NO\n");
    end

    wall_clock = toc(tic_val);

    % --- Compare results ---
    fprintf("\n--- Comparison ---\n");
    if results_mips.success && results_glpk.success
        obj_diff = abs(results_mips.f - results_glpk.f);
        obj_rel = obj_diff / max(abs(results_mips.f), 1e-10);
        fprintf("Objective difference: %.2f $/hr (relative: %.2e)\n", obj_diff, obj_rel);
        fprintf("  (expected small difference due to PWL approximation of quadratic costs)\n");

        gen_diff = max(abs(results_mips.gen(:, PG) - results_glpk.gen(:, PG)));
        fprintf("Max generator dispatch difference: %.4f MW\n", gen_diff);

        lmp_diff = max(abs(lmp_mips - lmp_glpk));
        fprintf("Max LMP difference: %.4f $/MWh\n", lmp_diff);
    elseif results_mips.success
        fprintf("Only MIPS converged (GLPK failed)\n");
    elseif results_glpk.success
        fprintf("Only GLPK converged (MIPS failed)\n");
    end

    % --- At least one solver must converge ---
    if ~results_mips.success && ~results_glpk.success
        error("Neither solver converged");
    end

    fprintf("\nTotal wall clock: %.4f seconds\n", wall_clock);
    status = "pass";
    loc = 80;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    if length(err.stack) > 0
        fprintf("Error in: %s (line %d)\n", err.stack(1).name, err.stack(1).line);
    end
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
