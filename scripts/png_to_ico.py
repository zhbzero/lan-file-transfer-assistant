"""
将 图标.png 转为 Windows 可用的多尺寸 app.ico（供 PyInstaller 与窗口图标使用）。

查找顺序：项目根目录「图标.png」→ assets/图标.png。
若均不存在，生成简易占位 PNG 并给出提示（可自行替换后重新打包）。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_source_png(root: Path) -> Path | None:
    for name in (root / "图标.png", root / "assets" / "图标.png"):
        if name.is_file():
            return name
    return None


def _write_placeholder_png(path: Path) -> None:
    """简易占位图标（蓝底 + 文件夹示意），避免无图标时打包失败。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 256
    im = Image.new("RGBA", (size, size), (15, 23, 42, 255))
    draw = ImageDraw.Draw(im)
    margin = 28
    draw.rounded_rectangle(
        [margin, margin + 18, size - margin, size - margin],
        radius=18,
        fill=(59, 130, 246, 255),
    )
    draw.rounded_rectangle(
        [margin, margin, margin + 96, margin + 52],
        radius=12,
        fill=(96, 165, 250, 255),
    )
    draw.rectangle([margin + 8, margin + 70, size - margin - 8, margin + 78], fill=(30, 64, 175, 255))
    im.save(path, format="PNG")


def _png_to_ico(png_path: Path, ico_path: Path) -> None:
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    side = max(w, h, 16)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)

    sizes_px = [16, 24, 32, 48, 64, 128, 256]
    frames = [canvas.resize((s, s), Image.Resampling.LANCZOS) for s in sizes_px]
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes_px],
        append_images=frames[1:],
    )


def main() -> int:
    root = _project_root()
    out_dir = root / "dist_assets"
    ico_out = out_dir / "app.ico"

    src = _find_source_png(root)
    if src is None:
        placeholder = out_dir / "_placeholder_icon.png"
        _write_placeholder_png(placeholder)
        print(
            "未找到「图标.png」（请在项目根目录或 assets 目录放置）。"
            f"已生成占位图：{placeholder}\n打包仍可继续；替换为你的图标后重新运行本脚本即可。",
            file=sys.stderr,
        )
        src = placeholder

    _png_to_ico(src, ico_out)
    print(f"已生成：{ico_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
