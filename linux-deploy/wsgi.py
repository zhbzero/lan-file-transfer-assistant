"""gunicorn / systemd 入口：wsgi:app"""

from config import SHARE_DIR
from server import create_app
from state import TransferState

SHARE_DIR.mkdir(parents=True, exist_ok=True)
_state = TransferState(root=SHARE_DIR)
app = create_app(_state)
