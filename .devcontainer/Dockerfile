# grc-tech-evaluation devcontainer
# Multi-language image: Python 3.12, Julia 1.10, GNU Octave
# with pre-installed dependencies for all six power-system evaluation tools.

# === Layer 1: Base image ===
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# === Layer 2: System packages (rarely changes) ===
# Python 3.12 ships with Ubuntu 24.04.
# Octave 8.x from apt. curl needed for Julia download and MATPOWER setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        octave \
        liboctave-dev \
        unzip \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# === Layer 3: Julia 1.10 installation (rarely changes) ===
ARG JULIA_VERSION=1.10.7
RUN curl -fsSL \
        "https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-${JULIA_VERSION}-linux-x86_64.tar.gz" \
        -o /tmp/julia.tar.gz \
    && tar -xzf /tmp/julia.tar.gz -C /usr/local --strip-components=1 \
    && rm /tmp/julia.tar.gz \
    && julia --version

# === Layer 4: uv installation (rarely changes) ===
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# === Layer 5: Environment variables ===
ENV JULIA_CPU_TARGET=generic

# === Layer 6: Copy repository source for dependency installation ===
COPY . /workspace

# === Layer 7: Python tool dependencies ===
RUN cd /workspace/evaluations/gridcal && uv sync
RUN cd /workspace/evaluations/pandapower && uv sync
RUN cd /workspace/evaluations/pypsa && uv sync

# === Layer 8: Julia tool dependencies ===
RUN julia --project=/workspace/evaluations/powermodels \
    -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
RUN julia --project=/workspace/evaluations/powersimulations \
    -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'

# === Layer 9: MATPOWER download ===
RUN cd /workspace/evaluations/matpower && bash setup.sh
