% Test G-FNM-1: Two-check gate -- PSS/E format compatibility + record count fidelity
%
% Dimension: fnm_ingestion
% Network: LARGE (FNM Annual S01)
% Pass condition: (a) PSS/E compatibility: if the tool fails to parse the
%   intermediate CSV tables, record failure_reason: psse_parse_error, emit a blocking
%   api-friction observation, and proceed to G-FNM-3/4/5 via MATPOWER fallback.
%   (b) Record count fidelity (only checked if PSS/E parsing succeeds).
% Tool: MATPOWER 8.1

% Add MATPOWER to path
mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));

fprintf('\n=== G-FNM-1: FNM Ingestion Gate ===\n\n');

tic_id = tic;

% Sub-check (a): PSS/E format compatibility
%
% MATPOWER is a MATLAB/Octave tool. It natively uses:
%   - .m case files (MATPOWER case format)
%   - .mat files (binary MATLAB format)
%   - PSS/E RAW files via psse2mpc()
%
% The intermediate CSV tables are a format-neutral representation of PSS/E
% v31 record types (bus.csv, branch.csv, transformer.csv, etc.). MATPOWER
% has NO built-in function to import these CSVs.

fprintf('Sub-check (a): PSS/E format compatibility\n\n');
fprintf('MATPOWER native import formats:\n');
fprintf('  1. MATPOWER case format (.m/.mat) via loadcase()\n');
fprintf('  2. PSS/E RAW format via psse2mpc()\n\n');

% Confirm psse2mpc exists
has_psse2mpc = exist('psse2mpc', 'file') > 0;
fprintf('psse2mpc function available: %d\n', has_psse2mpc);

% Confirm no CSV table import function exists
has_csv_import = false;
csv_funcs = {'csv2mpc', 'importcsv', 'load_csv', 'readcsv'};
for i = 1:length(csv_funcs)
    if exist(csv_funcs{i}, 'file') > 0
        has_csv_import = true;
        fprintf('Found CSV import function: %s\n', csv_funcs{i});
    end
end
fprintf('CSV table import available: %d\n\n', has_csv_import);

% Result
fprintf('RESULT: FAIL\n');
fprintf('failure_reason: psse_parse_error\n\n');
fprintf('Explanation:\n');
fprintf('MATPOWER has no built-in function to import intermediate CSV tables.\n');
fprintf('It supports MATPOWER case format (.m/.mat) and PSS/E RAW format\n');
fprintf('(via psse2mpc). The intermediate CSVs represent PSS/E v31 records\n');
fprintf('in a tool-neutral tabular format. Mapping these 17 CSV tables to\n');
fprintf('MATPOWER''s MPC struct (bus/branch/gen matrices) would require a\n');
fprintf('complete custom importer. This is a fundamental format incompatibility.\n\n');

% Sub-check (b): Record count fidelity
fprintf('Sub-check (b): Record count fidelity\n');
fprintf('BLOCKED - CSV parsing not possible, sub-check (b) cannot be evaluated.\n\n');

% Fallback path
fprintf('Fallback path for G-FNM-3/4/5:\n');
fallback = fullfile('..', '..', 'data', 'fnm', 'reference', 'cleaned', 'fnm_main_island.mat');
fprintf('  %s\n', fallback);
if exist(fallback, 'file')
    fprintf('  Fallback file EXISTS.\n');
else
    fprintf('  Fallback file not found at relative path (expected in devcontainer).\n');
end

elapsed = toc(tic_id);
fprintf('\nWall clock: %.3f seconds\n', elapsed);
fprintf('\nG-FNM-2 (field coverage) is BLOCKED by this failure.\n');
