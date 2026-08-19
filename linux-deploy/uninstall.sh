#!/usr/bin/env bash
# 卸载 systemd 服务（默认不删除共享目录里的文件）。
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lan-file-transfer}"
SHARE_DIR="${SHARE_DIR:-/var/lib/lan-file-transfer/share}"
SERVICE_USER="${SERVICE_USER:-lantransfer}"
PURGE_DATA="${PURGE_DATA:-0}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请用 root 运行：sudo bash uninstall.sh" >&2
  exit 1
fi

systemctl disable --now lan-file-transfer.service 2>/dev/null || true
rm -f /etc/systemd/system/lan-file-transfer.service
systemctl daemon-reload

rm -rf "${APP_DIR}"
if [[ "${PURGE_DATA}" == "1" ]]; then
  rm -rf "${SHARE_DIR}"
  echo "已删除共享目录 ${SHARE_DIR}"
else
  echo "保留共享目录 ${SHARE_DIR}（如需一并删除：PURGE_DATA=1 bash uninstall.sh）"
fi

if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  userdel "${SERVICE_USER}" 2>/dev/null || true
fi

echo "已卸载 lan-file-transfer"
