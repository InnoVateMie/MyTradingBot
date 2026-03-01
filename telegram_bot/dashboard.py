"""Telegram dashboard UI - message formatting and keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings
from engine.signal_generator import Signal, AnalysisResult
from storage.performance_repo import PerformanceStats, SymbolStats


class Dashboard:
    """Builds Telegram dashboard messages and keyboards."""
    
    # Callback data prefixes
    CB_GET_SIGNAL = "get_signal"
    CB_START_SIGNAL = "start_signal"
    CB_STOP = "stop"
    CB_STATS = "stats"
    CB_SET_PAIRS = "set_pairs"
    CB_TOGGLE_PAIR = "toggle_pair"
    CB_BACK = "back"
    
    @staticmethod
    def welcome_message() -> str:
        """Get welcome message for unauthenticated users."""
        return (
            "Welcome to Trading Signal Bot\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Please enter the password to access:\n\n"
            "Use: /password <your_password>"
        )
    
    @staticmethod
    def auth_success_message() -> str:
        """Get authentication success message."""
        return (
            "Access Granted!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You now have full access to the trading bot.\n"
            "Use /dashboard to view the main menu."
        )
    
    @staticmethod
    def auth_failed_message() -> str:
        """Get authentication failed message."""
        return (
            "Access Denied\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Incorrect password. Please try again."
        )
    
    @staticmethod
    def main_dashboard(
        status: str = "Idle",
        mode: str = "Smart Scan",
        pairs_count: int = 5,
        expiry_mode: str = "Auto",
    ) -> tuple:
        """
        Build main dashboard message and keyboard.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        message = (
            "Trading Bot Dashboard\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status: {status}\n"
            f"Mode: {mode}\n"
            f"Pairs: {pairs_count} monitored\n"
            f"Expiry: {expiry_mode}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("GET SIGNAL", callback_data=Dashboard.CB_GET_SIGNAL)],
            [
                InlineKeyboardButton("SET PAIRS", callback_data=Dashboard.CB_SET_PAIRS),
                InlineKeyboardButton("STATS", callback_data=Dashboard.CB_STATS),
            ],
            [InlineKeyboardButton("STOP", callback_data=Dashboard.CB_STOP)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def scanning_message(cooldown_remaining: int = 0) -> str:
        """Get scanning in progress message."""
        if cooldown_remaining > 0:
            return (
                "Scanning Markets...\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Time until next signal: {cooldown_remaining}s\n"
                "Analyzing all pairs for best opportunity.\n"
                "Please wait..."
            )
        else:
            return (
                "Scanning Markets...\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Analyzing all pairs for best opportunity.\n"
                "Please wait..."
            )
    
    @staticmethod
    def no_opportunity_message(cooldown_remaining: int = 0) -> tuple:
        """
        Message when no good opportunity found.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        if cooldown_remaining > 0:
            message = (
                "Monitoring Markets...\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "No trading pair currently meets the\n"
                "minimum score threshold (72/100).\n\n"
                f"Time until next signal: {cooldown_remaining}s\n\n"
                "Markets are being continuously analyzed.\n"
                "Signals will be sent when conditions align."
            )
        else:
            message = (
                "No Strong Signal Found\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "No trading pair currently meets the\n"
                "minimum score threshold (72/100).\n\n"
                "Markets are either ranging or\n"
                "conditions are unclear.\n\n"
                "Try again in a few moments."
            )
        
        keyboard = [
            [InlineKeyboardButton("SCAN AGAIN", callback_data=Dashboard.CB_GET_SIGNAL)],
            [InlineKeyboardButton("BACK", callback_data=Dashboard.CB_BACK)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def opportunity_found(result: AnalysisResult) -> tuple:
        """
        Build opportunity found message.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        display_name = settings.get_display_name(result.symbol)
        direction_emoji = "" if result.score.direction == "BUY" else ""
        
        # Score bar visualization
        score_int = int(result.score.total_score)
        filled = score_int // 10
        empty = 10 - filled
        score_bar = "" * filled + "" * empty
        
        message = (
            "BEST OPPORTUNITY FOUND\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pair: {display_name}\n"
            f"Direction: {direction_emoji} {result.score.direction}\n"
            f"Score: {score_int}/100 {score_bar}\n"
            f"Expiry: {result.expiry.label}\n"
            f"Confidence: {result.score.confidence}\n\n"
            f"Trend: {result.score.trend_score:.0f}/100\n"
            f"Momentum: {result.score.momentum_score:.0f}/100\n"
            f"Volatility: {result.score.volatility_score:.0f}/100\n"
            f"Structure: {result.score.structure_score:.0f}/100\n"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "START SIGNAL",
                callback_data=f"{Dashboard.CB_START_SIGNAL}:{result.symbol}"
            )],
            [InlineKeyboardButton("SCAN AGAIN", callback_data=Dashboard.CB_GET_SIGNAL)],
            [InlineKeyboardButton("BACK", callback_data=Dashboard.CB_BACK)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def monitoring_started(symbol: str) -> tuple:
        """
        Build monitoring started message.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        display_name = settings.get_display_name(symbol)
        
        message = (
            "MONITORING ACTIVE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Watching: {display_name}\n\n"
            "Waiting for entry confirmation...\n"
            "Signal will be sent when conditions align.\n\n"
            "Stay ready to execute!"
        )
        
        keyboard = [
            [InlineKeyboardButton("STOP MONITORING", callback_data=Dashboard.CB_STOP)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def signal_alert(signal: Signal) -> tuple:
        """Build signal alert message and keyboard."""
        display_name = settings.get_display_name(signal.symbol)
        
        if signal.direction == "BUY":
            direction_line = f"BUY NOW (Signal #{signal.signal_number})"
        else:
            direction_line = f"SELL NOW (Signal #{signal.signal_number})"
        
        message = (
            f"{direction_line}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Pair: {display_name}\n"
            f"Score: {signal.score:.0f}/100\n"
            f"Expiry: {signal.expiry_label}\n"
            f"Confidence: {signal.confidence}\n"
            f"Entry: {signal.entry_price:.5f}\n\n"
            "Execute trade NOW!"
        )
        
        # Add STOP button to the signal
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("STOP BOT", callback_data="stop_bot")],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def stats_message(
        stats: PerformanceStats,
        symbol_stats: list,
    ) -> tuple:
        """
        Build statistics message.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        message = (
            "Performance Summary\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Today's Signals: {stats.today_signals}\n"
            f"Today Win Rate: {stats.today_win_rate:.1f}%\n\n"
            f"All-Time Signals: {stats.total_signals}\n"
            f"All-Time Win Rate: {stats.win_rate:.1f}%\n\n"
        )
        
        if symbol_stats:
            message += "By Symbol:\n"
            message += "─────────────────────────\n"
            
            for ss in symbol_stats[:5]:  # Top 5 symbols
                display_name = settings.get_display_name(ss.symbol)
                message += f"{display_name}: {ss.wins}W/{ss.losses}L ({ss.win_rate:.1f}%)\n"
        
        keyboard = [
            [InlineKeyboardButton("BACK", callback_data=Dashboard.CB_BACK)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def stopped_message() -> tuple:
        """
        Build stopped/idle message.
        
        Returns:
            Tuple of (message_text, InlineKeyboardMarkup)
        """
        message = (
            "Bot Stopped\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Signal monitoring has stopped.\n"
            "Press GET SIGNAL to scan again."
        )
        
        keyboard = [
            [InlineKeyboardButton("GET SIGNAL", callback_data=Dashboard.CB_GET_SIGNAL)],
            [InlineKeyboardButton("BACK TO DASHBOARD", callback_data=Dashboard.CB_BACK)],
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_message() -> str:
        """Get help message."""
        return (
            "Trading Bot Help\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/dashboard - Show main dashboard\n"
            "/stats - View performance statistics\n"
            "/help - Show this help message\n\n"
            "How to use:\n"
            "1. Press GET SIGNAL to scan markets\n"
            "2. Review the opportunity shown\n"
            "3. Press START SIGNAL to monitor\n"
            "4. Execute trade when signal appears\n\n"
            "Signals are generated when:\n"
            "- Score reaches 72/100 threshold\n"
            "- All indicator conditions align\n"
            "- Market structure confirms direction"
        )
