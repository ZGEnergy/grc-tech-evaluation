function fail_count = test_gate(data_dir)
    % test_gate -- Gate tests for MATPOWER: load, parse, solve.
    %
    % Args:
    %   data_dir : path to shared data/networks/ directory
    %
    % Returns:
    %   fail_count : 0 if all tests pass, 1 if any test fails

    fail_count = 0;

    % --- Test 1: Load MATPOWER ---
    try
        ver = mpver();
        fprintf('  [PASS] test_load_matpower: MATPOWER version %s\n', ver);
    catch e
        fprintf('  [FAIL] test_load_matpower: %s\n', e.message);
        fail_count = 1;
        return
    end

    % --- Test 2: Parse case39 ---
    try
        case_file = fullfile(data_dir, 'case39.m');
        mpc = loadcase(case_file);

        assert(size(mpc.bus, 1) == 39, 'Expected 39 buses, got %d', size(mpc.bus, 1));
        assert(size(mpc.branch, 1) == 46, 'Expected 46 branches, got %d', size(mpc.branch, 1));
        assert(size(mpc.gen, 1) == 10, 'Expected 10 generators, got %d', size(mpc.gen, 1));

        fprintf('  [PASS] test_parse_case39: %d buses, %d branches, %d generators\n', ...
                size(mpc.bus, 1), size(mpc.branch, 1), size(mpc.gen, 1));
    catch e
        fprintf('  [FAIL] test_parse_case39: %s\n', e.message);
        fail_count = 1;
        return
    end

    % --- Test 3: Solve DC power flow ---
    try
        mpopt = mpoption('out.all', 0);
        results = rundcpf(mpc, mpopt);

        assert(results.success == 1, 'DC power flow did not converge');

        va = results.bus(:, 9);
        assert(any(va ~= 0), 'All voltage angles are zero -- trivial solution');

        pf = results.branch(:, 14);
        assert(any(pf ~= 0), 'All branch power flows are zero -- trivial solution');

        n_angles = sum(va ~= 0);
        n_flows = sum(pf ~= 0);
        fmt = '  [PASS] test_dc_power_flow: converged, %d non-zero angles, %d non-zero flows\n';
        fprintf(fmt, n_angles, n_flows);
    catch e
        fprintf('  [FAIL] test_dc_power_flow: %s\n', e.message);
        fail_count = 1;
    end

end
