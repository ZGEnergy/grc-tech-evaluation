%% Test C-1: DCPF Scale on ACTIVSg 10k (MEDIUM)
%%
%% Pass condition: Converges on MEDIUM network. Performance recorded.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/scalability/test_c1_dcpf_scale_medium.m

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
fprintf("TEST C-1: DCPF Scale on MEDIUM (ACTIVSg 10k)\n");
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

    load_time = toc(tic_val);
    fprintf("Case load time: %.4f seconds\n", load_time);

    % --- Run DC power flow ---
    mpopt = mpoption("verbose", 0, "out.all", 0);

    fprintf("\nRunning DCPF...\n");
    tic_solve = tic();
    results = rundcpf(mpc, mpopt);
    solve_time = toc(tic_solve);
    wall_clock = toc(tic_val);

    if ~results.success
        error("DCPF did not converge");
    end

    fprintf("DCPF converged: YES\n");
    fprintf("Solve time: %.4f seconds\n", solve_time);
    fprintf("Total wall clock (load + solve): %.4f seconds\n", wall_clock);

    % --- Extract key outputs ---
    bus_va = results.bus(:, VA);
    pf = results.branch(:, PF);

    fprintf("\n--- Voltage Angles ---\n");
    fprintf("  Range: [%.4f, %.4f] degrees\n", min(bus_va), max(bus_va));
    fprintf("  Std dev: %.4f degrees\n", std(bus_va));

    fprintf("\n--- Line Flows ---\n");
    fprintf("  Max |flow|: %.2f MW\n", max(abs(pf)));
    fprintf("  Mean |flow|: %.2f MW\n", mean(abs(pf)));
    fprintf("  Non-zero flows: %d / %d\n", sum(abs(pf) > 1e-6), nbr);

    fprintf("\n--- Generation / Load Balance ---\n");
    fprintf("  Total generation: %.2f MW\n", sum(results.gen(:, PG)));
    fprintf("  Total load: %.2f MW\n", sum(results.bus(:, PD)));

    % --- Verify non-trivial ---
    assert(any(bus_va ~= 0), "All voltage angles are zero");
    assert(any(pf ~= 0), "All line flows are zero");
    assert(sum(results.gen(:, PG)) > 0, "No generation dispatched");

    % --- Memory estimate ---
    % Octave does not have a direct memory profiler, estimate from data sizes
    bus_mem = nb * 13 * 8;       % bus matrix: nb x 13 columns x 8 bytes
    branch_mem = nbr * 21 * 8;   % branch matrix: nbr x 21 columns x 8 bytes
    gen_mem = ng * 21 * 8;       % gen matrix: ng x 21 columns x 8 bytes
    % B matrix (sparse): approximately nb x nb with ~3*nbr non-zeros
    b_nnz = 3 * nbr;
    b_mem = b_nnz * 16;          % sparse: 8 bytes value + 8 bytes index per entry
    total_mem_mb = (bus_mem + branch_mem + gen_mem + b_mem) / 1e6;
    fprintf("\n--- Memory Estimate ---\n");
    fprintf("  Data structures: %.1f MB\n", total_mem_mb);
    fprintf("  B matrix (sparse, ~%d nnz): %.1f MB\n", b_nnz, b_mem / 1e6);

    fprintf("\nAll outputs verified: YES\n");
    status = "pass";
    loc = 40;

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
