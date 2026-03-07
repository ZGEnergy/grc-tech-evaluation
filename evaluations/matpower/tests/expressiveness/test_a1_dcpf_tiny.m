%% Test A-1: DC Power Flow on IEEE 39-bus (TINY)
%%
%% Pass condition: Converges. Nodal injections, line flows, and voltage
%% angles accessible as structured output.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/expressiveness/test_a1_dcpf_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

% Load shared network
network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST A-1: DCPF on TINY (IEEE 39-bus)\n");
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

    % --- Run DC power flow ---
    results = rundcpf(mpc);
    wall_clock = toc(tic_val);

    if ~results.success
        error("DCPF did not converge");
    end

    fprintf("\nDCPF converged: YES\n");
    fprintf("Wall clock: %.4f seconds\n", wall_clock);

    % --- Extract structured outputs ---

    % 1. Voltage angles (radians -> degrees, stored in bus col 9)
    bus_va = results.bus(:, 9);  % VA column
    fprintf("\n--- Voltage Angles (degrees) ---\n");
    fprintf("  Bus  1: %10.4f\n", bus_va(1));
    fprintf("  Bus 10: %10.4f\n", bus_va(10));
    fprintf("  Bus 31 (slack): %10.4f\n", bus_va(find(results.bus(:, 1) == 31)));
    fprintf("  Min angle: %.4f  Max angle: %.4f\n", min(bus_va), max(bus_va));

    % 2. Nodal injections (P_INJ = PG - PD at each bus)
    %    In DC PF results: bus(:,3) = PD (load), gen(:,2) = PG (generation)
    %    Build net injection per bus
    bus_ids = results.bus(:, 1);
    n_bus = length(bus_ids);
    p_inj = -results.bus(:, 3);  % start with -PD (load is negative injection)
    for g = 1:size(results.gen, 1)
        gen_bus = results.gen(g, 1);
        idx = find(bus_ids == gen_bus);
        p_inj(idx) = p_inj(idx) + results.gen(g, 2);  % add PG
    end
    fprintf("\n--- Nodal Injections (MW) ---\n");
    fprintf("  Bus  1: %10.2f MW\n", p_inj(1));
    fprintf("  Bus 10: %10.2f MW\n", p_inj(10));
    fprintf("  Bus 31 (slack): %10.2f MW\n", p_inj(find(bus_ids == 31)));
    fprintf("  Total generation: %.2f MW\n", sum(results.gen(:, 2)));
    fprintf("  Total load:       %.2f MW\n", sum(results.bus(:, 3)));

    % 3. Line flows (PF = branch col 14, PT = branch col 16 in results)
    pf = results.branch(:, 14);  % P from-end
    pt = results.branch(:, 16);  % P to-end
    fprintf("\n--- Line Flows (MW) ---\n");
    for k = 1:min(5, size(results.branch, 1))
        fprintf("  Branch %2d (%d -> %d): PF = %8.2f MW\n", ...
                k, results.branch(k, 1), results.branch(k, 2), pf(k));
    end
    fprintf("  ... (%d branches total)\n", size(results.branch, 1));
    fprintf("  Max |flow|: %.2f MW\n", max(abs(pf)));

    % --- Verify outputs are non-trivial ---
    assert(any(bus_va ~= 0), "All voltage angles are zero -- trivial solution");
    assert(any(pf ~= 0), "All line flows are zero -- trivial solution");
    assert(sum(results.gen(:, 2)) > 0, "No generation dispatched");

    fprintf("\nAll structured outputs accessible: YES\n");
    status = "pass";
    loc = 55;  % approximate lines of core logic

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
