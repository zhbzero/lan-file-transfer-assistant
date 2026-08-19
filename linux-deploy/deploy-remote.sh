#!/usr/bin/env bash
# 从开发机通过 SSH 同步并安装。用法：bash deploy-remote.sh user@host
# user@host 可以是 ~/.ssh/config 里的 Host 别名。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="/opt/lan-file-transfer"
SSH_TARGET="${1:-}"

if [[ -z "${SSH_TARGET}" ]]; then
  echo "用法: bash deploy-remote.sh <ssh主机，例如 user@192.0.2.10 或 ssh config 中的 Host>" >&2
  exit 1
fi

echo "同步到 ${SSH_TARGET}:${REMOTE_DIR} ..."
ssh "${SSH_TARGET}" "mkdir -p '${REMOTE_DIR}'"
rsync -az --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'env' \
  -e ssh \
  "${ROOT}/" "${SSH_TARGET}:${REMOTE_DIR}/"

echo "在服务器上执行 install.sh ..."
ssh "${SSH_TARGET}" "bash '${REMOTE_DIR}/install.sh'"
