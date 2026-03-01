"""Logging configuration for the trading bot."""
import logging
import sys
from datetime import datetime

from config.settings import settings


def setup_logger():
    """Configure the logger with appropriate settings."""
    # Create logger
    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Prevent adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logger()


def log_exception(exc: Exception, context: str = ""):
    """Log an exception with context."""
    logger.error(f"{context} - Exception: {str(exc)}", exc_info=True)


__all__ = ["logger", "log_exception"]