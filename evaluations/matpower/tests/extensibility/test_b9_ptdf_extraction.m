%% Test B-9: Compute PTDF matrix for TINY, verify dimensions and flow accuracy
%%
%% Dimension: extensibility
%% Network: TINY (IEEE 39-bus New England)
%% Pass condition: PTDF matrix accessible via native API. Flow predictions
%%   match DCPF within 1e-6. Handle phase-shifting transformers.
%% Tool: MATPOWER 8.1

function result = test_b9_ptdf_extraction(network_file)
    if nargin < 1
        network_file = '/workspace/data/networks/case39.m';
    end

    result = struct();
    result.status = 'fail';
    result.wall_clock_seconds = 0;
    result.details = struct();
    result.errors = {};
    result.workarounds = {};

    %% Setup MATPOWER
    mp_root = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'matpower8.1');
    addpath(fullfile(mp_root, 'lib'));
    addpath(fullfile(mp_root, 'data'));
    addpath(fullfile(mp_root, 'mips', 'lib'));
    addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
    addpath(fullfile(mp_root, 'mptest', 'lib'));

    tic;
    try
        %% Load case
        mpc = loadcase(network_file);
        define_constants;

        nb = size(mpc.bus, 1);
        nl = size(mpc.branch, 1);
        ng = size(mpc.gen, 1);

        %% Check for phase-shifting transformers
        shift_vals = mpc.branch(:, SHIFT);
        n_phase_shifters = sum(abs(shift_vals) > 1e-6);
        fprintf('=== Phase-Shifter Analysis ===\n');
        fprintf('Branches with nonzero SHIFT: %d / %d\n', n_phase_shifters, nl);

        %% Solve DCPF for reference flows
        mpopt = mpoption('verbose', 0, 'out.all', 0);
        results_dcpf = rundcpf(mpc, mpopt);
        if ~results_dcpf.success
            error('DC power flow failed');
        end
        ref_flows = results_dcpf.branch(:, PF);  % MW

        %% Compute PTDF matrix via native API
        ptdf_tic = tic;
        H = makePTDF(mpc.baseMVA, mpc.bus, mpc.branch);
        ptdf_time = toc(ptdf_tic);

        fprintf('\n=== PTDF Matrix ===\n');
        fprintf('Dimensions: %d x %d (branches x buses)\n', size(H, 1), size(H, 2));
        fprintf('Expected: %d x %d\n', nl, nb);
        fprintf('Density: %.2f%%\n', 100 * nnz(H) / numel(H));
        fprintf('Computation time: %.4f s\n', ptdf_time);

        dim_ok = (size(H, 1) == nl) && (size(H, 2) == nb);

        %% Compute bus power injections (Pbus)
        %% Pbus = Pgen - Pload at each bus (in MW)
        Pbus = zeros(nb, 1);
        for i = 1:nb
            Pbus(i) = -mpc.bus(i, PD);  % load is negative injection
        end
        for i = 1:ng
            if mpc.gen(i, GEN_STATUS) > 0
                bus_idx = find(mpc.bus(:, BUS_I) == mpc.gen(i, GEN_BUS));
                Pbus(bus_idx) = Pbus(bus_idx) + results_dcpf.gen(i, PG);
            end
        end

        %% Method 1: Uncorrected flow prediction
        %% flow = H * Pbus (with Pbus in per-unit)
        Pbus_pu = Pbus / mpc.baseMVA;
        ptdf_flows_uncorrected = H * Pbus_pu * mpc.baseMVA;

        %% Method 2: Corrected flow prediction (with Pbusinj/Pfinj)
        [Bbus, Bf, Pbusinj, Pfinj] = makeBdc(mpc.baseMVA, mpc.bus, mpc.branch);
        ptdf_flows_corrected = (H * (Pbus_pu - Pbusinj) + Pfinj) * mpc.baseMVA;

        %% Compute errors
        error_uncorrected = abs(ptdf_flows_uncorrected - ref_flows);
        error_corrected = abs(ptdf_flows_corrected - ref_flows);

        max_err_uncorr = max(error_uncorrected);
        max_err_corr = max(error_corrected);
        mean_err_corr = mean(error_corrected);

        fprintf('\n=== Flow Accuracy ===\n');
        fprintf('Max error (uncorrected): %.6e MW\n', max_err_uncorr);
        fprintf('Max error (corrected):   %.6e MW\n', max_err_corr);
        fprintf('Mean error (corrected):  %.6e MW\n', mean_err_corr);

        %% Print top branches by error
        fprintf('\n=== Top 5 Branches by Error (corrected) ===\n');
        [sorted_err, err_idx] = sort(error_corrected, 'descend');
        for i = 1:min(5, nl)
            bi = err_idx(i);
            fprintf('Branch %d (%d -> %d): DCPF=%.3f MW, PTDF=%.3f MW, Error=%.6e MW\n', ...
                    bi, mpc.branch(bi, F_BUS), mpc.branch(bi, T_BUS), ...
                    ref_flows(bi), ptdf_flows_corrected(bi), sorted_err(i));
        end

        %% If phase shifters exist, also report filtered accuracy
        if n_phase_shifters > 0
            non_ps_mask = abs(shift_vals) < 1e-6;
            max_err_filtered = max(error_uncorrected(non_ps_mask));
            fprintf('\nMax error (non-phase-shifter branches only): %.6e MW\n', max_err_filtered);
            result.details.max_error_filtered = max_err_filtered;
        end

        %% Tolerance check
        tol = 1e-6;  % MW
        flow_ok = max_err_corr < tol;
        fprintf('\nFlow accuracy within %.0e MW: %s\n', tol, mat2str(flow_ok));

        %% Peak memory
        [~, mem_out] = system('grep VmHWM /proc/self/status');
        peak_kb = sscanf(mem_out, 'VmHWM: %f');
        if ~isempty(peak_kb)
            peak_memory_mb = peak_kb / 1024;
        else
            peak_memory_mb = -1;
        end

        %% Store results
        result.details.ptdf_rows = size(H, 1);
        result.details.ptdf_cols = size(H, 2);
        result.details.ptdf_density_pct = 100 * nnz(H) / numel(H);
        result.details.ptdf_time = ptdf_time;
        result.details.max_error_uncorrected = max_err_uncorr;
        result.details.max_error_corrected = max_err_corr;
        result.details.mean_error_corrected = mean_err_corr;
        result.details.n_phase_shifters = n_phase_shifters;
        result.details.peak_memory_mb = peak_memory_mb;

        %% Pass condition
        if dim_ok && flow_ok
            result.status = 'pass';
            fprintf('\n=== PASS: PTDF extraction and flow validation successful ===\n');
        else
            if ~dim_ok
                result.errors{end+1} = sprintf('PTDF dimension mismatch: got %dx%d, expected %dx%d', ...
                                               size(H,1), size(H,2), nl, nb);
            end
            if ~flow_ok
                result.errors{end+1} = sprintf('Flow error exceeds tolerance: %.6e > %.6e', ...
                                               max_err_corr, tol);
            end
        end

    catch e
        result.errors{end+1} = e.message;
        fprintf('ERROR: %s\n', e.message);
    end
    result.wall_clock_seconds = toc;
end

%% Run when executed as script
result = test_b9_ptdf_extraction();
disp(result);
disp(result.details);
