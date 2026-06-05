"""Flask HTTP 服务：列表、上传、下载、删除、共享文字。"""

from __future__ import annotations

import os
import shutil
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from lan_transfer.expiry import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_NOTICE,
    RETENTION_NOTICE,
    relative_to_root,
)
from lan_transfer.paths import safe_resolve_under_root
from lan_transfer.state import TransferState


def create_app(state: TransferState) -> Flask:
    pkg_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(pkg_dir / "templates"),
        static_folder=str(pkg_dir / "static"),
    )
    # 单次请求体上限（多文件上传时总和）
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    @app.errorhandler(413)
    def request_entity_too_large(_e):
        return jsonify({"error": MAX_UPLOAD_NOTICE}), 413

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            retention_notice=RETENTION_NOTICE,
            max_upload_notice=MAX_UPLOAD_NOTICE,
            max_upload_bytes=MAX_UPLOAD_BYTES,
        )

    @app.route("/api/list")
    def api_list():
        state.purge_expired()
        root = state.get_root_dir()
        rel = request.args.get("path", "").strip().replace("\\", "/")
        target = safe_resolve_under_root(root, rel)
        if target is None or not target.is_dir():
            return jsonify({"error": "无效路径"}), 400
        items = []
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if entry.name.startswith("."):
                    continue
                try:
                    st = entry.stat()
                    items.append(
                        {
                            "name": entry.name,
                            "is_dir": entry.is_dir(),
                            "size": None if entry.is_dir() else st.st_size,
                            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                except OSError:
                    continue
        except OSError as e:
            return jsonify({"error": str(e)}), 500
        breadcrumbs = _breadcrumbs(rel)
        return jsonify({"path": rel, "breadcrumbs": breadcrumbs, "items": items})

    @app.route("/api/download")
    def api_download():
        state.purge_expired()
        root = state.get_root_dir()
        rel = request.args.get("path", "").strip().replace("\\", "/")
        if state.is_file_expired(rel):
            abort(404)
        full = safe_resolve_under_root(root, rel)
        if full is None or not full.is_file():
            abort(404)
        directory = str(full.parent)
        fname = full.name
        return send_from_directory(directory, fname, as_attachment=True)

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        root = state.get_root_dir()
        sub = request.form.get("path", "").strip().replace("\\", "/")
        dest_dir = safe_resolve_under_root(root, sub)
        if dest_dir is None or not dest_dir.is_dir():
            return jsonify({"error": "上传目标目录无效"}), 400
        if "file" not in request.files:
            return jsonify({"error": "未选择文件"}), 400
        files = request.files.getlist("file")
        saved = 0
        errors: list[str] = []
        for f in files:
            if not f or not f.filename:
                continue
            name = secure_filename(f.filename)
            if not name:
                errors.append("非法文件名")
                continue
            target = dest_dir / name
            try:
                f.save(str(target))
                state.schedule_file_expiry(relative_to_root(root, target))
                saved += 1
            except OSError as e:
                errors.append(f"{name}: {e}")
        if saved == 0 and not errors:
            return jsonify({"error": "没有可保存的文件"}), 400
        return jsonify({"saved": saved, "errors": errors})

    @app.route("/api/delete", methods=["POST"])
    def api_delete():
        root = state.get_root_dir()
        payload = request.get_json(silent=True) or {}
        rel = str(payload.get("path", "")).strip().replace("\\", "/")
        full = safe_resolve_under_root(root, rel)
        if full is None:
            return jsonify({"error": "无效路径"}), 400
        if full.resolve() == root.resolve():
            return jsonify({"error": "不能删除共享根目录"}), 400
        try:
            if full.is_file():
                full.unlink()
            elif full.is_dir():
                shutil.rmtree(full)
            else:
                return jsonify({"error": "路径不存在"}), 404
            state.unschedule_path(rel)
        except OSError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"ok": True})

    @app.route("/api/text", methods=["GET"])
    def api_text_get():
        state.purge_expired()
        return jsonify({"text": state.shared_text, "updated_at": state.text_updated_at})

    @app.route("/api/text", methods=["POST"])
    def api_text_post():
        payload = request.get_json(silent=True) or {}
        text = payload.get("text")
        if text is None:
            return jsonify({"error": "缺少 text 字段"}), 400
        if not isinstance(text, str):
            return jsonify({"error": "text 须为字符串"}), 400
        state.set_shared_text(text)
        return jsonify({"ok": True})

    return app


def _breadcrumbs(rel: str) -> list[dict[str, str]]:
    """生成前端面包屑：每项 name + path（相对根）。"""
    rel = (rel or "").strip().replace("\\", "/").strip("/")
    crumbs = [{"name": "根目录", "path": ""}]
    if not rel:
        return crumbs
    acc = ""
    for part in rel.split("/"):
        if not part:
            continue
        acc = f"{acc}/{part}" if acc else part
        crumbs.append({"name": part, "path": acc})
    return crumbs


class ServerThread(threading.Thread):
    """在后台线程运行 Werkzeug 服务器，支持 shutdown 后更换端口重启。"""

    def __init__(self, app: Flask, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.app = app
        self.host = host
        self.port = port
        self._server = None
        self._ready = threading.Event()

    def run(self) -> None:
        from werkzeug.serving import make_server

        self._server = make_server(self.host, self.port, self.app, threaded=True)
        self._ready.set()
        self._server.serve_forever()

    def wait_until_started(self, timeout: float = 5.0) -> bool:
        return self._ready.wait(timeout)

    def shutdown(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
