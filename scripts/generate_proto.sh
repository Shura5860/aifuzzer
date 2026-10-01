#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROTO_DIR="${ROOT_DIR}/proto"
PY_OUT_DIR="${ROOT_DIR}/services/gateway-py/src/gateway/proto"

mkdir -p "${PY_OUT_DIR}"

echo "Protobuf Python kodları üretiliyor..."
uv run --project "${ROOT_DIR}/services/gateway-py" python -m grpc_tools.protoc \
    -I"${PROTO_DIR}" \
    --python_out="${PY_OUT_DIR}" \
    --grpc_python_out="${PY_OUT_DIR}" \
    "${PROTO_DIR}/fuzzer.proto"

# Python göreceli import düzeltmesi
touch "${PY_OUT_DIR}/__init__.py"
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' 's/import fuzzer_pb2 as fuzzer__pb2/from . import fuzzer_pb2 as fuzzer__pb2/' "${PY_OUT_DIR}/fuzzer_pb2_grpc.py"
else
    sed -i 's/import fuzzer_pb2 as fuzzer__pb2/from . import fuzzer_pb2 as fuzzer__pb2/' "${PY_OUT_DIR}/fuzzer_pb2_grpc.py"
fi

echo "Python Protobuf kodları üretildi: ${PY_OUT_DIR}"
