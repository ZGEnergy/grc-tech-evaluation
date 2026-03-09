% Probe-032b: Verify MOST loadmd() failure on ACTIVSg 2000
% Focus on whether non-consecutive bus numbering causes the failure

mp_root = fullfile(pwd, 'matpower8.1');
addpath(fullfile(mp_root, 'lib'));
addpath(fullfile(mp_root, 'data'));
addpath(fullfile(mp_root, 'mips', 'lib'));
addpath(fullfile(mp_root, 'mp-opt-model', 'lib'));
addpath(fullfile(mp_root, 'mptest', 'lib'));
addpath(fullfile(mp_root, 'most', 'lib'));

fprintf('=== Probe-032b: MOST loadmd() Bus Numbering Test ===\n');
fprintf('MATPOWER version: %s\n', mpver());

% Load ACTIVSg 2000
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case_ACTIVSg2000.m'));
nb = size(mpc.bus, 1);
ng = size(mpc.gen, 1);
fprintf('Buses: %d, Generators: %d\n', nb, ng);
fprintf('Bus IDs range: %d to %d (non-consecutive)\n', min(mpc.bus(:, 1)), max(mpc.bus(:, 1)));

% Step 1: Read loadmd source for bus numbering check
fprintf('\n--- Step 1: loadmd source analysis ---\n');
which_loadmd = which('loadmd');
fprintf('loadmd location: %s\n', which_loadmd);

fid = fopen(which_loadmd, 'r');
if fid ~= -1
    lines = {};
    while ~feof(fid)
        lines{end + 1} = fgetl(fid);
    end
    fclose(fid);

    fprintf('Total lines in loadmd.m: %d\n', length(lines));

    % Search for bus numbering validation
    for i = 1:length(lines)
        line = lines{i};
        if ischar(line)
            if ~isempty(strfind(line, 'consecutive')) || ...
               ~isempty(strfind(line, 'ext2int')) || ...
               ~isempty(strfind(line, 'bus number')) || ...
               ~isempty(strfind(line, 'BUS_I'))
                fprintf('Line %d: %s\n', i, strtrim(line));
            end
        end
    end
end

% Step 2: Build proper xGenData struct for MOST
fprintf('\n--- Step 2: Build proper xGenData ---\n');
% MOST requires specific fields in xGenData
xgd = struct();
xgd.CommitSched = ones(ng, 1);       % all committed
xgd.CommitKey = ones(ng, 1);         % all must-run
xgd.MinUp = ones(ng, 1);             % min up time
xgd.MinDown = ones(ng, 1);           % min down time
xgd.InitialState = ones(ng, 1) * 24; % been on for 24 hours
xgd.RampWearCostCoeff = zeros(ng, 1);
xgd.PositiveActiveReservePrice = zeros(ng, 1);
xgd.PositiveActiveReserveQuantity = zeros(ng, 1);
xgd.NegativeActiveReservePrice = zeros(ng, 1);
xgd.NegativeActiveReserveQuantity = zeros(ng, 1);
xgd.PositiveActiveDeltaPrice = zeros(ng, 1);
xgd.NegativeActiveDeltaPrice = zeros(ng, 1);
xgd.PositiveLoadFollowReservePrice = zeros(ng, 1);
xgd.PositiveLoadFollowReserveQuantity = zeros(ng, 1);
xgd.NegativeLoadFollowReservePrice = zeros(ng, 1);
xgd.NegativeLoadFollowReserveQuantity = zeros(ng, 1);

nt = 24;

% Step 3: Try loadmd with non-consecutive bus numbering
fprintf('\n--- Step 3: loadmd with non-consecutive buses ---\n');
try
    md = loadmd(mpc, [], xgd, [], nt);
    fprintf('loadmd: SUCCESS (unexpected!)\n');
    fprintf('md fields: ');
    disp(fieldnames(md));
catch e
    fprintf('loadmd: FAILED\n');
    fprintf('Error: %s\n', e.message);
    % Print the full error stack
    for i = 1:length(e.stack)
        fprintf('  at %s:%d (%s)\n', e.stack(i).file, e.stack(i).line, e.stack(i).name);
    end
    if ~isempty(strfind(e.message, 'consecutive'))
        fprintf('\n>>> CONFIRMED: fails due to non-consecutive bus numbering\n');
    end
end

