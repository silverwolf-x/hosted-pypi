#!/bin/bash

set -euxo pipefail

if [[ -z "${TALIB_C_VER:-}" ]]; then
  echo "TALIB_C_VER is required" >&2
  exit 1
fi

yum install -y cmake make

curl -fsSL -o /tmp/talib-c.tar.gz \
  "https://github.com/TA-Lib/ta-lib/archive/refs/tags/v${TALIB_C_VER}.tar.gz"

rm -rf "/tmp/ta-lib-${TALIB_C_VER}"
tar -xzf /tmp/talib-c.tar.gz -C /tmp/

cd "/tmp/ta-lib-${TALIB_C_VER}"
mkdir -p include/ta-lib
cp include/*.h include/ta-lib/

mkdir -p _build
cd _build

cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local
make -j"$(nproc)"
make install
ldconfig