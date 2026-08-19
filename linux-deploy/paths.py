"""路径安全：禁止用 .. 或符号链接逃出共享根目录。"""

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
    parts = Path(rel).parts
    if ".." in parts:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def safe_filename(name: str) -> str:
    """保留中文等 Unicode 文件名，只去掉路径分隔符和空字节。"""
    name = (name or "").replace("\x00", "")
    name = Path(name).name.strip().strip(".")
    if not name or name in {".", ".."}:
        return ""
    return name
