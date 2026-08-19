#!/usr/bin/env bash
# systemd ExecStart 调用：从 EnvironmentFile 读取监听地址。
set -euo pipefail

cd "$(dirname "$0")"
HOST="${LAN_TRANSFER_HOST:-0.0.0.0}"
PORT="${LAN_TRANSFER_PORT:-5000}"

# 单 worker + 多线程：共享文字/过期状态在进程内存里，多 worker 会不一致。
exec .venv/bin/gunicorn \
  --bind "${HOST}:${PORT}" \
  --worker-class gthread \
  --workers 1 \
  --threads 16 \
  --timeout 600 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  wsgi:app
