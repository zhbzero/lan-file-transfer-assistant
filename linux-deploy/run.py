"""本机调试入口：python3 run.py（生产环境请用 gunicorn + systemd）。"""

from __future__ import annotations

from config import HOST, PORT, SHARE_DIR
from wsgi import app

if __name__ == "__main__":
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"共享目录: {SHARE_DIR}")
    print(f"监听: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True)
