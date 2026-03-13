# grc-tech-evaluation devcontainer
# Multi-language image: Python 3.12, Julia 1.10, GNU Octave
# with pre-installed dependencies for all six power-system evaluation tools.

# === Base image ===
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# === System packages (rarely changes) ===
# Python 3.12 ships with Ubuntu 24.04.
# Octave 8.x from apt. curl needed for Julia download and MATPOWER setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-dev \
        python3-pip \
        octave \
        octave-dev \
        coinor-libipopt-dev \
        glpk-utils \
        unzip \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# === Julia 1.10 installation (rarely changes) ===
# Julia 1.10 is the current LTS release. Pinned here rather than using the
# julialang devcontainer feature, which installs via juliaup and can silently
# resolve to a newer major version (e.g. 1.12), breaking Manifest.toml compat.
ARG JULIA_VERSION=1.10.7
RUN ARCH=$(dpkg --print-architecture) \
    && if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then \
           JULIA_ARCH="aarch64"; JULIA_DIR="aarch64"; \
       else \
           JULIA_ARCH="x86_64"; JULIA_DIR="x64"; \
       fi \
    && curl -fsSL \
        "https://julialang-s3.julialang.org/bin/linux/${JULIA_DIR}/1.10/julia-${JULIA_VERSION}-linux-${JULIA_ARCH}.tar.gz" \
        -o /tmp/julia.tar.gz \
    && tar -xzf /tmp/julia.tar.gz -C /usr/local --strip-components=1 \
    && rm /tmp/julia.tar.gz \
    && julia --version

# === uv installation (rarely changes) ===
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# === Environment variables ===
# JULIA_DEPOT_PATH: shared depot so packages installed at build time (as root)
# are visible at runtime regardless of which user runs Julia (root vs vscode).
ENV JULIA_CPU_TARGET=generic \
    JULIA_DEPOT_PATH=/opt/julia-depot

# === Dependency files only (cache-friendly) ===
# Copy only lockfiles/manifests first so that dependency-install layers are
# invalidated only when lockfiles change, not on every source edit.
COPY evaluations/gridcal/pyproject.toml evaluations/gridcal/uv.lock \
     /workspace/evaluations/gridcal/
COPY evaluations/pandapower/pyproject.toml evaluations/pandapower/uv.lock \
     /workspace/evaluations/pandapower/
COPY evaluations/pypsa/pyproject.toml evaluations/pypsa/uv.lock \
     /workspace/evaluations/pypsa/
COPY evaluations/powermodels/Project.toml evaluations/powermodels/Manifest.toml \
     /workspace/evaluations/powermodels/
COPY evaluations/powersimulations/Project.toml evaluations/powersimulations/Manifest.toml \
     /workspace/evaluations/powersimulations/

# === Python tool dependencies (only re-runs when lockfiles change) ===
RUN cd /workspace/evaluations/gridcal && uv sync
RUN cd /workspace/evaluations/pandapower && uv sync
RUN cd /workspace/evaluations/pypsa && uv sync

# === Julia tool dependencies (only re-runs when manifests change) ===
RUN julia --project=/workspace/evaluations/powermodels \
    -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
RUN julia --project=/workspace/evaluations/powersimulations \
    -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'

# === Wire Ipopt JLL binary to system PATH ===
# Ubuntu 24.04 dropped the coinor-ipopt binary package. Symlink the JLL
# binary installed with PowerModels/PowerSimulations, and register its
# runtime library paths via ldconfig.
RUN IPOPT_BIN=$(find /opt/julia-depot/artifacts -maxdepth 3 -name 'ipopt' -path '*/bin/*' -print -quit) \
    && ln -sf "$IPOPT_BIN" /usr/local/bin/ipopt \
    && find /opt/julia-depot/artifacts -maxdepth 3 \
           \( -name 'libspral.so' -o -name 'libmetis.so' -o -name 'libasl.so' \) \
           -exec dirname {} \; \
       > /etc/ld.so.conf.d/julia-jll.conf \
    && echo '/usr/local/lib/julia' >> /etc/ld.so.conf.d/julia-jll.conf \
    && ldconfig \
    && ipopt --version

# === JuliaFormatter shared environment (for pre-commit hook) ===
# The pre-commit hook runs: julia --project=@format -e 'using JuliaFormatter; ...'
RUN julia --project=@format -e 'using Pkg; Pkg.add("JuliaFormatter"); Pkg.precompile()'

# Make depot writable by vscode user (packages installed as root during build,
# but Pkg.instantiate() at runtime writes logs/pidfiles as vscode).
RUN chmod -R a+rw /opt/julia-depot

# === Full source copy (cheap — only adds/overwrites non-dep files) ===
COPY . /workspace

# === MATPOWER download ===
RUN cd /workspace/evaluations/matpower && bash setup.sh
