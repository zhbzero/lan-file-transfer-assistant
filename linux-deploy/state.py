"""进程内共享状态（根目录、剪贴文字、过期清理）。"""

from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

from expiry import AUTO_DELETE_SECONDS
from paths import safe_resolve_under_root

_META_FILENAME = ".lan_transfer_meta.json"


class TransferState:
    """线程安全的传输状态。"""

    def __init__(self, root: str | Path) -> None:
        self._lock = threading.Lock()
        self._root_dir: Path = Path(root).expanduser().resolve()
        self.shared_text: str = ""
        self.text_updated_at: float = 0.0
        self._file_expires: dict[str, float] = {}
        self._text_expires_at: float = 0.0
        self._cleanup_stop = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="expiry-cleanup"
        )
        self._load_meta_for_root(self._root_dir)
        self._cleanup_thread.start()
        try:
            self.purge_expired()
        except Exception:
            pass

    def set_root_dir(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve()
        with self._lock:
            self._root_dir = p
            self._load_meta_unlocked()

    def get_root_dir(self) -> Path:
        with self._lock:
            return self._root_dir

    def set_shared_text(self, text: str) -> None:
        with self._lock:
            self.shared_text = text
            self.text_updated_at = time.time()
            self._text_expires_at = time.time() + AUTO_DELETE_SECONDS
            self._save_meta_unlocked()

    def schedule_file_expiry(self, rel: str) -> None:
        rel = rel.replace("\\", "/").lstrip("/")
        if not rel:
            return
        with self._lock:
            self._file_expires[rel] = time.time() + AUTO_DELETE_SECONDS
            self._save_meta_unlocked()

    def unschedule_path(self, rel: str) -> None:
        rel = rel.replace("\\", "/").lstrip("/")
        with self._lock:
            keys = [k for k in self._file_expires if k == rel or k.startswith(rel + "/")]
            if not keys:
                return
            for key in keys:
                del self._file_expires[key]
            self._save_meta_unlocked()

    def purge_expired(self) -> int:
        """删除已过期文件并清空过期文字，返回删除的文件/目录数量。"""
        now = time.time()
        removed = 0
        text_expired = False
        with self._lock:
            root = self._root_dir
            expired_rels = [rel for rel, exp in self._file_expires.items() if now >= exp]
            for rel in expired_rels:
                if self._delete_path_unlocked(root, rel):
                    removed += 1
                self._file_expires.pop(rel, None)

            if self._text_expires_at > 0 and now >= self._text_expires_at:
                text_expired = True
                self.shared_text = ""
                self.text_updated_at = 0.0
                self._text_expires_at = 0.0

            if expired_rels or text_expired:
                self._save_meta_unlocked()

        return removed

    def is_file_expired(self, rel: str) -> bool:
        rel = rel.replace("\\", "/").lstrip("/")
        now = time.time()
        with self._lock:
            exp = self._file_expires.get(rel)
            return exp is not None and now >= exp

    def _cleanup_loop(self) -> None:
        while not self._cleanup_stop.wait(60.0):
            try:
                self.purge_expired()
            except Exception:
                pass

    def _load_meta_for_root(self, root: Path) -> None:
        with self._lock:
            self._root_dir = root.resolve()
            self._load_meta_unlocked()

    def _load_meta_unlocked(self) -> None:
        self._file_expires = {}
        self._text_expires_at = 0.0
        meta_path = self._root_dir / _META_FILENAME
        if not meta_path.is_file():
            return
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        files = raw.get("files")
        if isinstance(files, dict):
            for rel, exp in files.items():
                if isinstance(rel, str) and isinstance(exp, (int, float)):
                    self._file_expires[rel] = float(exp)
        text_exp = raw.get("text_expires_at")
        if isinstance(text_exp, (int, float)):
            self._text_expires_at = float(text_exp)

    def _save_meta_unlocked(self) -> None:
        meta_path = self._root_dir / _META_FILENAME
        data = {
            "files": self._file_expires,
            "text_expires_at": self._text_expires_at,
        }
        try:
            self._root_dir.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _delete_path_unlocked(self, root: Path, rel: str) -> bool:
        full = safe_resolve_under_root(root, rel)
        if full is None or full.resolve() == root.resolve():
            return False
        try:
            if full.is_file():
                full.unlink()
                return True
            if full.is_dir():
                shutil.rmtree(full)
                return True
        except OSError:
            return False
        return False
