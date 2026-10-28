#!/usr/bin/env bash
set -euo pipefail
TASKROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Network is available only for these dependency-install image builds.
docker build -t oa-exception-python-20261029 -f "$TASKROOT/Dockerfile.python" "$TASKROOT" > "$TASKROOT/build-python.log" 2>&1
docker build -t oa-exception-node-20261029 -f "$TASKROOT/Dockerfile.node" "$TASKROOT" > "$TASKROOT/build-node.log" 2>&1
# All actual probes use a read-only root filesystem and bind, with no network.
FLAGS=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=64m --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,src=$TASKROOT,dst=/work,readonly")
docker run "${FLAGS[@]}" oa-exception-python-20261029 python /work/probe-duckdb.py > "$TASKROOT/raw-duckdb.json" 2> "$TASKROOT/stderr-duckdb.log"
docker run "${FLAGS[@]}" oa-exception-python-20261029 python /work/probe-streamlit.py > "$TASKROOT/raw-streamlit.json" 2> "$TASKROOT/stderr-streamlit.log"
docker run "${FLAGS[@]}" oa-exception-node-20261029 node /work/probe-query.cjs > "$TASKROOT/raw-query.json" 2> "$TASKROOT/stderr-query.log"
