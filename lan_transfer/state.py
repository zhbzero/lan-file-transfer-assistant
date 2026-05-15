"""进程内共享状态（根目录、剪贴文字），供 Flask 与 GUI 线程读写。"""

from __future__ import annotations

import threading
import time
from pathlib import Path


class TransferState:
    """线程安全的传输状态。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        default_root = Path.home() / "Documents" / "内网传输共享"
        self._root_dir: Path = default_root
        self.shared_text: str = ""
        self.text_updated_at: float = 0.0

    def set_root_dir(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve()
        with self._lock:
            self._root_dir = p

    def get_root_dir(self) -> Path:
        with self._lock:
            return self._root_dir

    def touch_text(self) -> None:
        with self._lock:
            self.text_updated_at = time.time()
