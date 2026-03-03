% test/run_tests.m -- MATPOWER test driver
%
% Sets up MATPOWER paths and runs all test scripts.
% Exit code: 0 if all tests pass, 1 if any test fails.
%
% Usage: cd evaluations/matpower && octave test/run_tests.m

% --- Path setup ---
mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(pwd, 'test'));

% --- Shared data path ---
data_dir = fullfile(pwd, '..', '..', 'data', 'networks');

% --- Run test scripts ---
failures = 0;

fprintf('\n=== MATPOWER Gate Tests ===\n\n');

failures = failures + test_gate(data_dir);

fprintf('\n=== Summary ===\n');
if failures > 0
    fprintf('FAILED: %d test script(s) had failures\n', failures);
    exit(1);
else
    fprintf('All tests passed\n');
    exit(0);
end
