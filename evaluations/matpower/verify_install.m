% Verify MATPOWER installation by running power flow on IEEE 39-bus case.
%
% Usage: octave verify_install.m

% Add MATPOWER to path
addpath(fullfile(pwd, 'matpower-8.1', 'lib'));
addpath(fullfile(pwd, 'matpower-8.1', 'data'));

% Load IEEE 39-bus case from shared data directory
mpc = loadcase(fullfile('..', '..', 'data', 'networks', 'case39.m'));

fprintf('MATPOWER version: %s\n', mpver());
fprintf('Buses: %d\n', size(mpc.bus, 1));
fprintf('Branches: %d\n', size(mpc.branch, 1));

% Run DC power flow
results = rundcpf(mpc);

if results.success
    fprintf('DC power flow completed successfully\n');
    exit(0);
else
    fprintf('DC power flow failed\n');
    exit(1);
end
