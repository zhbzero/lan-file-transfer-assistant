"""路径安全与程序目录解析。"""

from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """程序所在目录：打包后为 exe 所在文件夹，开发时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def default_share_root() -> Path:
    """默认共享文件夹（与程序同目录下的「内网传输共享」）。"""
    return app_base_dir() / "内网传输共享"


def safe_resolve_under_root(root: Path, relative: str) -> Path | None:
    """
    将 relative（相对共享根的路径）解析为绝对路径。
    若结果不在 root 之下（含符号链接穿透后的 realpath），返回 None。
    """
    root = root.resolve()
    rel = (relative or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        return root
    # 分段检查，禁止 .. 组件
    parts = Path(rel).parts
    if ".." in parts:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate
