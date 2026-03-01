"""Application settings and configuration."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Central configuration for the trading bot."""
    
    # Telegram
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    
    # Finnhub
    finnhub_api_key: str = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))
    finnhub_ws_url: str = "wss://ws.finnhub.io"
    
    # Trading pairs to monitor
    symbols: List[str] = field(default_factory=lambda: [
        "OANDA:EUR_USD",  # EURUSD
        "OANDA:GBP_USD",  # GBPUSD
        "OANDA:USD_JPY",  # USDJPY
        "OANDA:XAU_USD",  # XAUUSD (Gold)
        "BINANCE:BTCUSDT",  # BTCUSD
    ])
    
    # Display names for symbols
    symbol_display_names: dict = field(default_factory=lambda: {
        "OANDA:EUR_USD": "EURUSD",
        "OANDA:GBP_USD": "GBPUSD",
        "OANDA:USD_JPY": "USDJPY",
        "OANDA:XAU_USD": "XAUUSD",
        "BINANCE:BTCUSDT": "BTCUSD",
    })
    
    # Candle timeframes (in seconds)
    timeframes: List[int] = field(default_factory=lambda: [5, 10, 15, 30, 60])
    
    # Signal thresholds
    signal_threshold: float = 72.0  # Minimum score to generate a signal
    
    # Scoring engine weights (must sum to <= 1.0)
    trend_weight: float = 0.30
    momentum_weight: float = 0.20
    volatility_weight: float = 0.15
    structure_weight: float = 0.25
    
    # Indicator parameters
    ema_fast_period: int = 20
    ema_medium_period: int = 50
    ema_slow_period: int = 200
    rsi_period: int = 14
    atr_period: int = 14
    adx_period: int = 14
    
    # Candle buffer size (number of candles to keep)
    candle_buffer_size: int = 300  # Enough for EMA-200 + buffer
    
    # Tick buffer size per symbol
    tick_buffer_size: int = 10000
    
    # Signal cooldown (seconds) - prevent duplicate signals
    signal_cooldown: int = 120  # 2 minutes to allow time for previous signal execution
    
    # WebSocket reconnection settings
    ws_reconnect_delay_initial: float = 1.0
    ws_reconnect_delay_max: float = 60.0
    ws_reconnect_delay_multiplier: float = 2.0
    
    # Database
    database_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "trading_bot.db"))
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    def get_display_name(self, symbol: str) -> str:
        """Get user-friendly display name for a symbol."""
        return self.symbol_display_names.get(symbol, symbol)
    
    def validate(self) -> bool:
        """Validate required settings are present."""
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.finnhub_api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        return True


# Global settings instance
settings = Settings()
