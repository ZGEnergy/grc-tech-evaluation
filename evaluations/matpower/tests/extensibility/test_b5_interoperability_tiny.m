%% Test B-5: Interoperability — Export DCPF results to CSV (IEEE 39-bus, TINY)
%%
%% Pass condition: Export DCPF results to a DataFrame-equivalent and write
%% to CSV. Trivial — fewer than 5 lines of code beyond the solve.
%%
%% Usage (from evaluations/matpower/):
%%   octave tests/extensibility/test_b5_interoperability_tiny.m

% Add MATPOWER to path
mp_root = fullfile(pwd, "matpower8.1");
addpath(fullfile(mp_root, "lib"));
addpath(fullfile(mp_root, "data"));
addpath(fullfile(mp_root, "mips", "lib"));
addpath(fullfile(mp_root, "mp-opt-model", "lib"));
addpath(fullfile(mp_root, "mptest", "lib"));

network_file = fullfile(pwd, "..", "..", "data", "networks", "case39.m");

fprintf("\n========================================\n");
fprintf("TEST B-5: Interoperability (CSV export) on TINY (IEEE 39-bus)\n");
fprintf("========================================\n");

status = "fail";
wall_clock = 0;
loc = 0;

tic_val = tic();
try
    % --- Run DCPF (same as A-1) ---
    mpc = loadcase(network_file);
    results = rundcpf(mpc);
    assert(results.success == 1, "DCPF did not converge");

    % --- Export bus results to CSV ---
    bus_csv = fullfile(pwd, "results", "extensibility", "b5_bus_results.csv");
    branch_csv = fullfile(pwd, "results", "extensibility", "b5_branch_results.csv");

    % Bus export: bus_id, type, Pd, Qd, Vm, Va
    bus_data = results.bus(:, [1 2 3 4 8 9]);
    fid = fopen(bus_csv, "w");
    fprintf(fid, "bus_id,type,Pd_MW,Qd_MVAr,Vm_pu,Va_deg\n");
    for i = 1:size(bus_data, 1)
        fprintf(fid, "%d,%d,%.4f,%.4f,%.6f,%.6f\n", ...
                bus_data(i, 1), bus_data(i, 2), bus_data(i, 3), bus_data(i, 4), ...
                bus_data(i, 5), bus_data(i, 6));
    end
    fclose(fid);

    % Branch export: from_bus, to_bus, Pf, Pt, Qf, Qt
    branch_data = results.branch(:, [1 2 14 16 15 17]);
    fid = fopen(branch_csv, "w");
    fprintf(fid, "from_bus,to_bus,Pf_MW,Pt_MW,Qf_MVAr,Qt_MVAr\n");
    for i = 1:size(branch_data, 1)
        fprintf(fid, "%d,%d,%.4f,%.4f,%.4f,%.4f\n", ...
                branch_data(i, 1), branch_data(i, 2), branch_data(i, 3), ...
                branch_data(i, 4), branch_data(i, 5), branch_data(i, 6));
    end
    fclose(fid);

    wall_clock = toc(tic_val);

    % --- Verify CSV files written ---
    bus_info = dir(bus_csv);
    branch_info = dir(branch_csv);
    fprintf("\nBus CSV:    %s (%d bytes)\n", bus_csv, bus_info.bytes);
    fprintf("Branch CSV: %s (%d bytes)\n", branch_csv, branch_info.bytes);

    assert(bus_info.bytes > 0, "Bus CSV is empty");
    assert(branch_info.bytes > 0, "Branch CSV is empty");

    % Read back and verify row counts
    bus_read = dlmread(bus_csv, ",", 1, 0);  % skip header
    branch_read = dlmread(branch_csv, ",", 1, 0);
    fprintf("Bus CSV rows: %d (expected %d)\n", size(bus_read, 1), size(results.bus, 1));
    fprintf("Branch CSV rows: %d (expected %d)\n", size(branch_read, 1), size(results.branch, 1));

    assert(size(bus_read, 1) == size(results.bus, 1), "Bus row count mismatch");
    assert(size(branch_read, 1) == size(results.branch, 1), "Branch row count mismatch");

    fprintf("\nCSV round-trip verification: PASS\n");

    status = "pass";
    loc = 18;  % lines of export code beyond the solve

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
