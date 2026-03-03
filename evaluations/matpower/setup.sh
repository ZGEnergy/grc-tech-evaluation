#!/usr/bin/env bash
# Download and extract MATPOWER 8.1 for GNU Octave evaluation.
set -euo pipefail

MATPOWER_VERSION="8.1"
MATPOWER_URL="https://github.com/MATPOWER/matpower/releases/download/${MATPOWER_VERSION}/matpower${MATPOWER_VERSION}.zip"
MATPOWER_SHA256="7f13b1441669a64e312d14a60e564cd91977ff1676ff77d25538e94ff313dd56"
DEST_DIR="matpower${MATPOWER_VERSION}"

if [ -d "$DEST_DIR" ]; then
    echo "MATPOWER ${MATPOWER_VERSION} already extracted at ${DEST_DIR}/"
    exit 0
fi

echo "Downloading MATPOWER ${MATPOWER_VERSION}..."
curl -L -o "matpower${MATPOWER_VERSION}.zip" "$MATPOWER_URL"

echo "Verifying checksum..."
echo "${MATPOWER_SHA256}  matpower${MATPOWER_VERSION}.zip" | sha256sum -c -

echo "Extracting..."
unzip -q "matpower${MATPOWER_VERSION}.zip"
rm "matpower${MATPOWER_VERSION}.zip"

echo "MATPOWER ${MATPOWER_VERSION} installed to ${DEST_DIR}/"
