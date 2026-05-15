"""路径安全：禁止跳出共享根目录。"""

from __future__ import annotations

from pathlib import Path


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
