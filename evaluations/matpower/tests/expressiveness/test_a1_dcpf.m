%% Test A-1: Solve DC power flow on TINY
%%
%% Dimension: expressiveness
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: Converges. Nodal injections, line flows, and voltage angles
%%   accessible as structured output (DataFrame, dict, or named array -- not raw
%%   solver vector).
%% Tool: MATPOWER 8.1

%% Setup MATPOWER paths
mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

network_file = '/workspace/data/networks/case39.m';

result_status = 'fail';
errors = {};
workarounds = {};

try
    %% Load case
    mpc = loadcase(network_file);
    define_constants;

    %% Configure options: suppress output for programmatic use
    mpopt = mpoption('verbose', 0, 'out.all', 0);

    %% Solve DC power flow
    tic;
    results = rundcpf(mpc, mpopt);
    solve_time = toc;

    if ~results.success
        errors{end + 1} = 'DC power flow did not converge';
    else
        %% Extract structured results

        % Bus results
        bus_count = size(results.bus, 1);
        bus_ids = results.bus(:, BUS_I);
        voltage_angles_deg = results.bus(:, VA);
        bus_pd = results.bus(:, PD);

        % Generator results
        gen_count = size(results.gen, 1);
        gen_buses = results.gen(:, GEN_BUS);
        gen_pg = results.gen(:, PG);

        % Branch results
        branch_count = size(results.branch, 1);
        branch_from = results.branch(:, F_BUS);
        branch_to = results.branch(:, T_BUS);
        branch_pf = results.branch(:, PF);
        branch_pt = results.branch(:, PT);

        % Compute nodal injections
        nodal_injections = zeros(bus_count, 1);
        for i = 1:bus_count
            bid = bus_ids(i);
            gen_at_bus = gen_pg(gen_buses == bid);
            nodal_injections(i) = sum(gen_at_bus) - bus_pd(i);
        end

        % Summary statistics
        total_generation = sum(gen_pg);
        total_load = sum(bus_pd);
        max_angle = max(voltage_angles_deg);
        min_angle = min(voltage_angles_deg);
        max_flow = max(abs(branch_pf));
        nonzero_angles = sum(abs(voltage_angles_deg) > 1e-6);

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Print results
        fprintf('\n=== Test A-1: DCPF Results ===\n');
        fprintf('Wall clock: %.4f s\n', solve_time);
        fprintf('Buses: %d, Branches: %d, Generators: %d\n', bus_count, branch_count, gen_count);
        fprintf('Total generation: %.2f MW\n', total_generation);
        fprintf('Total load: %.2f MW\n', total_load);
        fprintf('Angle spread: %.4f deg (min=%.4f, max=%.4f)\n', ...
                max_angle - min_angle, min_angle, max_angle);
        fprintf('Max branch flow: %.2f MW\n', max_flow);
        fprintf('Nonzero voltage angles: %d / %d\n', nonzero_angles, bus_count);
        fprintf('Peak memory: %.1f MB\n', peak_memory_mb);

        fprintf('\nSample bus results (first 5):\n');
        fprintf('  Bus | Angle (deg) | Injection (MW)\n');
        for i = 1:min(5, bus_count)
            fprintf('  %3d | %10.4f  | %10.2f\n', bus_ids(i), voltage_angles_deg(i), ...
                    nodal_injections(i));
        end

        fprintf('\nSample branch results (first 5):\n');
        fprintf('  From -> To  | Pf (MW)   | Pt (MW)\n');
        for i = 1:min(5, branch_count)
            fprintf('  %3d -> %3d | %9.2f | %9.2f\n', branch_from(i), branch_to(i), ...
                    branch_pf(i), branch_pt(i));
        end

        fprintf('\nOutput format: MATPOWER struct with named matrices (bus, gen, branch)\n');
        fprintf('Column access: define_constants provides named indices\n');

        %% Pass condition check
        if results.success && nonzero_angles > 0 && bus_count == 39 && branch_count == 46
            result_status = 'pass';
        end
    end

catch e
    errors{end + 1} = e.message;
end

fprintf('\nStatus: %s\n', result_status);
if ~isempty(errors)
    fprintf('Errors: %s\n', strjoin(errors, '; '));
end