% Step 4: Try loadmd with ext2int-converted case
fprintf('\n--- Step 4: loadmd with ext2int-converted case ---\n');
mpc_int = ext2int(mpc);
ng_int = size(mpc_int.gen, 1);
fprintf('Internal buses: %d, generators: %d\n', size(mpc_int.bus, 1), ng_int);

% Rebuild xgd for internal generator count (ext2int may remove offline gens)
xgd_int = struct();
xgd_int.CommitSched = ones(ng_int, 1);
xgd_int.CommitKey = ones(ng_int, 1);
xgd_int.MinUp = ones(ng_int, 1);
xgd_int.MinDown = ones(ng_int, 1);
xgd_int.InitialState = ones(ng_int, 1) * 24;
xgd_int.RampWearCostCoeff = zeros(ng_int, 1);
xgd_int.PositiveActiveReservePrice = zeros(ng_int, 1);
xgd_int.PositiveActiveReserveQuantity = zeros(ng_int, 1);
xgd_int.NegativeActiveReservePrice = zeros(ng_int, 1);
xgd_int.NegativeActiveReserveQuantity = zeros(ng_int, 1);
xgd_int.PositiveActiveDeltaPrice = zeros(ng_int, 1);
xgd_int.NegativeActiveDeltaPrice = zeros(ng_int, 1);
xgd_int.PositiveLoadFollowReservePrice = zeros(ng_int, 1);
xgd_int.PositiveLoadFollowReserveQuantity = zeros(ng_int, 1);
xgd_int.NegativeLoadFollowReservePrice = zeros(ng_int, 1);
xgd_int.NegativeLoadFollowReserveQuantity = zeros(ng_int, 1);

try
    md = loadmd(mpc_int, [], xgd_int, [], nt);
    fprintf('loadmd: SUCCESS with ext2int-converted case\n');
    fprintf('>>> This means the failure IS caused by non-consecutive bus numbering\n');
catch e
    fprintf('loadmd: FAILED even with ext2int\n');
    fprintf('Error: %s\n', e.message);
    for i = 1:length(e.stack)
        fprintf('  at %s:%d (%s)\n', e.stack(i).file, e.stack(i).line, e.stack(i).name);
    end
end

% Step 5: Test with the case39 (known consecutive buses) as control
fprintf('\n--- Step 5: Control test with case39 (consecutive buses) ---\n');
mpc39 = loadcase(fullfile('..', '..', 'data', 'networks', 'case39.m'));
ng39 = size(mpc39.gen, 1);
fprintf('case39: %d buses, %d generators\n', size(mpc39.bus, 1), ng39);
fprintf('Bus IDs consecutive: %s\n', ...
        mat2str(isequal(mpc39.bus(:, 1), (1:size(mpc39.bus, 1))')));

xgd39 = struct();
xgd39.CommitSched = ones(ng39, 1);
xgd39.CommitKey = ones(ng39, 1);
xgd39.MinUp = ones(ng39, 1);
xgd39.MinDown = ones(ng39, 1);
xgd39.InitialState = ones(ng39, 1) * 24;
xgd39.RampWearCostCoeff = zeros(ng39, 1);
xgd39.PositiveActiveReservePrice = zeros(ng39, 1);
xgd39.PositiveActiveReserveQuantity = zeros(ng39, 1);
xgd39.NegativeActiveReservePrice = zeros(ng39, 1);
xgd39.NegativeActiveReserveQuantity = zeros(ng39, 1);
xgd39.PositiveActiveDeltaPrice = zeros(ng39, 1);
xgd39.NegativeActiveDeltaPrice = zeros(ng39, 1);
xgd39.PositiveLoadFollowReservePrice = zeros(ng39, 1);
xgd39.PositiveLoadFollowReserveQuantity = zeros(ng39, 1);
xgd39.NegativeLoadFollowReservePrice = zeros(ng39, 1);
xgd39.NegativeLoadFollowReserveQuantity = zeros(ng39, 1);

try
    md = loadmd(mpc39, [], xgd39, [], nt);
    fprintf('loadmd on case39: SUCCESS\n');
catch e
    fprintf('loadmd on case39: FAILED\n');
    fprintf('Error: %s\n', e.message);
end

fprintf('\n=== SUMMARY ===\n');
fprintf('Claim: MOST loadmd() fails at data ingestion due to non-consecutive bus numbering\n');
fprintf('Claim: error says "buses must be numbered consecutively"\n');
