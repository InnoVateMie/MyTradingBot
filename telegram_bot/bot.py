"""Telegram bot setup and initialization."""
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config.settings import settings
from telegram_bot.handlers import BotHandlers
from telegram_bot.notifier import SignalNotifier
from utils.logger import logger


class TradingBot:
    """Main Telegram bot class."""
    
    def __init__(self, scanner, signal_repo, performance_repo):
        """
        Initialize the trading bot.
        
        Args:
            scanner: MarketScanner instance
            signal_repo: SignalRepository instance
            performance_repo: PerformanceRepository instance
        """
        self.scanner = scanner
        self.signal_repo = signal_repo
        self.performance_repo = performance_repo
        
        self.application = None
        self.handlers = None
        self.notifier = None
    
    def build(self) -> Application:
        """
        Build and configure the Telegram application.
        
        Returns:
            Configured Application instance
        """
        # Create application
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )
        
        # Create handlers
        self.handlers = BotHandlers(
            scanner=self.scanner,
            signal_repo=self.signal_repo,
            performance_repo=self.performance_repo,
        )
        
        # Create notifier
        self.notifier = SignalNotifier(self.application.bot)
        
        # Register command handlers
        self.application.add_handler(
            CommandHandler("start", self.handlers.start_command)
        )
        self.application.add_handler(
            CommandHandler("password", self.handlers.password_command)
        )
        self.application.add_handler(
            CommandHandler("dashboard", self.handlers.dashboard_command)
        )
        self.application.add_handler(
            CommandHandler("stats", self.handlers.stats_command)
        )
        self.application.add_handler(
            CommandHandler("help", self.handlers.help_command)
        )
        
        # Register callback handler for inline keyboards
        self.application.add_handler(
            CallbackQueryHandler(self.handlers.callback_handler)
        )
        
        logger.info("Telegram bot configured")
        return self.application
    
    async def start(self) -> None:
        """Start the bot in polling mode."""
        if not self.application:
            self.build()
        
        logger.info("Starting Telegram bot polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
    
    async def stop(self) -> None:
        """Stop the bot."""
        if self.application:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
    
    async def broadcast_signal(self, signal) -> int:
        """
        Broadcast a signal to all authorized users.
        
        Args:
            signal: Signal to broadcast
        
        Returns:
            Number of users notified
        """
        if self.notifier:
            return await self.notifier.broadcast_signal(signal)
        return 0
