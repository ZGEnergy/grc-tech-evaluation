%% run_tests.m -- Octave test runner for MATPOWER evaluation
%%
%% Copy this file into evaluations/matpower/tests/ to enable test discovery.
%%
%% Usage:
%%   octave tests/run_tests.m                          % run all tests
%%   octave tests/run_tests.m expressiveness           % run one dimension
%%   octave tests/run_tests.m expressiveness test_a1   % run one test

function run_tests(dimension, test_name)
    %% Setup paths
    test_dir = fileparts(mfilename('fullpath'));
    repo_root = fullfile(test_dir, '..', '..', '..', '..');
    data_dir = fullfile(repo_root, 'data', 'networks');

    %% Add MATPOWER to path (assumes setup.sh has been run)
    matpower_dir = fullfile(test_dir, '..', 'matpower8.1');
    if exist(matpower_dir, 'dir')
        addpath(genpath(matpower_dir));
    end

    %% Network file paths
    networks = struct();
    networks.TINY = fullfile(data_dir, 'case39.m');
    networks.SMALL = fullfile(data_dir, 'case_ACTIVSg2000.m');
    networks.MEDIUM = fullfile(data_dir, 'case_ACTIVSg10k.m');
    timeseries.TINY = fullfile(fileparts(data_dir), 'timeseries', 'case39');

    %% Discover test files
    if nargin < 1 || isempty(dimension)
        dimension = '';
    end
    if nargin < 2 || isempty(test_name)
        test_name = '';
    end

    test_files = discover_tests(test_dir, dimension, test_name);

    if isempty(test_files)
        warning('No test files found (dimension=%s, test=%s)', ...
                dimension, test_name);
        return
    end

    fprintf('Found %d test file(s)\n', length(test_files));
    fprintf('==========================================\n');

    %% Run tests
    passed = 0;
    failed = 0;
    errs = 0;

    for i = 1:length(test_files)
        tf = test_files{i};
        [~, fname, ~] = fileparts(tf);
        fprintf('\nRunning: %s\n', fname);
        fprintf('------------------------------------------\n');

        try
            %% Change to test directory so relative paths work
            old_dir = pwd();
            cd(fileparts(tf));

            %% Run the test function
            result = feval(fname);

            cd(old_dir);

            if strcmp(result.status, 'pass') || ...
                    strcmp(result.status, 'qualified_pass')
                fprintf('  PASS (%0.2fs)\n', result.wall_clock_seconds);
                passed = passed + 1;
            else
                fprintf('  FAIL (%0.2fs)\n', result.wall_clock_seconds);
                if isfield(result, 'errors')
                    for j = 1:length(result.errors)
                        fprintf('    Error: %s\n', result.errors{j});
                    end
                end
                failed = failed + 1;
            end
        catch e
            cd(old_dir);
            fprintf('  ERROR: %s\n', e.message);
            errs = errs + 1;
        end
    end

    %% Summary
    fprintf('\n==========================================\n');
    fprintf('Results: %d passed, %d failed, %d errors\n', ...
            passed, failed, errs);
    fprintf('==========================================\n');
end

function test_files = discover_tests(test_dir, dimension, test_name)
    test_files = {};

    if isempty(dimension)
        %% Search all subdirectories
        entries = dir(test_dir);
        for i = 1:length(entries)
            if entries(i).isdir && ~startsWith(entries(i).name, '.')
                dim_path = fullfile(test_dir, entries(i).name);
                files = dir(fullfile(dim_path, 'test_*.m'));
                for j = 1:length(files)
                    if isempty(test_name) || ...
                            contains(files(j).name, test_name)
                        idx = length(test_files) + 1;
                        test_files{idx} = fullfile(dim_path, ...
                                                   files(j).name);
                    end
                end
            end
        end
    else
        dim_path = fullfile(test_dir, dimension);
        if exist(dim_path, 'dir')
            files = dir(fullfile(dim_path, 'test_*.m'));
            for j = 1:length(files)
                if isempty(test_name) || ...
                        contains(files(j).name, test_name)
                    idx = length(test_files) + 1;
                    test_files{idx} = fullfile(dim_path, files(j).name);
                end
            end
        else
            warning('Dimension directory not found: %s', dim_path);
        end
    end

    test_files = sort(test_files);
end
