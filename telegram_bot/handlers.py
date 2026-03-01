"""Telegram command and callback handlers."""
from telegram import Update
from telegram.ext import ContextTypes

from config.auth import auth_manager
from config.settings import settings
from telegram_bot.dashboard import Dashboard
from utils.logger import logger


class BotHandlers:
    """Handles all Telegram commands and callbacks."""
    
    def __init__(self, scanner, signal_repo, performance_repo):
        """
        Initialize handlers.
        
        Args:
            scanner: MarketScanner instance
            signal_repo: SignalRepository instance
            performance_repo: PerformanceRepository instance
        """
        self.scanner = scanner
        self.signal_repo = signal_repo
        self.performance_repo = performance_repo
    
    async def start_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        
        if auth_manager.is_authorized(chat_id):
            # Already authorized - show dashboard
            message, keyboard = Dashboard.main_dashboard(
                pairs_count=len(settings.symbols)
            )
            await update.message.reply_text(message, reply_markup=keyboard)
        else:
            # Not authorized - show welcome
            await update.message.reply_text(Dashboard.welcome_message())
    
    async def password_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /password command."""
        chat_id = update.effective_chat.id
        
        # Extract password from command
        if not context.args:
            await update.message.reply_text(
                "Please provide password: /password <your_password>"
            )
            return
        
        password = context.args[0]
        
        if auth_manager.validate_password(password):
            auth_manager.authorize(chat_id)
            logger.info(f"User {chat_id} authenticated successfully")
            await update.message.reply_text(Dashboard.auth_success_message())
            
            # Show dashboard
            message, keyboard = Dashboard.main_dashboard(
                pairs_count=len(settings.symbols)
            )
            await update.message.reply_text(message, reply_markup=keyboard)
        else:
            logger.warning(f"Failed auth attempt from {chat_id}")
            await update.message.reply_text(Dashboard.auth_failed_message())
    
    async def dashboard_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /dashboard command."""
        chat_id = update.effective_chat.id
        
        if not auth_manager.is_authorized(chat_id):
            await update.message.reply_text(Dashboard.welcome_message())
            return
        
        status = "Monitoring" if self.scanner.is_monitoring else "Idle"
        message, keyboard = Dashboard.main_dashboard(
            status=status,
            pairs_count=len(settings.symbols)
        )
        await update.message.reply_text(message, reply_markup=keyboard)
    
    async def stats_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /stats command."""
        chat_id = update.effective_chat.id
        
        if not auth_manager.is_authorized(chat_id):
            await update.message.reply_text(Dashboard.welcome_message())
            return
        
        stats = await self.performance_repo.get_overall_stats()
        symbol_stats = await self.performance_repo.get_all_symbol_stats()
        
        message, keyboard = Dashboard.stats_message(stats, symbol_stats)
        await update.message.reply_text(message, reply_markup=keyboard)
    
    async def help_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        await update.message.reply_text(Dashboard.help_message())
    
    async def callback_handler(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        data = query.data
        
        if not auth_manager.is_authorized(chat_id):
            await query.edit_message_text(Dashboard.welcome_message())
            return
        
        # Parse callback data
        if data == Dashboard.CB_GET_SIGNAL:
            await self._handle_get_signal(query)
        
        elif data.startswith(Dashboard.CB_START_SIGNAL):
            symbol = data.split(":")[1]
            await self._handle_start_signal(query, symbol)
        
        elif data == Dashboard.CB_STOP:
            await self._handle_stop(query)
        
        elif data == "stop_bot":  # Handle the STOP BOT button from signals
            await self._handle_stop_bot(query)
        
        elif data == "start_bot":  # Handle the START BOT button
            await self._handle_start_bot(query)
        
        elif data == Dashboard.CB_STATS:
            await self._handle_stats(query)
        
        elif data == Dashboard.CB_BACK:
            await self._handle_back(query)
        
        elif data == Dashboard.CB_SET_PAIRS:
            await query.edit_message_text(
                "Pair selection coming soon!\n\n"
                "Currently monitoring all pairs."
            )
    
    async def _handle_get_signal(self, query) -> None:
        """Handle GET SIGNAL button."""
        # Check if any symbol is on cooldown and show countdown
        is_on_cooldown, remaining_time = self.scanner.get_global_cooldown_status()
        
        # Show initial scanning message with cooldown if applicable
        await query.edit_message_text(Dashboard.scanning_message(remaining_time))
        
        # Simulate progress by updating the message periodically
        import asyncio
        for i in range(3):  # Show progress for 3 seconds
            await asyncio.sleep(1)
            dots = "." * (i % 3 + 1)
            # Check cooldown again during scanning
            is_on_cooldown, remaining_time = self.scanner.get_global_cooldown_status()
            progress_message = (
                f"Scanning Markets{dots}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Time until next signal: {remaining_time}s\n"
                f"Analyzing all pairs for best opportunity.\n"
                f"Progress: {(i+1)*25}% complete..."
            )
            await query.edit_message_text(progress_message)
        
        # Now run the actual scan
        result = await self.scanner.scan_once()
        
        if result and result.meets_threshold:
            message, keyboard = Dashboard.opportunity_found(result)
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            # Show cooldown info even if no signal found
            is_on_cooldown, remaining_time = self.scanner.get_global_cooldown_status()
            message, keyboard = Dashboard.no_opportunity_message(remaining_time)
            await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_start_signal(self, query, symbol: str) -> None:
        """Handle START SIGNAL button."""
        await self.scanner.start_monitoring(symbol)
        
        message, keyboard = Dashboard.monitoring_started(symbol)
        await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_stop(self, query) -> None:
        """Handle STOP button."""
        await self.scanner.stop_monitoring()
        
        message, keyboard = Dashboard.stopped_message()
        await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_stop_bot(self, query) -> None:
        """Handle STOP BOT button - disables signal generation."""
        self.scanner.disable_signals()
        
        message = (
            "BOT STOPPED\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Signal generation has been disabled.\n"
            "Press START to resume signal generation."
        )
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("START BOT", callback_data="start_bot")],
            [InlineKeyboardButton("BACK TO DASHBOARD", callback_data=Dashboard.CB_BACK)],
        ]
        
        await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_start_bot(self, query) -> None:
        """Handle START BOT button - enables signal generation."""
        self.scanner.enable_signals()
        
        message, keyboard = Dashboard.main_dashboard(
            status="Monitoring" if self.scanner.is_monitoring else "Idle",
            pairs_count=len(settings.symbols)
        )
        await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_stats(self, query) -> None:
        """Handle STATS button."""
        stats = await self.performance_repo.get_overall_stats()
        symbol_stats = await self.performance_repo.get_all_symbol_stats()
        
        message, keyboard = Dashboard.stats_message(stats, symbol_stats)
        await query.edit_message_text(message, reply_markup=keyboard)
    
    async def _handle_back(self, query) -> None:
        """Handle BACK button."""
        status = "Monitoring" if self.scanner.is_monitoring else "Idle"
        message, keyboard = Dashboard.main_dashboard(
            status=status,
            pairs_count=len(settings.symbols)
        )
        await query.edit_message_text(message, reply_markup=keyboard)
