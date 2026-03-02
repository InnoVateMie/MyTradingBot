"""Authentication and session management."""
import os
from typing import Set


import json
from pathlib import Path

class AuthManager:
    """Manages bot authentication and user sessions."""

    DEFAULT_PASSWORD = "TradePro2024"
    AUTH_FILE = "authorized_chats.json"

    def __init__(self):
        self._password = os.getenv("BOT_PASSWORD", self.DEFAULT_PASSWORD)
        self._authorized_chat_ids: Set[int] = set()
        self._load_authorized()

    def _load_authorized(self):
        path = Path(self.AUTH_FILE)
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    self._authorized_chat_ids = set(data)
            except Exception:
                self._authorized_chat_ids = set()

    def _save_authorized(self):
        try:
            with open(self.AUTH_FILE, "w") as f:
                json.dump(list(self._authorized_chat_ids), f)
        except Exception:
            pass

    def validate_password(self, password: str) -> bool:
        return password == self._password

    def authorize(self, chat_id: int) -> None:
        self._authorized_chat_ids.add(chat_id)
        self._save_authorized()

    def revoke(self, chat_id: int) -> None:
        self._authorized_chat_ids.discard(chat_id)
        self._save_authorized()

    def is_authorized(self, chat_id: int) -> bool:
        return chat_id in self._authorized_chat_ids

    def get_authorized_chats(self) -> Set[int]:
        return self._authorized_chat_ids.copy()

    @property
    def authorized_count(self) -> int:
        return len(self._authorized_chat_ids)


# Global auth manager instance
auth_manager = AuthManager()
