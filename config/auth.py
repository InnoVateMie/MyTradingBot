"""Authentication and session management."""
import os
from typing import Set


class AuthManager:
    """Manages bot authentication and user sessions."""
    
    # Default password - can be overridden via environment variable
    DEFAULT_PASSWORD = "TradePro2024"
    
    def __init__(self):
        """Initialize the auth manager."""
        self._password = os.getenv("BOT_PASSWORD", self.DEFAULT_PASSWORD)
        self._authorized_chat_ids: Set[int] = set()
    
    def validate_password(self, password: str) -> bool:
        """Check if provided password is correct."""
        return password == self._password
    
    def authorize(self, chat_id: int) -> None:
        """Grant access to a chat ID."""
        self._authorized_chat_ids.add(chat_id)
    
    def revoke(self, chat_id: int) -> None:
        """Revoke access from a chat ID."""
        self._authorized_chat_ids.discard(chat_id)
    
    def is_authorized(self, chat_id: int) -> bool:
        """Check if a chat ID is authorized."""
        return chat_id in self._authorized_chat_ids
    
    def get_authorized_chats(self) -> Set[int]:
        """Get all authorized chat IDs."""
        return self._authorized_chat_ids.copy()
    
    @property
    def authorized_count(self) -> int:
        """Get count of authorized sessions."""
        return len(self._authorized_chat_ids)


# Global auth manager instance
auth_manager = AuthManager()
