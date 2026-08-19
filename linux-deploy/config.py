"""从环境变量读取运行配置（适合 systemd EnvironmentFile）。"""

from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# 监听地址。公网服务器请保持 0.0.0.0，由安全组控制谁能进来。
HOST = _env("LAN_TRANSFER_HOST", "0.0.0.0")
PORT = int(_env("LAN_TRANSFER_PORT", "5000") or "5000")

# 共享目录：上传的文件会落到这里
SHARE_DIR = Path(_env("LAN_TRANSFER_SHARE_DIR", "/var/lib/lan-file-transfer/share")).expanduser()

# HTTP Basic Auth。公网部署必须设置密码；密码为空则不启用鉴权（仅建议内网）。
ACCESS_USER = _env("LAN_TRANSFER_USER", "admin")
ACCESS_PASSWORD = _env("LAN_TRANSFER_PASSWORD", "")
