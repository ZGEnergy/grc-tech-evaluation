#!/usr/bin/env bash
# Download and extract MATPOWER 8.1 for GNU Octave evaluation.
set -euo pipefail

MATPOWER_VERSION="8.1"
MATPOWER_URL="https://github.com/MATPOWER/matpower/releases/download/${MATPOWER_VERSION}/matpower-${MATPOWER_VERSION}.tar.gz"
MATPOWER_SHA256="553fe603b1f5d4e5be0e94dd0ee8c22c1e0bfb27f236fc24d9e6b09b4cd0db88"
DEST_DIR="matpower-${MATPOWER_VERSION}"

if [ -d "$DEST_DIR" ]; then
    echo "MATPOWER ${MATPOWER_VERSION} already extracted at ${DEST_DIR}/"
    exit 0
fi

echo "Downloading MATPOWER ${MATPOWER_VERSION}..."
curl -L -o "matpower-${MATPOWER_VERSION}.tar.gz" "$MATPOWER_URL"

echo "Verifying checksum..."
echo "${MATPOWER_SHA256}  matpower-${MATPOWER_VERSION}.tar.gz" | sha256sum -c -

echo "Extracting..."
tar xzf "matpower-${MATPOWER_VERSION}.tar.gz"
rm "matpower-${MATPOWER_VERSION}.tar.gz"

echo "MATPOWER ${MATPOWER_VERSION} installed to ${DEST_DIR}/"
