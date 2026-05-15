"""Tkinter 桌面外壳：配置共享目录、端口、二维码与浏览器打开。"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import qrcode

from lan_transfer.network import get_lan_ipv4_candidates, pick_primary_lan_ip
from lan_transfer.server import ServerThread, create_app
from lan_transfer.state import TransferState


def _config_paths() -> tuple[Path, Path]:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"
    d = base / "LANTransferAssistant"
    return d, d / "config.json"


class TransferAssistantGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("文件传输助手")
        self.geometry("520x680")
        self.minsize(480, 620)

        self.state = TransferState()
        self._cfg_dir, self._cfg_file = _config_paths()
        self.port_var = tk.StringVar(value="5000")
        self.folder_var = tk.StringVar()
        self._load_config_into_state()

        self.flask_app = create_app(self.state)
        self._server_thread: ServerThread | None = None
        self._qr_photo: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._apply_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_server_safe(initial=True)

    def _load_config_into_state(self) -> None:
        """从配置文件恢复目录与端口；若无配置则创建默认共享目录。"""
        root_default = Path.home() / "Documents" / "内网传输共享"
        port_default = 5000
        root_path = root_default
        port = port_default
        try:
            if self._cfg_file.is_file():
                raw = json.loads(self._cfg_file.read_text(encoding="utf-8"))
                if isinstance(raw.get("root_dir"), str):
                    root_path = Path(raw["root_dir"])
                if raw.get("port") is not None:
                    port = int(raw["port"])
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        root_path = root_path.expanduser()
        try:
            root_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            root_path = Path.home() / "Documents"
        self.state.set_root_dir(root_path)
        self.folder_var.set(str(self.state.get_root_dir()))
        self.port_var.set(str(port))

    def _apply_window_icon(self) -> None:
        """打包后在任务栏/标题栏显示与 exe 一致的图标（Windows 使用 .ico）。"""
        if sys.platform != "win32":
            return
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).resolve().parents[1] / "dist_assets"
        ico = base / "app.ico"
        if not ico.is_file():
            return
        try:
            self.iconbitmap(default=str(ico))
        except tk.TclError:
            pass

    def _save_config(self) -> None:
        try:
            self._cfg_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "root_dir": str(self.state.get_root_dir()),
                "port": int(self.port_var.get().strip()),
            }
            self._cfg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            messagebox.showwarning("保存配置", f"无法写入配置文件：{e}")

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 8}

        hint = ttk.Label(self, text="扫描二维码或在局域网内浏览器访问下方链接：")
        hint.pack(anchor="w", **pad)

        self.qr_label = ttk.Label(self)
        self.qr_label.pack(pady=(4, 8))

        url_frame = ttk.Frame(self)
        url_frame.pack(fill="x", **pad)
        self.url_label = tk.Label(
            url_frame,
            text="",
            fg="#2563eb",
            cursor="hand2",
            font=("Segoe UI", 11, "underline"),
        )
        self.url_label.pack(side="left")
        self.url_label.bind("<Button-1>", lambda _e: self._open_browser())

        open_btn = ttk.Button(self, text="在浏览器中打开", command=self._open_browser)
        open_btn.pack(pady=(0, 10))

        cfg = ttk.LabelFrame(self, text="服务器配置")
        cfg.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        row1 = ttk.Frame(cfg)
        row1.pack(fill="x", padx=10, pady=8)
        ttk.Label(row1, text="共享文件夹:").pack(side="left")
        entry = ttk.Entry(row1, textvariable=self.folder_var)
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        browse = ttk.Button(row1, text="浏览…", command=self._browse_folder)
        browse.pack(side="left")

        row2 = ttk.Frame(cfg)
        row2.pack(fill="x", padx=10, pady=8)
        ttk.Label(row2, text="端口:").pack(side="left")
        port_entry = ttk.Entry(row2, textvariable=self.port_var, width=10)
        port_entry.pack(side="left", padx=(8, 0))

        apply_btn = ttk.Button(cfg, text="更新配置", command=self._apply_config)
        apply_btn.pack(pady=(4, 12))

        status_fr = ttk.Frame(self)
        status_fr.pack(fill="x", padx=12, pady=(0, 12))
        self.status_var = tk.StringVar(value="")
        ttk.Label(status_fr, textvariable=self.status_var, foreground="#64748b").pack(anchor="w")

        self._refresh_access_ui()

    def _silent_port(self) -> int | None:
        """读取端口输入框，非法时不弹窗（用于刷新链接与二维码）。"""
        try:
            p = int(self.port_var.get().strip())
            if 1 <= p <= 65535:
                return p
        except ValueError:
            pass
        return None

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if path:
            self.folder_var.set(path)

    def _parse_port(self) -> int | None:
        try:
            p = int(self.port_var.get().strip())
            if 1 <= p <= 65535:
                return p
        except ValueError:
            pass
        messagebox.showerror("端口无效", "请输入 1–65535 之间的整数端口。")
        return None

    def _stop_server(self) -> None:
        t = self._server_thread
        if t is None:
            return
        try:
            t.shutdown()
            t.join(timeout=5.0)
        except Exception:
            pass
        self._server_thread = None

    def _start_server_safe(self, *, initial: bool = False) -> None:
        port = self._parse_port()
        if port is None:
            return
        self._stop_server()
        self.port_var.set(str(port))
        try:
            thr = ServerThread(self.flask_app, "0.0.0.0", port)
            thr.start()
            if not thr.wait_until_started(timeout=8.0):
                raise TimeoutError("服务启动超时")
            self._server_thread = thr
            self.status_var.set(f"服务已启动，监听 0.0.0.0:{port}")
        except OSError as e:
            self.status_var.set("")
            msg = str(e)
            if not initial:
                messagebox.showerror("启动失败", f"无法监听端口 {port}：\n{msg}")
            else:
                messagebox.showerror("启动失败", f"无法监听端口 {port}：\n{msg}\n请更换端口或关闭占用该端口的程序。")
        except TimeoutError as e:
            self.status_var.set("")
            messagebox.showerror("启动失败", str(e))

        self._refresh_access_ui()

    def _apply_config(self) -> None:
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("共享文件夹", "请先选择共享文件夹。")
            return
        target = Path(folder).expanduser()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("共享文件夹", f"无法创建或使用该目录：\n{e}")
            return
        self.state.set_root_dir(target)
        self.folder_var.set(str(self.state.get_root_dir()))

        old_port = None
        if self._server_thread is not None:
            old_port = self._server_thread.port

        new_port = self._parse_port()
        if new_port is None:
            return

        if old_port != new_port or self._server_thread is None:
            self._start_server_safe(initial=False)
        else:
            self.status_var.set(f"服务运行中，目录已更新（端口仍为 {new_port}）")

        self._save_config()
        self._refresh_access_ui()

    def _refresh_access_ui(self) -> None:
        port = self._silent_port()
        if port is None:
            self.url_label.config(text="（端口应为 1–65535 的整数）")
            self.qr_label.configure(image="")
            self._qr_photo = None
            return
        ip = pick_primary_lan_ip(get_lan_ipv4_candidates())
        if not ip:
            self.url_label.config(text="（未检测到局域网 IP，请检查网卡）")
            self.qr_label.configure(image="")
            self._qr_photo = None
            return
        url = f"http://{ip}:{port}"
        self.url_label.config(text=url)
        self._set_qr(url)

    def _set_qr(self, url: str) -> None:
        qr = qrcode.QRCode(version=None, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((220, 220), Image.Resampling.LANCZOS)
        self._qr_photo = ImageTk.PhotoImage(img)
        self.qr_label.configure(image=self._qr_photo)

    def _open_browser(self) -> None:
        port = self._silent_port()
        if port is None:
            messagebox.showinfo("提示", "请先在「端口」中填写合法数字（1–65535）。")
            return
        ip = pick_primary_lan_ip(get_lan_ipv4_candidates())
        if not ip:
            messagebox.showinfo("提示", "未检测到局域网 IP，请确认已连接网线或 Wi‑Fi。")
            return
        webbrowser.open(f"http://{ip}:{port}")

    def _on_close(self) -> None:
        self._stop_server()
        self.destroy()


def main() -> None:
    app = TransferAssistantGUI()
    app.mainloop()
