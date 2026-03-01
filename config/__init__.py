"""Configuration module for the trading bot."""
from .settings import settings
from .auth import auth_manager

__all__ = ["settings", "auth_manager"]
