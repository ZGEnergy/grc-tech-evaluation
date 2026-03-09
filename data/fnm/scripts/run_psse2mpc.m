% run_psse2mpc.m -- Convert a PSS/E RAW file to MATPOWER case struct and export CSVs.
%
% Usage:
%   octave --no-gui --no-init-file run_psse2mpc.m <raw_path> <output_dir> [<matpower_path>]
%
% Arguments:
%   raw_path      -- Path to the PSS/E RAW file.
%   output_dir    -- Directory to write CSV exports and .mat file.
%   matpower_path -- (optional) Path to MATPOWER installation directory.
%                   Default: evaluations/matpower/matpower8.1 relative to repo root.
%
% Outputs:
%   Structured stdout lines:
%     MPC_BASEMVA:<value>
%     MPC_VERSION:<version>
%     MPC_FIELD_COUNT:<field>:<count>
%   CSV files: mpc_bus.csv, mpc_gen.csv, mpc_branch.csv, etc.
%   MAT file:  mpc_case.mat

args = argv();
if length(args) < 2
    fprintf(2, 'Usage: run_psse2mpc.m <raw_path> <output_dir> [<matpower_path>]\n');
    exit(1);
end

raw_path = args{1};
output_dir = args{2};

% Determine MATPOWER path
if length(args) >= 3
    matpower_path = args{3};
else
    % Default: relative to this script's location
    % Script is at <repo>/data/fnm/scripts/run_psse2mpc.m
    % MATPOWER is at <repo>/evaluations/matpower/matpower8.1
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fullfile(script_dir, '..', '..', '..');
    matpower_path = fullfile(repo_root, 'evaluations', 'matpower', 'matpower8.1');
end

% Add MATPOWER to path
if ~exist(matpower_path, 'dir')
    fprintf(2, 'ERROR: MATPOWER path not found: %s\n', matpower_path);
    exit(1);
end
addpath(genpath(matpower_path));

% Ensure output directory exists
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

% Verify input file exists
if ~exist(raw_path, 'file')
    fprintf(2, 'ERROR: RAW file not found: %s\n', raw_path);
    exit(1);
end

% Run psse2mpc conversion
try
    [mpc, warnings] = psse2mpc(raw_path, '', 0);
catch err
    fprintf(2, 'ERROR: psse2mpc failed: %s\n', err.message);
    exit(1);
end

% Print structured output
if isfield(mpc, 'baseMVA')
    fprintf('MPC_BASEMVA:%g\n', mpc.baseMVA);
end

if isfield(mpc, 'version')
    fprintf('MPC_VERSION:%s\n', mpc.version);
end

% Export numeric fields as CSV
numeric_fields = {'bus', 'gen', 'branch', 'gencost', 'areas', 'dcline'};

for i = 1:length(numeric_fields)
    fname = numeric_fields{i};
    if isfield(mpc, fname) && ~isempty(mpc.(fname))
        csv_path = fullfile(output_dir, ['mpc_' fname '.csv']);
        csvwrite(csv_path, mpc.(fname));
        row_count = size(mpc.(fname), 1);
        fprintf('MPC_FIELD_COUNT:%s:%d\n', fname, row_count);
    end
end

% Handle bus_name (cell array of strings) separately
if isfield(mpc, 'bus_name') && ~isempty(mpc.bus_name)
    csv_path = fullfile(output_dir, 'mpc_bus_name.csv');
    fid = fopen(csv_path, 'w');
    for i = 1:length(mpc.bus_name)
        fprintf(fid, '%s\n', strtrim(mpc.bus_name{i}));
    end
    fclose(fid);
    fprintf('MPC_FIELD_COUNT:bus_name:%d\n', length(mpc.bus_name));
end

% Save the full mpc struct as .mat
mat_path = fullfile(output_dir, 'mpc_case.mat');
save('-v7', mat_path, 'mpc');

% Print any warnings from psse2mpc
if ~isempty(warnings)
    for i = 1:length(warnings)
        fprintf(2, 'PSSE2MPC_WARNING: %s\n', warnings{i});
    end
end

fprintf('CONVERSION_COMPLETE\n');
