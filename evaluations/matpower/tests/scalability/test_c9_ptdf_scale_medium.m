%% Test C-9: PTDF Scale on ACTIVSg 10k (MEDIUM)
%%
%% Pass condition: PTDF matrix computable on MEDIUM. Performance recorded.
%% Also compute LODF via makeLODF.
%%
%% Note: ACTIVSg10k has non-consecutive bus numbering, so ext2int()
%% conversion is required before calling makePTDF/makeLODF.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c9_ptdf_scale_medium.m

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
fprintf("TEST C-9: PTDF Scale on MEDIUM (ACTIVSg 10k)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Load case ---
    mpc_ext = loadcase(network_file);
    nb = size(mpc_ext.bus, 1);
    nbr = size(mpc_ext.branch, 1);
    ng = size(mpc_ext.gen, 1);
    fprintf("Loaded %d buses, %d branches, %d generators\n", nb, nbr, ng);
    fprintf("External bus IDs range: [%d, %d]\n", min(mpc_ext.bus(:, BUS_I)), max(mpc_ext.bus(:, BUS_I)));

    % Convert to internal (consecutive) ordering
    fprintf("Converting to internal ordering (ext2int)...\n");
    mpc = ext2int(mpc_ext);
    nb_int = size(mpc.bus, 1);
    nbr_int = size(mpc.branch, 1);
    fprintf("Internal: %d buses, %d branches\n", nb_int, nbr_int);

    ref_bus = find(mpc.bus(:, BUS_TYPE) == REF);
    fprintf("Reference bus index: %d\n", ref_bus(1));

    load_time = toc(tic_val);
    fprintf("Case load + conversion time: %.4f seconds\n", load_time);

    % --- Step 1: Compute PTDF matrix ---
    fprintf("\n--- Computing PTDF matrix ---\n");
    tic_ptdf = tic();
    H = makePTDF(mpc);
    time_ptdf = toc(tic_ptdf);

    fprintf("PTDF computation time: %.4f seconds\n", time_ptdf);
    fprintf("PTDF matrix dimensions: %d x %d\n", size(H, 1), size(H, 2));

    % Verify dimensions
    assert(size(H, 1) == nbr_int, "PTDF row count != branch count");
    assert(size(H, 2) == nb_int, "PTDF col count != bus count");

    % Matrix properties
    n_elements = numel(H);
    if issparse(H)
        n_nonzero = nnz(H);
        fprintf("PTDF storage: sparse\n");
    else
        n_nonzero = nnz(abs(H) > 1e-10);
        fprintf("PTDF storage: dense\n");
    end
    density = n_nonzero / n_elements;
    fprintf("Total elements: %d (%.0f million)\n", n_elements, n_elements / 1e6);
    fprintf("Non-zero elements (>1e-10): %d\n", n_nonzero);
    fprintf("Density: %.4f (%.2f%%)\n", density, 100 * density);
    fprintf("PTDF value range: [%.6f, %.6f]\n", min(H(:)), max(H(:)));

    % Memory estimate for PTDF
    if issparse(H)
        ptdf_mem_mb = (n_nonzero * 12 + (size(H, 2) + 1) * 4) / 1e6;
    else
        ptdf_mem_mb = n_elements * 8 / 1e6;  % dense double
    end
    fprintf("PTDF memory estimate: %.1f MB\n", ptdf_mem_mb);

    % Slack column check
    ref_col = H(:, ref_bus(1));
    fprintf("Slack column max abs: %.2e (should be ~0)\n", max(abs(ref_col)));

    % --- Step 2: Verify PTDF against DCPF ---
    fprintf("\n--- Verifying PTDF against DCPF ---\n");
    mpopt = mpoption("verbose", 0, "out.all", 0);
    results = rundcpf(mpc, mpopt);
    assert(results.success, "DCPF did not converge");

    Pf_dcpf = results.branch(:, PF);

    % Build net bus injection vector in per-unit
    Pbus = -results.bus(:, PD) / mpc.baseMVA;
    for g = 1:ng
        gen_bus_idx = results.gen(g, GEN_BUS);  % already internal index
        Pbus(gen_bus_idx) = Pbus(gen_bus_idx) + results.gen(g, PG) / mpc.baseMVA;
    end

    Pf_ptdf = H * Pbus * mpc.baseMVA;
    flow_error = abs(Pf_ptdf - Pf_dcpf);
    max_error = max(flow_error);
    mean_error = mean(flow_error);

    fprintf("Max flow error: %.2e MW\n", max_error);
    fprintf("Mean flow error: %.2e MW\n", mean_error);

    tol = 1e-3;  % looser tolerance for 10k network numerical effects
    fprintf("Tolerance: %.0e MW\n", tol);
    fprintf("Within tolerance: %s\n", mat2str(max_error < tol));

    if max_error >= tol
        fprintf("WARNING: Max error exceeds tolerance (%.2e), but PTDF is still computable\n", max_error);
    end

    % --- Step 3: Compute LODF matrix ---
    fprintf("\n--- Computing LODF matrix ---\n");
    tic_lodf = tic();
    LODF = makeLODF(H, mpc);
    time_lodf = toc(tic_lodf);

    fprintf("LODF computation time: %.4f seconds\n", time_lodf);
    fprintf("LODF matrix dimensions: %d x %d\n", size(LODF, 1), size(LODF, 2));

    if issparse(LODF)
        lodf_nnz = nnz(LODF);
        fprintf("LODF storage: sparse (%d non-zeros)\n", lodf_nnz);
    else
        lodf_nnz = nnz(abs(LODF) > 1e-10);
        fprintf("LODF storage: dense\n");
        fprintf("LODF non-zero elements (>1e-10): %d\n", lodf_nnz);
    end
    lodf_density = lodf_nnz / numel(LODF);
    fprintf("LODF density: %.4f (%.2f%%)\n", lodf_density, 100 * lodf_density);

    % --- Summary ---
    wall_clock = toc(tic_val);

    fprintf("\n--- Summary ---\n");
    fprintf("PTDF: %d x %d, computed in %.4f s, density %.2f%%\n", ...
            nbr_int, nb_int, time_ptdf, 100 * density);
    fprintf("LODF: %d x %d, computed in %.4f s, density %.2f%%\n", ...
            nbr_int, nbr_int, time_lodf, 100 * lodf_density);
    fprintf("PTDF-vs-DCPF max error: %.2e MW\n", max_error);
    fprintf("Total wall clock: %.4f seconds\n", wall_clock);

    status = "pass";
    loc = 75;

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
