"""自动过期相关常量。"""

from __future__ import annotations

from pathlib import Path

AUTO_DELETE_SECONDS = 30 * 60
RETENTION_NOTICE = "文件和文字半小时后自动删除，请及时保存"
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1GB，单次请求（多文件总和）
MAX_UPLOAD_NOTICE = "最大传输大小为 1GB，过大会导致传输失败"


def relative_to_root(root: Path, full: Path) -> str:
    return full.resolve().relative_to(root.resolve()).as_posix()
