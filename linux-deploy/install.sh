#!/usr/bin/env bash
# 在 Ubuntu 上安装为 systemd 服务。需 root。
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lan-file-transfer}"
SHARE_DIR="${SHARE_DIR:-/var/lib/lan-file-transfer/share}"
SERVICE_USER="${SERVICE_USER:-lantransfer}"
PORT="${LAN_TRANSFER_PORT:-5000}"
HOST="${LAN_TRANSFER_HOST:-0.0.0.0}"
ENV_FILE="${APP_DIR}/env"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请用 root 运行：sudo bash install.sh" >&2
  exit 1
fi

if [[ ! -f "${APP_DIR}/wsgi.py" ]]; then
  echo "未找到 ${APP_DIR}/wsgi.py，请先把 linux-deploy 同步到 ${APP_DIR}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip

# 专用系统用户，避免 gunicorn 以 root 跑
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

mkdir -p "${APP_DIR}" "${SHARE_DIR}"
chmod +x "${APP_DIR}/start.sh" "${APP_DIR}/install.sh" "${APP_DIR}/uninstall.sh"

if [[ ! -d "${APP_DIR}/.venv" ]]; then
  python3 -m venv "${APP_DIR}/.venv"
fi
"${APP_DIR}/.venv/bin/pip" install -q --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -q -r "${APP_DIR}/requirements.txt"

# 已有 env 则保留密码，避免重装时把口令冲掉
if [[ ! -f "${ENV_FILE}" ]]; then
  PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | head -c 16)"
  cat > "${ENV_FILE}" <<EOF
LAN_TRANSFER_HOST=${HOST}
LAN_TRANSFER_PORT=${PORT}
LAN_TRANSFER_SHARE_DIR=${SHARE_DIR}
LAN_TRANSFER_USER=admin
LAN_TRANSFER_PASSWORD=${PASSWORD}
EOF
  chmod 640 "${ENV_FILE}"
  echo "已生成访问密码，写入 ${ENV_FILE}"
else
  echo "沿用已有 ${ENV_FILE}"
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}" "${SHARE_DIR}"
chmod 750 "${APP_DIR}"
chmod 770 "${SHARE_DIR}"

install -m 644 "${APP_DIR}/systemd/lan-file-transfer.service" /etc/systemd/system/lan-file-transfer.service
systemctl daemon-reload
systemctl enable --now lan-file-transfer.service
systemctl --no-pager --full status lan-file-transfer.service || true

# 若本机开了 ufw，放行端口（阿里云安全组仍需在控制台单独放行）
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "${PORT}/tcp" comment "lan-file-transfer" || true
fi

# 读取实际端口和密码，打印访问信息
# shellcheck disable=SC1090
set -a
source "${ENV_FILE}"
set +a

PUBLIC_IP="$(curl -s --max-time 3 ifconfig.me || hostname -I | awk '{print $1}')"

echo
echo "========== 部署完成 =========="
echo "本机探活:   curl -sS http://127.0.0.1:${LAN_TRANSFER_PORT}/healthz"
echo "公网地址:   http://${PUBLIC_IP}:${LAN_TRANSFER_PORT}"
echo "用户名:     ${LAN_TRANSFER_USER}"
echo "密码:       ${LAN_TRANSFER_PASSWORD}"
echo "共享目录:   ${LAN_TRANSFER_SHARE_DIR}"
echo "查看日志:   journalctl -u lan-file-transfer -f"
echo
echo "若浏览器打不开，请到阿里云控制台 → 安全组，放行 TCP ${LAN_TRANSFER_PORT}。"
echo "=============================="
