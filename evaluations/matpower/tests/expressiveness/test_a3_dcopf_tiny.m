%% Test A-3: DC OPF on IEEE 39-bus (TINY)
%%
%% Pass condition: Converges. Optimal dispatch and LMPs/shadow prices
%% extractable from solution.
%%
%% Solver: MIPS (built-in), handles quadratic cost curves.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a3_dcopf_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load column index constants (PF, QF, PT, QT, MU_SF, MU_ST, LAM_P, etc.)
define_constants;

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-3: DCOPF on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc = loadcase(network_file);
    fprintf("Loaded %d buses, %d branches, %d generators\n", ...
            size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));

    % Check cost model
    if isfield(mpc, "gencost")
        cost_model = mpc.gencost(1, 1);
        fprintf("Cost model type: %d (1=piecewise, 2=polynomial)\n", cost_model);
        n_cost = mpc.gencost(1, 4);
        fprintf("Number of cost coefficients: %d\n", n_cost);
    end

    % --- Configure solver ---
    mpopt = mpoption("verbose", 0, "out.all", 0);
    % MIPS is the default solver for DC OPF; handles QP for polynomial costs

    fprintf("\nRunning DC OPF with MIPS solver...\n");
    results = rundcopf(mpc, mpopt);
    wall_clock = toc(tic_val);

    if ~results.success
        error("DC OPF did not converge");
    end

    fprintf("DC OPF converged: YES\n");
    fprintf("Objective value (total cost): %.2f $/hr\n", results.f);
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    % --- Extract structured outputs ---

    % 1. Optimal generator dispatch
    fprintf("\n--- Optimal Dispatch ---\n");
    fprintf("  Gen#  Bus   PG(MW)   PMIN(MW)  PMAX(MW)\n");
    for g = 1:size(results.gen, 1)
        fprintf("  %3d  %4d  %8.2f  %8.2f  %8.2f\n", ...
                g, results.gen(g, GEN_BUS), results.gen(g, PG), ...
                results.gen(g, PMIN), results.gen(g, PMAX));
    end
    fprintf("  Total dispatch: %.2f MW\n", sum(results.gen(:, PG)));
    fprintf("  Total load:     %.2f MW\n", sum(results.bus(:, PD)));

    % 2. LMPs (Locational Marginal Prices) - LAM_P = bus col 14
    lam_p = results.bus(:, LAM_P);
    bus_ids = results.bus(:, BUS_I);

    fprintf("\n--- LMPs ($/MWh) ---\n");
    fprintf("  Bus   LMP\n");
    sample_buses = [1, 10, 20, 31, 39];
    for k = 1:length(sample_buses)
        idx = find(bus_ids == sample_buses(k));
        if ~isempty(idx)
            fprintf("  %3d   %8.4f\n", sample_buses(k), lam_p(idx));
        end
    end
    fprintf("  LMP range: [%.4f, %.4f] $/MWh\n", min(lam_p), max(lam_p));
    fprintf("  Mean LMP:  %.4f $/MWh\n", mean(lam_p));

    % 3. Line flows (PF=col14, QF=col15, PT=col16, QT=col17)
    pf_flow = results.branch(:, PF);
    pt_flow = results.branch(:, PT);
    fprintf("\n--- Line Flows (first 5) ---\n");
    fprintf("  Br#  From  To     PF(MW)\n");
    for k = 1:min(5, size(results.branch, 1))
        fprintf("  %3d  %4d  %4d  %8.2f\n", ...
                k, results.branch(k, F_BUS), results.branch(k, T_BUS), pf_flow(k));
    end
    fprintf("  Max |flow|: %.2f MW\n", max(abs(pf_flow)));

    % 4. Branch shadow prices (MU_SF=col18, MU_ST=col19)
    mu_sf = results.branch(:, MU_SF);
    mu_st = results.branch(:, MU_ST);
    n_binding = sum(mu_sf > 1e-6) + sum(mu_st > 1e-6);

    fprintf("\n--- Branch Shadow Prices ---\n");
    fprintf("  Binding flow constraints: %d\n", n_binding);
    if n_binding > 0
        binding_idx = find(mu_sf > 1e-6 | mu_st > 1e-6);
        for k = 1:length(binding_idx)
            bi = binding_idx(k);
            fprintf("  Branch %d (%d->%d): MU_SF=%.4f MU_ST=%.4f\n", ...
                    bi, results.branch(bi, F_BUS), results.branch(bi, T_BUS), ...
                    mu_sf(bi), mu_st(bi));
        end
    else
        fprintf("  No binding flow constraints (case39 has no RATE_A limits)\n");
        fprintf("  All LMPs are uniform as expected with unconstrained network\n");
    end

    % --- Verify outputs are non-trivial ---
    assert(results.f > 0, "Objective value is non-positive");
    assert(any(lam_p ~= 0), "All LMPs are zero");
    assert(sum(results.gen(:, PG)) > 0, "No generation dispatched");

    fprintf("\nAll structured outputs accessible: YES\n");
    status = "pass";
    loc = 75;

catch err
    wall_clock = toc(tic_val);
    fprintf("ERROR: %s\n", err.message);
    status = "fail";
end

fprintf("\n========================================\n");
fprintf("STATUS: %s\n", status);
fprintf("WALL_CLOCK: %.4f\n", wall_clock);
fprintf("LOC: %d\n", loc);
fprintf("========================================\n");
