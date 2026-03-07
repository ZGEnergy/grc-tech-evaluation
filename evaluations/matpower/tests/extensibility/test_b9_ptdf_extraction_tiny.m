%% Test B-9: PTDF Matrix Extraction — IEEE 39-bus (TINY)
%%
%% Pass condition: Compute PTDF matrix for TINY (39-bus). Verify dimensions
%% (branches x buses). Verify PTDF-predicted flows match DCPF-solved flows
%% within tolerance (1e-6).
%%
%% depends_on: A-1 (DCPF)
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b9_ptdf_extraction_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

define_constants;

network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST B-9: PTDF Extraction on TINY (IEEE 39-bus)\n");
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

    ref_bus = find(mpc.bus(:, BUS_TYPE) == REF);
    fprintf("Reference bus: %d (index %d)\n", mpc.bus(ref_bus, BUS_I), ref_bus);

    % --- Step 1: Compute PTDF matrix ---
    fprintf("\n--- Computing PTDF matrix ---\n");
    H = makePTDF(mpc);
    fprintf("PTDF matrix dimensions: %d x %d\n", size(H, 1), size(H, 2));

    % Verify dimensions
    assert(size(H, 1) == nbr, "PTDF row count (%d) != branch count (%d)", size(H, 1), nbr);
    assert(size(H, 2) == nb, "PTDF col count (%d) != bus count (%d)", size(H, 2), nb);
    fprintf("Dimension check: PASS (%d branches x %d buses)\n", nbr, nb);

    % --- Step 2: Run DCPF to get reference flows ---
    fprintf("\n--- Running DCPF for reference flows ---\n");
    mpopt = mpoption("verbose", 0, "out.all", 0);
    results = rundcpf(mpc, mpopt);
    assert(results.success, "DCPF did not converge");
    fprintf("DCPF converged: YES\n");

    % Extract solved flows (from-end active power)
    Pf_dcpf = results.branch(:, PF);  % MW

    % --- Step 3: Compute PTDF-predicted flows ---
    fprintf("\n--- Computing PTDF-predicted flows ---\n");

    % Build net bus injection vector (Pbus) in per-unit
    % Pbus = (Pgen - Pload) / baseMVA at each bus
    Pbus = -results.bus(:, PD) / mpc.baseMVA;  % load as negative injection
    for g = 1:ng
        gen_bus_id = results.gen(g, GEN_BUS);
        idx = find(mpc.bus(:, BUS_I) == gen_bus_id);
        Pbus(idx) = Pbus(idx) + results.gen(g, PG) / mpc.baseMVA;
    end

    % PTDF-predicted flows: H * Pbus (result in per-unit, convert to MW)
    Pf_ptdf = H * Pbus * mpc.baseMVA;

    % --- Step 4: Compare flows ---
    fprintf("\n--- Flow Comparison (DCPF vs PTDF-predicted) ---\n");
    flow_error = abs(Pf_ptdf - Pf_dcpf);
    max_error = max(flow_error);
    mean_error = mean(flow_error);

    fprintf("  Max absolute error:  %.2e MW\n", max_error);
    fprintf("  Mean absolute error: %.2e MW\n", mean_error);

    % Show representative branches
    fprintf("\n  Branch  From  To     DCPF(MW)   PTDF(MW)   Error(MW)\n");
    show_branches = [1, 5, 10, 20, 30, 40, 46];
    for k = 1:length(show_branches)
        bi = show_branches(k);
        if bi <= nbr
            fprintf("  %5d  %4d  %4d  %9.4f  %9.4f  %9.2e\n", ...
                    bi, mpc.branch(bi, F_BUS), mpc.branch(bi, T_BUS), ...
                    Pf_dcpf(bi), Pf_ptdf(bi), flow_error(bi));
        end
    end

    % Tolerance check
    tol = 1e-6;
    fprintf("\n  Tolerance: %.0e MW\n", tol);
    fprintf("  Max error within tolerance: %s\n", mat2str(max_error < tol));

    assert(max_error < tol, ...
           "Max flow error (%.2e) exceeds tolerance (%.0e)", max_error, tol);

    % --- Step 5: Verify PTDF properties ---
    fprintf("\n--- PTDF Matrix Properties ---\n");

    % Row corresponding to ref bus should sum to ~0
    % (slack column should be all zeros)
    ref_col = H(:, ref_bus);
    fprintf("  Slack column (bus %d) max abs value: %.2e\n", ...
            mpc.bus(ref_bus, BUS_I), max(abs(ref_col)));
    assert(max(abs(ref_col)) < 1e-10, "Slack bus column should be near-zero");

    % Each row sums to ~0 (for single-slack PTDF)
    row_sums = sum(H, 2);
    fprintf("  Row sums max abs value: %.2e (should be ~0 for single slack)\n", ...
            max(abs(row_sums)));

    % PTDF values should be in [-1, 1] range
    fprintf("  PTDF value range: [%.6f, %.6f]\n", min(H(:)), max(H(:)));
    assert(max(abs(H(:))) <= 1.0 + 1e-10, "PTDF values should be in [-1, 1]");

    % Sparsity
    n_nonzero = nnz(abs(H) > 1e-10);
    n_total = numel(H);
    fprintf("  Non-zero entries: %d / %d (%.1f%%)\n", ...
            n_nonzero, n_total, 100 * n_nonzero / n_total);

    % --- Step 6: Test with distributed slack weights ---
    fprintf("\n--- PTDF with distributed slack ---\n");
    slack_weights = ones(nb, 1) / nb;  % uniform distribution
    H_dist = makePTDF(mpc, slack_weights);
    fprintf("  Distributed-slack PTDF dimensions: %d x %d\n", ...
            size(H_dist, 1), size(H_dist, 2));

    % Distributed-slack PTDF should differ from single-slack
    ptdf_diff = max(abs(H_dist(:) - H(:)));
    fprintf("  Max diff vs single-slack PTDF: %.6f\n", ptdf_diff);
    assert(ptdf_diff > 1e-6, "Distributed slack PTDF should differ from single slack");
    fprintf("  Distributed slack produces different PTDF: YES\n");

    % --- Summary ---
    wall_clock = toc(tic_val);

    fprintf("\n--- Summary ---\n");
    fprintf("PTDF matrix: %d x %d (branches x buses)\n", nbr, nb);
    fprintf("PTDF-predicted flows match DCPF within %.0e: YES\n", tol);
    fprintf("Distributed slack supported: YES (via weight vector)\n");
    fprintf("API call: makePTDF(mpc) — single function, no preprocessing\n");
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    status = "pass";
    loc = 70;

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
