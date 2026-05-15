"""
将 图标.png 转为 Windows 可用的多尺寸 app.ico（供 PyInstaller 与窗口图标使用）。

查找顺序：项目根目录「图标.png」→ assets/图标.png。
若均不存在，生成简易占位 PNG 并给出提示（可自行替换后重新打包）。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


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
    # 占位图也尽量大一点，后续多步缩小时更清晰（尺寸以 256 版为基准两倍）
    size = 512
    k = size / 256
    im = Image.new("RGBA", (size, size), (15, 23, 42, 255))
    draw = ImageDraw.Draw(im)
    margin = int(28 * k)
    draw.rounded_rectangle(
        [margin, margin + int(18 * k), size - margin, size - margin],
        radius=int(18 * k),
        fill=(59, 130, 246, 255),
    )
    draw.rounded_rectangle(
        [margin, margin, margin + int(96 * k), margin + int(52 * k)],
        radius=int(12 * k),
        fill=(96, 165, 250, 255),
    )
    draw.rectangle(
        [margin + int(8 * k), margin + int(70 * k), size - margin - int(8 * k), margin + int(78 * k)],
        fill=(30, 64, 175, 255),
    )
    im.save(path, format="PNG")


def _resize_square_high_quality(im: Image.Image, out_side: int) -> Image.Image:
    """
    从已正方形的 RGBA 图生成目标边长的一帧。
    大图→小图时使用「多步缩小 + LANCZOS」，比一步缩到 16px 更锐利。
    小图→大图仅能用插值放大，无法比源图更清晰（应在素材阶段使用足够大的 PNG）。
    """
    w, h = im.size
    if w != h:
        raise ValueError("expected square image")
    if w == out_side:
        return im.copy()
    if w < out_side:
        return im.resize((out_side, out_side), Image.Resampling.LANCZOS)

    cur = im
    side = w
    # 每次至多缩小到约一半，直到边长落在 (out_side, out_side*2] 再精确缩到 out_side
    while side > out_side * 2:
        next_side = max(out_side, side // 2)
        cur = cur.resize((next_side, next_side), Image.Resampling.LANCZOS)
        side = next_side
    return cur.resize((out_side, out_side), Image.Resampling.LANCZOS)


def _mild_sharpen_rgba_for_small_icons(side: int, im: Image.Image) -> Image.Image:
    """
    资源管理器 / 桌面常用 16～48px，高 DPI 下还会要 20、40、56 等档位。
    小图仅在 RGB 上做轻微 Unsharp，减轻缩小后的糊边（不伤透明通道）。
    """
    if side > 96:
        return im
    r, g, b, a = im.split()
    rgb = Image.merge("RGB", (r, g, b))
    if side <= 48:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.35, percent=58, threshold=2))
    else:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.28, percent=38, threshold=2))
    r2, g2, b2 = rgb.split()
    return Image.merge("RGBA", (r2, g2, b2, a))


def _png_to_ico(png_path: Path, ico_path: Path) -> None:
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    side = max(w, h, 16)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)

    if side < 256:
        print(
            f"提示：当前「图标.png」最大边仅 {side}px，ICO 中 128/256 档位会被放大插值，容易发虚。"
            "建议使用至少 512×512（更佳 1024×1024）的矢量导出或高清 PNG。",
            file=sys.stderr,
        )

    # 含 Win10/11 高 DPI 壳层常用的中间档（20、40、56 等），减少「只有 256 清晰、exe 图标糊」的拉伸插值。
    sizes_px = [16, 20, 24, 28, 32, 40, 48, 56, 64, 96, 128, 256]
    frames: list[Image.Image] = []
    for s in sizes_px:
        frame = _resize_square_high_quality(canvas, s)
        frame = _mild_sharpen_rgba_for_small_icons(s, frame)
        frames.append(frame)

    # Pillow ICO：首张图的尺寸用于判断是否写入各档位；若首张是 16×16，则所有大于 16 的尺寸会被跳过，
    # 导致 ICO 极小且失真。必须把「最大」的那一帧作为第一个参数。
    ordered_largest_first = list(reversed(frames))
    ordered_largest_first[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes_px],
        append_images=ordered_largest_first[1:],
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
