function peak_mb = get_peak_rss()
    [~, out] = system('grep VmHWM /proc/self/status');
    peak_mb = sscanf(out, 'VmHWM: %f') / 1024;  % kB to MB
end
